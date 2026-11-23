# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Scope: this file covers `projects/auto_page/autopageMKII/`, the active project in the `Python` git repo. The rest of the repo is unrelated one-off scripts. Also read `AGENTS.md` here and at the repo root: they hold the TypeSafe/`jev` gating rules, which are not repeated below.

## Environment

- Windows only: Tkinter GUI, `win32api`/`win32print`, Chrome, SumatraPDF. Run commands from PowerShell or Git Bash.
- Dependencies come from the repo-root `requirements.txt` (no per-project lockfile). Quick import check used by the run skill:
  `python -c "import customtkinter, selenium, pandas, openpyxl, PIL, win32api, pdfplumber, googletrans, loguru; print('ok')"`
- Secrets live in `.env` (git-ignored). Keys read from env: `TYPESAFE_API_KEY`, `TYPESAFE_MODEL`, `TYPESAFE_TIMEOUT_S`, `TYPESAFE_MIN_CONFIDENCE`, `OPENJEV_*`, `IPS`, and per-instance `AUTOPAGE_WORKER_ID` / `AUTOPAGE_CHROME_DEBUG_HOST` / `AUTOPAGE_CHROME_DEBUG_PORT` / `AUTOPAGE_DATA_DIR` (see `autopage_config.py`). Never print or commit them.

## Commands

Run tests from the **repo root** (`C:\Users\Satawad_Ta\Documents\GitHub\Python`), not from this folder. Test files use `unittest`:

```
python -m unittest projects/auto_page/autopageMKII/tests/test_accel_mode_queue.py
python -m unittest projects/auto_page/autopageMKII/tests/test_cp_pattern_viewer_sort_search.py
python -m unittest discover -s projects/auto_page/autopageMKII/tests -p "test_*.py"   # full suite; runs well over 2 minutes, so run it in the background
```

- Known pre-existing failures (per the backlog in `CHANGELOG.md`, not caused by recent edits): `test_seller_voucher_pricing` (2 cases) and `test_cp_date_auto_correction` (loader error). Compare against these before blaming a change.
- `projects/pytest.ini` also exists (`testpaths` points at this `tests/` folder), but the suite is written for `unittest`.
- Syntax check after edits: `python -m py_compile <file>`.
- Package to exe: `powershell -File to_exe_tools/build_exe.ps1` (PyInstaller; default entry `autopage_MKII_ver5.3.0LITE.py`, name `AutopageMKIIver5.3.0LITE`). The root-level `.spec` file is stale (points at 5.0.1).

### Running the app

- Human path: `python autopage_MKII_ver5.x.x.py`. It attaches to the production bot's Chrome on port **8989** and drives the real SMCO POS. Do not start it from an agent session.
- Agent path for end-to-end checks: `.claude/skills/run-autopage-mkii/` (driver + SKILL.md). It runs the real GUI against a local mock SMCO on `127.0.0.1:8765` and a test Chrome on port `8990`, and is controlled through `driver.py send <cmd>`. Read its SKILL.md gotchas before use. In particular, importing an order whose SKUs are missing from `cp_data.xlsx` opens a modal `askyesno` that blocks the Tk thread, and the driver answers No.

## Working rules specific to this project

- Thai is the working language. Comments, logs, the changelog and most UI strings are Thai. Read and write all files as UTF-8 (`.editorconfig`); never save as cp874.
- Versioned copies of the app are kept side by side (`autopage_MKII_ver5_*LITE.py`, `ver4_*`, `ver3_*_UAT`). Edit **`autopage_MKII_ver5.x.x.py`**, the current development file. Treat the others as frozen snapshots unless asked.
- Before reporting a change done, run the related test module(s) under `tests/` and confirm they pass (`.agents/rules/testing_verification_rule.md`). Add or update a test when behavior changes.
- Log each fix in `CHANGELOG.md`: tick the backlog item `[x]`, and add the entry under section 3 with the date and `[ver5.x.x]` tag.
- `cp_data.xlsx`, `tables/Accel_mode*.xlsx` and `Addresscleaner_TambonData.xlsx` are live business data. Do not write to them while testing; use copies or the mock fixtures under `tests/mock_smco/`.

## Architecture (big picture)

**Single large GUI module, helpers in `functions/`.** `autopage_MKII_ver5.x.x.py` (~9.4k lines) defines `MyApp` (the customtkinter window) and the Selenium bot logic in the same class graph. Most business logic is split out into `functions/`:

- `browser_manager.py` — `BrowserManager` attaches to an already-running Chrome via its debug port (default 8989, from `RuntimeConfig` in `autopage_config.py`). It does not launch a fresh browser for production.
- `functions/pos/` — everything that drives SMCO POS forms and money: `pricing_engine.py` (~6.8k lines, `POSPricingReconciler`, `OrderFinancials`, CP/price/coupon rules), `payment_handler.py`, `customer_test_handler.py`, `cp_data_loader.py`, and `frontpage/smcoformhandler.py` (form filling).
- `accel_mode.py` (~2.5k lines) — batch mode. It reads an Accel order workbook from `tables/`, processes orders one at a time from a queue, and removes each row once it is saved. Saves are atomic and fall back to a direct write when the file is open in LibreOffice.
- `cp_pattern_viewer.py` — Tk viewer over the CP data workbook (sort/search, debounced input).
- `marketplace_scraper.py`, `tracking_manager.py`, `product_manager.py`, `auto_add_product.py`, `order_display_manager.py` — marketplace order intake (Shopee/Lazada), tracking numbers, SKU master handling, and display.
- `functions/utils/` — `crypto.py` (`AccountManager`, keyring-backed session), `helpers.py` (`resource_path` for PyInstaller), `report_manager.py`.

**Pipeline:** Excel/marketplace import → cleaning (`clean_address`, tax name formatting, phone fix) → SKU lookup and CP pricing (`pricing_engine`) → Bot fills customer, address, cart and payment in SMCO → tax-invoice PDF (base64) → silent print via SumatraPDF/Win32.

**Threads:** The Tk main thread must stay free. Bot work runs on background `threading.Thread`s started from `MyApp` (search for `threading.Thread(`). Anything that touches Tk widgets from a worker has to go back through the main loop. A blocked Tk thread is the usual cause of "driver not reachable" in the e2e tooling.

**Semi-auto by design:** the bot deliberately pauses in `while` loops and waits for the operator (barcode scan of SKUs, price/coupon adjustment, finish with F2). Do not "optimize" these waits away without checking the workflow in `README_autopage_MKII.md`.

**Safety-critical areas** (read the matching section of `CHANGELOG.md` section 2 first): order-state isolation between orders (`test_order_leak_guard.py`), SKU format and parsing, tax/customer name rules, and printing subprocesses.

**Auth:** SMCO login is stored in the Windows keyring under service `AutoSamaticMKII`. The e2e driver uses `AutoSamaticMKII-driver` so it cannot clear the production session.
