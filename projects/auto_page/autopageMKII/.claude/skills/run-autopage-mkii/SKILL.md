---
name: run-autopage-mkii
description: Run, launch, start, drive, screenshot and test the autopageMKII Tkinter GUI (SMCO POS order bot for Shopee/Lazada). Use when asked to run autopage, start the app, import an order file, click Start, take a screenshot of the window, or confirm a change works in the real GUI.
---

# run-autopage-mkii

Paths below are relative to the unit `projects/auto_page/autopageMKII/`. Windows only (Tkinter, win32, Chrome).

The app (`autopage_MKII_ver5.x.x.py`, class `MyApp`) is a Tk GUI that drives Chrome through Selenium against the SMCO POS site. The driver runs the **real** GUI in one process, against a local mock SMCO on `127.0.0.1:8765` and a dedicated test Chrome on port `8990`, and takes commands on `127.0.0.1:8791`.

## Run (agent path, use this first)

Check the imports (one line, prints `ok`):

```
python -c "import customtkinter, selenium, pandas, openpyxl, PIL, win32api, pdfplumber, googletrans, loguru; print('ok')"
```

Pick the browser first.

**A. Your logged-in browser on 8989 (preferred for UAT tests).** Use the Chrome that the user has already opened with remote debugging on 8989 and logged in to SMCO. Its page is the UAT POS, and it has no real data. The driver attaches to it and never launches or closes it. Only do this when the user has confirmed the bot is not running. Start the driver detached:

```
Start-Process -FilePath python -ArgumentList @('-u','.claude/skills/run-autopage-mkii/driver.py','serve','--chrome-port','8989') -WorkingDirectory (Get-Location) -RedirectStandardOutput "$env:TEMP\autopage-driver.log" -RedirectStandardError "$env:TEMP\autopage-driver.err.log"
```

**B. Driver-launched test Chrome on 8990 (default, no login).** It opens the local mock SMCO. Use it when the user's browser is not available. Start it with the same command, without `--chrome-port 8989`. Keep `--allow-live-bot` only if you have a reason to run it while the production bot's Chrome is up on 8989. Without that, the driver refuses to start.

Both commands block, so they are started detached.

Drive it with `send`, one command per call:

```
python .claude/skills/run-autopage-mkii/driver.py send state
python .claude/skills/run-autopage-mkii/driver.py send import
python .claude/skills/run-autopage-mkii/driver.py send "type inp1_order_input 2609032XS86R91"
python .claude/skills/run-autopage-mkii/driver.py send "click inp1_search_btn"
python .claude/skills/run-autopage-mkii/driver.py send "pump 8"
python .claude/skills/run-autopage-mkii/driver.py send ss
python .claude/skills/run-autopage-mkii/driver.py send dialogs
```

- `import` loads the mock Shopee fixture (`tests/mock_smco/mock_smco/fixtures/mock_orders.xlsx`, 2 rows).
- `click inp1_search_btn` is the Start button. After it, `pump N` lets the Tk loop run, then `state` shows the bot status.
- `ss` writes `%TEMP%\autopage-driver\app.png`. Open that file and look at it; do not claim success from the command alone.
- `dialogs` lists the messageboxes the driver answered for you.

Commands: `state`, `import [xlsx]`, `type <attr> <text>`, `click <attr>`, `pump [sec]`, `ss [path]`, `ssfull [path]`, `eval <expr>` (names `app`, `root`, `mod`), `exec <code>` (multi-statement, one line; put a script file in `%TEMP%` and run `exec exec(open(r'C:/...script.py').read())`), `dialogs`, `quit`.

To time a UI action, open the window with `exec`, then `pump` and read the widget text. The CP Patterns viewer is `mod.open_cp_pattern_window(app)`. Give entries focus, then send `<KeyRelease>` to the inner tk entry (`entry._entry`), not the CTkEntry.

Check where the attached browser is with `send "eval app.bot.driver.current_url"`. Stop the driver with `python .claude/skills/run-autopage-mkii/driver.py send quit`. This stops the GUI only. An attached browser stays open.

**Side effect (A):** Start moves the attached browser from its current page to the UAT POS (`posmainv3.htm`). Expect the tab to change.

Full options and safety notes are in the docstring at the top of `driver.py`.

## Run (human path)

`python autopage_MKII_ver5.x.x.py` opens the same GUI, but attaches to the live bot's Chrome on port 8989 and loads real SMCO sessions. Do not start it from an agent session. This path was not run during this skill's verification.

## Gotchas

- **Port 8989 is the production bot's Chrome.** `MyApp()` builds a `BrowserManager` that attaches to `RuntimeConfig.chrome_debug_port`, which defaults to 8989 unless `AUTOPAGE_CHROME_DEBUG_PORT` is set. The driver patches `BrowserManager.setup_chrome` to 8990 before constructing `MyApp`. Do not build `MyApp` any other way. `tests/mock_smco/gui_hang_launcher.py` builds `MyApp` *before* it stubs `setup_chrome`, so it attaches to 8989. Do not run it as-is.
- **Shared keyring session.** The app keeps its SMCO login in the Windows keyring under service `AutoSamaticMKII`. At start-up it clears the session if it is over 3600 s old. The driver uses `AutoSamaticMKII-driver` instead. A run without that isolation can clear the production session.
- **Modal messagebox on import.** Loading an order file whose SKUs are missing from `cp_data.xlsx` opens `askyesno("ยืนยันการเพิ่ม CP Data")`. Nobody clicks it, so the Tk thread blocks forever. The driver answers it **No** and logs it. Answering Yes would write into the real `cp_data.xlsx`.
- **`click` blocks the GUI thread.** Start runs `search_order` on the Tk thread (the real button does too). While it runs, `send` can time out or report "not reachable" even though the driver is alive. Wait, then run `state`. If it stays silent, read `%TEMP%\autopage-driver\stack_dump.txt`, which the watchdog writes after 10 s of silence.
- **Screenshots copy screen pixels.** `ss` raises the window to topmost first. Without that, the PNG shows whatever window is on top. `ssfull` includes everything on the desktop. Delete screenshots when you're done; they can show private data.
- **One driver at a time.** Port 8791 belongs to one process. A second `serve` is refused, and a stray client can leave a backlog.
- **Mock SMCO is shallow.** Every `.htm` returns `pos_page.html` and every POST returns `{"status":"ok"}`. The verified flow ends at Start (bot status `กำลังทำงาน`). Anything the bot does after that against the mock is not verified.
- **Chrome profile** for the test browser is `%TEMP%\autopage-driver\chrome-profile`. It is separate from the production profile `C:\bin\chromeProfile`.

## Troubleshooting

- `REFUSED: 127.0.0.1:8989 is listening` → the production bot's Chrome is up. Re-run `serve` with `--allow-live-bot` only if that is acceptable.
- `driver not reachable on 127.0.0.1:8791` → not started, or the Tk thread is blocked. Check `stack_dump.txt`. If it shows a `messagebox` frame, add that dialog to `_auto_dialog` in `driver.py`. Otherwise stop the process and start it again.
- `ss` fails with `FileNotFoundError` on a `/c/...` path → the driver runs under Windows Python, so pass `C:/...` paths, or no path.
- A screenshot shows another window → run `ss` again; the window is raised to topmost before the grab.
