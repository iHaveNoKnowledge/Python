# Twin instance architecture (prepared, not switched on)

Goal: allow two bot instances to work in parallel, each driving its own Chrome,
without changing how the app behaves today. A single instance with no
environment variables must stay byte-for-byte equivalent in behaviour.

Status: stage 0 done. Stages 1 and 2 are not implemented.

## Config contract

`autopage_config.RuntimeConfig` is the only place that knows about per-instance
settings. It is read when a component is constructed, never at import time,
because `autopage_MKII_ver5.x.x.py` calls `load_dotenv()` after its imports and
shell variables must win over the file.

| Variable | Default | Purpose |
| --- | --- | --- |
| `AUTOPAGE_CHROME_DEBUG_HOST` | `localhost` | Chrome debugging host to attach to |
| `AUTOPAGE_CHROME_DEBUG_PORT` | `8989` | Chrome debugging port to attach to |
| `AUTOPAGE_WORKER_ID` | `default` | Label used in logs to tell workers apart |
| `AUTOPAGE_DATA_DIR` | project folder | Reserved: mutable files per instance |

`functions/browser_manager.py` resolves the config in `BrowserManager.__init__`
and uses `config.chrome_debugger_address` for the Selenium `debuggerAddress`
capability. The module constants `CHROME_DEBUG_HOST` / `CHROME_DEBUG_PORT` stay
as the defaults for older callers.

Invalid port values raise `ValueError` instead of silently attaching nowhere.

## What is per instance and what is shared

Per instance, no negotiation needed:

- Chrome process, its own `--user-data-dir`, its own `--remote-debugging-port`
- WebDriver session, tabs, cart state
- `AUTOPAGE_WORKER_ID`, log lines, reconnect state

Shared today, must be separated or serialised before two instances run on the
same machine and folder:

| Shared thing | Where | Problem with two writers |
| --- | --- | --- |
| `logs/autopageMKII_log_YYYY_MM_DD.log` | main app loguru setup | rotation races, mixed workers |
| `logs/completed_orders.json` | order save path | read-modify-write loses entries |
| `logs/completed_orders.csv` | order save path | append is tolerable, header race is not |
| `sumatra_pdf_cache.txt` | bot init | both rewrite the same cache |
| accel workbook | `functions/accel_mode.py` sheet writes | `ExcelWriter(mode='a', if_sheet_exists='replace')` on the same file fails or drops a sheet |
| `tables/cp_data.xlsx` | `functions/pos/pricing_engine.py` formatting | last writer wins |
| Google Sheets / Processed_Logs rows | accel and cp loaders | duplicate rows without an idempotency key |
| keyring session paths | `AccountManager` | second instance overwrites the first one's paths |
| printer queue | invoice printing | interleaved physical documents |

`caches.json` (`autopage_MKII_ver5.x.x.py`) is computed but never written, so it
is not a conflict.

Two instances cannot share one `--user-data-dir`: Chrome keeps one process per
profile folder, and a second launch hands off to the running process and ignores
the new `--remote-debugging-port`. Chrome 136 and later also refuses to enable
remote debugging on the default profile, so every worker needs its own
`--user-data-dir`.

## cp_data rules for changes made from here on

`cp_data.xlsx` and the Google Sheet rows are master data shared by every worker,
so they are the opposite of `AUTOPAGE_DATA_DIR`: do **not** give each worker its
own copy, or the CP suggestion for the same SKU and price will drift between
workers.

1. Resolve the table path in one place. Today the path is guessed at
   `autopage_MKII_ver5.x.x.py:361`, `functions/pos/pricing_engine.py:633-634`,
   `:719-720`, `:1638-1639`, `:2605`, and the second loader in the same file
   repeats it at `:1310-1317`. New code should call one resolver fed by
   `RuntimeConfig.cp_table_path` (`AUTOPAGE_CP_TABLE_PATH`), keeping today's
   search order `tables/cp_data.xlsx` then `assets/tables/cp_data.xlsx` as the
   default.
2. Move the Web App URL out of `functions/pos/cp_data_loader.py:9` into
   `RuntimeConfig.gas_url` (`AUTOPAGE_GAS_URL`), defaulting to the current
   literal. Do not import `DEFAULT_GAS_URL` in new code; pass the value down.
3. Writes are whole-file rewrites: `functions/pos/cp_data_loader.py:416` and
   `:446` rewrite every sheet, and `functions/pos/pricing_engine.py:374,394`
   (`format_cp_excel`) reopens and saves the same workbook. Two writers lose
   rows and raise `PermissionError` while a person has the file open. Keep one
   writer; if two instances must write, serialise on a lock file, re-read before
   writing, and keep the existing `PermissionError` handling at
   `cp_data_loader.py:430` and `:465`.
4. GAS POSTs need an idempotency key. The dedup guard compares rows, so a
   retried POST after a timeout can still append a duplicate row.
5. Single-run behaviour must not change when the new env vars are unset: same
   path resolution, same URL, same file format.

## Stages

Stage 0, done: config seam plus `browser_manager` wiring. Single instance keeps
`localhost:8989`. Two terminals can already attach to two Chromes by setting
`AUTOPAGE_CHROME_DEBUG_PORT`, but shared files are still unsafe.

Stage 1, next: route `AUTOPAGE_DATA_DIR` into the log path, `completed_orders.*`,
`sumatra_pdf_cache.txt`, and generated workbooks. Then add one writer for the
accel workbook and Google Sheets rows (a queue or a file lock), not two bots
writing the same workbook.

Stage 2, only if one window must show both workers: replace the `self.app.bot`
singleton that `order_display_manager.py` and `functions/accel_mode.py` call with
an injected per-worker session object.

## Running two instances (after stage 1)

```
# worker 1
set AUTOPAGE_WORKER_ID=w1
set AUTOPAGE_CHROME_DEBUG_PORT=8989
set AUTOPAGE_DATA_DIR=..\run\w1
python autopage_MKII_ver5.x.x.py

# worker 2
set AUTOPAGE_WORKER_ID=w2
set AUTOPAGE_CHROME_DEBUG_PORT=8990
set AUTOPAGE_DATA_DIR=..\run\w2
python autopage_MKII_ver5.x.x.py
```

Each Chrome must be started with its own profile folder:

```
chrome.exe --remote-debugging-port=8989 --user-data-dir=%LOCALAPPDATA%\Autopage\chrome-w1 --no-first-run --no-default-browser-check
chrome.exe --remote-debugging-port=8990 --user-data-dir=%LOCALAPPDATA%\Autopage\chrome-w2 --no-first-run --no-default-browser-check
```

Keep the debugging port on `127.0.0.1` only. Any local process that reaches it
can drive the browser that is logged into SMCO.

## Verification checklist for a real twin run

- Each instance logs `browser attach host=... port=... worker=...` with its own
  port, and `get_tabs` lists only its own tabs.
- Two SMCO sessions on the same account do not fight over the cart or the
  invoice number. If they do, serialise per account or use one account per
  worker.
- One instance can be stopped and restarted without disturbing the other's
  driver, tabs or printing.
- Printing goes to the intended printer queue per worker.
- Both workers' completed orders appear once, in the shared report.
