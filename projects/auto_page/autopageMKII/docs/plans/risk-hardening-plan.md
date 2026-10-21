# AutopageMKII risk hardening plan

Harden `autopage_MKII_ver5.x.x.py` against silent wrong invoices, unverified login, ambiguous coupon application, and unstable threading. The users are back-office operators who key Shopee and Lazada orders into SMCO POS. The next maintainer inherits a 9,259-line app with a green baseline, named failure categories, and a mock POS they can drive.

The program enforces one rule. No fix ships without unit, live, and perf evidence.

PR order. PR-01 and PR-02 are gates. PR-03 through PR-08 are ordered by risk.

## How to read this

One box is one unit of work. Every box names the evidence that checks it. A nested box is a sub-step of the box above it. Check a box only when its evidence exists, a file, a log line, a screenshot, a test run, or a SHA. The body is a how-to. The appendices explain and record.

The program runs `skills/poteto-mode/playbooks/autopilot-stack.md`. The installed copy is `C:\Users\Satawad_Ta\.cache\opencode\packages\@falentio\opencode-pstack@0.7.0\node_modules\@falentio\opencode-pstack\skills\poteto-mode\playbooks\autopilot-stack.md`. The operator reviews and lands every PR. All PR ids stop at merge-ready.

PR-01 and PR-02 are gates, not the top user risk. PR-01 makes the app runnable against the mock POS, so every later lane can produce evidence. PR-02 makes the trunk test suite green, so a new failure means a new bug. The risk order starts at PR-03.

Risk order after the gates.

1. PR-03, customer and tax data.
2. PR-04, login and transport.
3. PR-05, coupon and price.
4. PR-06, bad input and broken UI paths.
5. PR-07, concurrency and cancellation.
6. PR-08, encoding and build hygiene.

Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

## Program checklist

### Arm the program

- [ ] State the protocol and this plan to the operator, then stop. Start execution only on her explicit go.
- [ ] On her go, write the goal file with this exact text. "Run `projects/auto_page/autopageMKII/docs/plans/risk-hardening-plan.md`. PR order is PR-01, PR-02, PR-03, PR-04, PR-05, PR-06, PR-07, PR-08. A PR is verified only when its unit, live, and perf boxes are all checked. The operator lands every PR. Done when all eight PRs are merge-ready, verified at their exact head SHAs, and appended to one linear stack."
- [ ] Read these from trunk at program start. Re-read them at every tick.
  - [ ] `git show origin/main:skills/poteto-mode/playbooks/autopilot-stack.md`
  - [ ] `git show origin/main:skills/swarm/SKILL.md`
  - [ ] `git show origin/main:skills/poteto-mode/playbooks/opening-a-pr.md`
  - [ ] `git show origin/main:skills/principle-prove-it-works/SKILL.md`
  - [ ] `git show origin/main:projects/auto_page/autopageMKII/AGENTS.md`
- [ ] Run the 30-minute audit tick as a background Task with sleep plus poll. Never leave the cadence to memory.
- [ ] Use this tick prompt, verbatim. "Re-read the execution playbook from trunk and the goal file. Audit the operation against both and fix drift in this tick. Probe every active lane and judge progress by side effects only. Stand down a stuck lane and dispatch its replacement now. Then send the operator a status message, whether or not anything changed, with the queue table of PR, owner, state, and head SHA, the verdicts since the last tick, what merged, open operator gates, and blockers."
- [ ] On the operator's hold or stand-down, send every owner a zero-writes order at once.

### Spawn owners

- [ ] Spawn one owner per PR with the full lifecycle the execution playbook names.
- [ ] Follow this dependency graph. Start dependent work only after its parent merges, or base it on the parent branch when the execution playbook stacks.
  - [ ] PR-01 and PR-02 are independent and first. Both branch from `main`.
  - [ ] PR-03 after PR-01 and PR-02.
  - [ ] PR-04 after PR-03.
  - [ ] PR-05 after PR-04.
  - [ ] PR-06 after PR-05.
  - [ ] PR-07 after PR-06.
  - [ ] PR-08 after PR-07.
- [ ] Hold the file boundaries. PR-01 touches only `autopage_config.py`, `functions/browser_manager.py`, `functions/pos/cp_data_loader.py`, `tools/ui_probe.py`, `tools/perf_probe.py`, `tests/test_config.py`, `.env.example`, and the config call sites in `autopage_MKII_ver5.x.x.py`.
- [ ] Hold the file boundaries. PR-02 touches only `tests/`, `scratch/test_record_completed_order_sn.py`, and `projects/pytest.ini`.
- [ ] Hold the file boundaries. PR-03 touches the customer, address, and tax regions of `autopage_MKII_ver5.x.x.py` and adds `tests/test_customer_match.py` and `tests/test_tax_roundtrip.py`.
- [ ] Hold the file boundaries. PR-04 touches `SmcoApiClient`, `UserAccount`, and `AccountManager` call sites in `autopage_MKII_ver5.x.x.py`, `functions/utils/crypto.py`, `tests/test_crypto_session.py`, and `tests/test_smco_api_client.py`.
- [ ] Hold the file boundaries. PR-05 touches `functions/pos/pricing_engine.py`, `functions/pos/cp_data_loader.py`, the `reconcile_and_verify` call site, `tests/test_coupon_date_suggestion.py`, `tests/test_preselected_coupon_recommendation.py`, and `tests/test_realtime_ambiguity_and_remark.py`.
- [ ] Hold the file boundaries. PR-06 touches `define_marketplace`, `select_excel`, `open_file_by_default`, `load_subdistrict_cache`, `update_mp_frame`, `on_thread_done`, `on_canvas_configure`, and `check_threads` in `autopage_MKII_ver5.x.x.py`, plus `tests/test_unit_autopage.py` if present.
- [ ] Hold the file boundaries. PR-07 touches `search_order`, `operation_start`, `auto_add_product_threaded`, `update_log`, `update_gui`, and the thread-status methods in `autopage_MKII_ver5.x.x.py`, plus `tests/test_thread_concurrency.py` and `tests/test_start_repress_hang.py`.
- [ ] Hold the file boundaries. PR-08 touches `AutopageMKIIver5.0.1LITE.spec`, `order_display_manager.py`, `tools/check_encoding.py`, `requirements-dev.txt`, and docs.
- [ ] Hold the review gate. PR-03, PR-04, PR-05, and PR-06 change an interaction. They wait for the operator's review in chat with screenshots and a video before merge.

### PR mechanics, for every PR

- [ ] Open the PR ready, never draft, with `gh pr create` and `draft: false`. For a stack, create one branch per PR and set each child base with `gh pr edit --base <parent-branch>`.
- [ ] Run the repo's lint and typecheck once before the PR-facing push. Push with hooks on.
- [ ] Load the no-comments skill before review.
- [ ] Triage every review-bot comment.
- [ ] Rebase onto current trunk before babysit and again before the merge-ready report.

### Verdict and merge, for every PR

- [ ] At the merge-ready head SHA, run the swarm per `skills/swarm/SKILL.md`. One gates lane. The ten live lanes from the PR's **Verify, live** block. The perf lane from its **Verify, perf** block. One audit lane that reads the diff and the receipts and distrusts the PR body.
- [ ] Clean only when every lane is `PASS`. Findings go back to the owner. A new head gets a fresh swarm and a fresh verdict.
- [ ] The root appends the PR to the one linear stack after a clean verdict. The operator lands the chain. No owner merges, enables auto-merge, or closes.
- [ ] Compare `git patch-id` at each verdict SHA against the rebased head. A changed patch id voids the verdict.

### Boot recipe, for every live lane

Each live lane runs at the PR head via the Task tool. The Tkinter window has no control skill in this package, so lanes drive it through `tools/ui_probe.py`, built in PR-01. The Chrome side is driven through the control-ui skill where the lane needs it.

- [ ] `git fetch origin <head-branch> && git checkout <head SHA>`.
- [ ] Start the mock POS with `python tests/mock_smco/mock_smco_server.py 8765`. Wait for `Mock SMCO server listening`.
- [ ] Start Chrome with `--remote-debugging-port=8989 --user-data-dir=%TEMP%\swarm-chrome`. Wait for port 8989 to accept connections.
- [ ] Start the app with `$env:AUTOPAGE_SMCO_ORIGIN="http://127.0.0.1:8765"; $env:AUTOPAGE_CHROME_DEBUG_PORT="8989"; python autopage_MKII_ver5.x.x.py`. Wait for the window title `Autosamatic`.
- [ ] Deliver input only through `python tools/ui_probe.py --scenario <slug> --shot /tmp/swarm-<pr-id>/worker-<n>/<slug>.png`. The probe clicks by widget text and fails on any unhandled exception in `logs/autopageMKII_log_YYYY_MM_DD.log`.
- [ ] Read only these diagnostics. The app log under `logs/`, the mock stdout, `logs/completed_orders.csv`, and the scenario fixture under `tests/fixtures/`.
- [ ] Save every screenshot to `/tmp/swarm-<pr-id>/worker-<n>/<slug>.png` and return the paths with the report.

## Isolate runtime settings behind one config seam (PR-01)

**Depends on.** None.

**Files.**

- [ ] Create `autopage_config.py`.
- [ ] Create `tools/ui_probe.py`.
- [ ] Create `tools/perf_probe.py`.
- [ ] Create `tests/test_config.py`.
- [ ] Create `.env.example`.
- [ ] Edit `autopage_MKII_ver5.x.x.py` at the origin and path call sites.
- [ ] Edit `functions/browser_manager.py`.
- [ ] Edit `functions/pos/cp_data_loader.py`.

**Build.**

- [ ] Add `RuntimeConfig` with `smco_origin`, `chrome_debug_host`, `chrome_debug_port`, `cp_table_path`, `gas_url`, `rd_vat_url`, and `session_ttl_s`.
- [ ] Read each value from the environment first, then `.env`, then the current literal as the default. Keep today's behavior when no value is set.
- [ ] Replace the hardcoded origin at `UserAccount.login` and `Bot_POS`, the Chrome host and port at `functions/browser_manager.py:18-19`, the GAS URL at `functions/pos/cp_data_loader.py:9`, and the RD VAT URL at `SmcoApiClient.get_vatinfo`.
- [ ] Build `tools/ui_probe.py` with named scenarios. Each scenario opens the app, drives widgets by text, and saves a screenshot. Exit code 1 on any failed step.
- [ ] Build `tools/perf_probe.py`. It starts the app, imports a fixture file, runs one mock order, and prints `startup_ms` and `order_cycle_ms` from log timestamps.

**You see.**

- [ ] With `AUTOPAGE_SMCO_ORIGIN=http://127.0.0.1:8765`, the app log starts with `config smco_origin=http://127.0.0.1:8765`.
- [ ] With `AUTOPAGE_CHROME_DEBUG_PORT=8989`, the log line reads `browser attach host=localhost port=8989`.
- [ ] `tools/ui_probe.py` writes a PNG and exits 0 for the `boot` scenario.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `tests/test_config.py` covers env over `.env` over default, an invalid port, a missing CP path, and an empty origin. Run `python -m pytest tests/test_config.py -q`.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on the inherited parent model at the PR head, per the boot recipe.

- [ ] Lane 1. Boot the app against the mock. Save `boot.png`. Pass when the title is `Autosamatic` and the log shows the mock origin.
- [ ] Lane 2. Import the Shopee fixture. Save `import-shopee.png`. Pass when `File located` shows the fixture name.
- [ ] Lane 3. Import the Lazada fixture. Save `import-lazada.png`. Pass when the generated `Laz.order.toship.*.xlsx` exists.cp874
- [ ] Lane 4. Enter a mock order and press Start. Save `order-start.png`. Pass when the status reaches `Your Turn`.
- [ ] Lane 5. Set an unreachable origin and press Start. Save `origin-error.png`. Pass when one error dialog appears and no traceback reaches the console.
- [ ] Lane 6. Override the Chrome port to 8989. Save `chrome-port.png`. Pass when the log shows the override and the driver attaches.
- [ ] Lane 7. Override the CP path to a fixture workbook. Save `cp-path.png`. Pass when the CP row shows the fixture basename.
- [ ] Lane 8. Override the GAS URL to the mock and load CP data. Save `gas-mock.png`. Pass when the mock receives one GET.
- [ ] Lane 9. Record `startup_ms` five times. Save `perf-startup.png`. Pass when the probe prints five numbers and no error.
- [ ] Lane 10. Kill Chrome and restart the app. Save `chrome-restart.png`. Pass when the log shows the reconnect path and no infinite retry.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Time from process start to the window title `Autosamatic`.
- [ ] Probe. `python tools/perf_probe.py --scenario startup` at trunk and at the head, interleaved, five runs each.
- [ ] Baseline. Record the trunk median from five runs first.
- [ ] Rule. Fail when the head median is more than 10 percent above the trunk median.

**Review gate.** None. PR-01 is not review-gated.

**Merge.**

- [ ] Root's clean verdict at the exact head SHA.
- [ ] Review triage done.
- [ ] Rebased onto current trunk after the verdict, patch-id unchanged.
- [ ] The root appends PR-01 to the stack. The operator lands the chain.

## Make the trunk suite green (PR-02)

**Depends on.** None.

**Files.**

- [ ] Edit `tests/test_baseurlfinder.py`.
- [ ] Edit `tests/test_coupon_date_suggestion.py`.
- [ ] Edit or move `scratch/test_record_completed_order_sn.py`.
- [ ] Edit `projects/pytest.ini` if a marker or path change is required.

**Build.**

- [ ] Run the six failures and record the root cause of each in the PR body. Fix the code when the test is right. Fix the test when the expectation is stale. Do not skip or delete coverage to get green.
- [ ] Move the scratch test under `tests/` or delete it with a reason in the PR body.
- [ ] Make the suite stable on a clean checkout with no `IPS` environment variable and no network.
- [ ] Fix the cp1252 stdout crash in `check_threads` at `autopage_MKII_ver5.x.x.py:3765` by replacing `print` with the existing logger.

**You see.**

- [ ] `python -m pytest -q` ends with `192 passed` and exit code 0.
- [ ] The same command on a shell with `PYTHONIOENCODING=cp1252` prints no `UnicodeEncodeError`.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Run `python -m pytest -q` from the repo root. Confirm 192 collected, 192 passed, 0 failed.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on the inherited parent model at the PR head, per the boot recipe.

- [ ] Lane 1. Boot the app. Save `boot.png`. Pass when the window opens and no exception is logged.
- [ ] Lane 2. Import the Shopee fixture. Save `shopee.png`. Pass when the product table has rows.
- [ ] Lane 3. Import the Lazada fixture. Save `lazada.png`. Pass when the product table has rows.
- [ ] Lane 4. Run one mock order to `Your Turn`. Save `your-turn.png`. Pass when the status text is `Your Turn`.
- [ ] Lane 5. Press Stop mid-order. Save `stop.png`. Pass when the status ends and no thread exception appears.
- [ ] Lane 6. Select a non-Excel file. Save `bad-file.png`. Pass when the app shows an error and stays open.
- [ ] Lane 7. Open the CP fixture. Save `cp.png`. Pass when the CP file label updates.
- [ ] Lane 8. Toggle Test Mode. Save `test-mode.png`. Pass when the checkpoint menu appears.
- [ ] Lane 9. Close the app. Save `close.png`. Pass when the process exits within 5 seconds.
- [ ] Lane 10. Reopen and restore the session. Save `restore.png`. Pass when the user id is restored and the password field is not shown in plain text.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Full suite wall time from `python -m pytest -q`.
- [ ] Probe. Run the suite three times at trunk and three times at the head, interleaved.
- [ ] Baseline. Record the trunk median first. The trunk run on 2026-10-21 was 86.55 seconds with 6 failures.
- [ ] Rule. Fail when the head median is more than 15 percent above the trunk median.

**Review gate.** None. PR-02 is not review-gated.

**Merge.**

- [ ] Root's clean verdict at the exact head SHA.
- [ ] Review triage done.
- [ ] Rebased onto current trunk after the verdict, patch-id unchanged.
- [ ] The root appends PR-02 to the stack. The operator lands the chain.

## Block silent customer and tax corruption (PR-03)

**Depends on.** PR-01, PR-02.

**Files.**

- [ ] Edit `autopage_MKII_ver5.x.x.py` at the customer and address regions.
- [ ] Edit `autopage_MKII_ver5.x.x.py` at `tax_address_corrector` and `tax_name_formatter`.
- [ ] Create `tests/test_customer_match.py`.
- [ ] Create `tests/test_tax_roundtrip.py`.

**Build.**

- [ ] Fix `cus_sub_district` at `:3466`. Read `.get()`, and treat `nan` and `""` as missing.
- [ ] Fix `open_edit_address_popup` at `:1791`. Pass `self.root` as the Tk master, not `self`.
- [ ] Add `CUSTOMER_MATCH_MIN_CONFIDENCE` and `CUSTOMER_AMBIGUOUS` to the failure categories.
- [ ] In auto-invoice, stop and ask when the best customer score is below the threshold, or when the top two scores differ by less than 0.05. Do not create a new customer in either case.
- [ ] After the tax form is filled, compare the tax name, tax id, branch code, subdistrict, district, and province against the order dict. On mismatch, fail with the field name and leave the cart unchanged.
- [ ] Log one line per decision, `customer decision=... reason=... score=... candidate_count=...`.

**You see.**

- [ ] An ambiguous fixture stops at `Your Turn` with `customer decision=ASK reason=ambiguous`.
- [ ] A tax fixture with a wrong branch code fails with `tax mismatch field=branch_code expected=00000 actual=00001`.
- [ ] The address edit button opens a window and saves a changed subdistrict.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `tests/test_customer_match.py` covers exact, fuzzy above threshold, fuzzy below threshold, two candidates within 0.05, and a missing name. `tests/test_tax_roundtrip.py` covers HQ, sub-branch, missing tax id, and a `nan` subdistrict. Run `python -m pytest tests/test_customer_match.py tests/test_tax_roundtrip.py -q`.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on the inherited parent model at the PR head, per the boot recipe.

- [ ] Lane 1. Existing customer with an exact name. Save `customer-exact.png`. Pass when the customer code in the log matches the fixture.
- [ ] Lane 2. Fuzzy name above threshold. Save `customer-fuzzy.png`. Pass when the accepted candidate is the fixture customer.
- [ ] Lane 3. Two candidates within 0.05. Save `customer-ambiguous.png`. Pass when the app stops and shows the two candidates.
- [ ] Lane 4. Unknown customer in auto-invoice. Save `customer-new-blocked.png`. Pass when no new customer is created.
- [ ] Lane 5. Unknown customer in manual mode. Save `customer-new-manual.png`. Pass when the add-customer modal opens.
- [ ] Lane 6. Tax invoice for HQ. Save `tax-hq.png`. Pass when branch code is blank and the branch type is `สำนักงานใหญ่`.
- [ ] Lane 7. Tax invoice for a sub-branch. Save `tax-branch.png`. Pass when the branch code is five digits and matches the fixture.
- [ ] Lane 8. Missing subdistrict in the order. Save `subdistrict-missing.png`. Pass when the app stops and names the missing field.
- [ ] Lane 9. Edit the address from the panel. Save `address-edit.png`. Pass when the popup opens and the save changes the visible address.
- [ ] Lane 10. Tax round-trip mismatch. Save `tax-mismatch.png`. Pass when the order is blocked before payment.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Time from Start to `Your Turn` for the tax fixture.
- [ ] Probe. `python tools/perf_probe.py --scenario tax-invoice` at the parent head and at the PR head, interleaved, five runs each.
- [ ] Baseline. Record the parent head median from five runs first.
- [ ] Rule. Fail when the head median is more than 10 percent above the parent median.

**Review gate.** The operator reviews before merge.

- [ ] Copy lane 3 and lane 10 screenshots into `projects/auto_page/autopageMKII/docs/media/pr-03-review-ambiguous.png` and `pr-03-review-tax-mismatch.png`.
- [ ] Record a 30 to 60 second video of the ambiguous customer stop and the tax mismatch block on a mock VM. Save it as `projects/auto_page/autopageMKII/docs/media/pr-03-review.mp4`.
- [ ] Post the screenshots and the video in chat. Stop at merge-ready. Wait for the operator's click.

**Merge.**

- [ ] Root's clean verdict at the exact head SHA.
- [ ] Review triage done.
- [ ] Rebased onto current trunk after the verdict, patch-id unchanged.
- [ ] The root appends PR-03 to the stack. The operator lands the chain.

## Validate login and stop disabling TLS (PR-04)

**Depends on.** PR-03.

**Files.**

- [ ] Edit `SmcoApiClient` and `UserAccount` in `autopage_MKII_ver5.x.x.py`.
- [ ] Edit `functions/utils/crypto.py`.
- [ ] Edit `tests/test_crypto_session.py`.
- [ ] Edit `tests/test_smco_api_client.py`.

**Build.**

- [ ] Make `UserAccount.update_btn` call `login()`. Accept only a 200 response with `MORE_BRANCH`. Show the failure and do not save the session.
- [ ] Remove the hardcoded `JSESSIONID` at `:135`. Take the cookie from the login response and fail closed when it is absent.
- [ ] Default to TLS verification. Allow `ALLOW_INSECURE_TLS=1` only through the config, and log `tls_verify=off` at warning level when it is set.
- [ ] Re-check the session age at `operation_start` and block the order with `SESSION_EXPIRED` when it is older than `session_ttl_s`.
- [ ] Keep the password out of logs. Test that `save_session` is not called on a failed login.

**You see.**

- [ ] A wrong password logs `login rejected status=401` and leaves `Logged in !!` off.
- [ ] A fresh app start with no saved session does not attempt an order.
- [ ] `ALLOW_INSECURE_TLS=1` logs `tls_verify=off` once per process.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `tests/test_smco_api_client.py` covers 200 with cookie, 200 without cookie, 401, timeout, and TLS verify on. `tests/test_crypto_session.py` covers no write on failure and expiry. Run `python -m pytest tests/test_smco_api_client.py tests/test_crypto_session.py -q`.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on the inherited parent model at the PR head, per the boot recipe.

- [ ] Lane 1. Valid login against the mock. Save `login-ok.png`. Pass when the button reads `Logged in !!`.
- [ ] Lane 2. Wrong password. Save `login-bad.png`. Pass when one error appears and no session is written.
- [ ] Lane 3. Mock returns 200 without a cookie. Save `login-no-cookie.png`. Pass when login fails closed.
- [ ] Lane 4. Mock is down. Save `login-down.png`. Pass when the error names the connection failure.
- [ ] Lane 5. Restore a session older than the TTL. Save `session-expired.png`. Pass when Start is blocked with `SESSION_EXPIRED`.
- [ ] Lane 6. Restore a fresh session. Save `session-ok.png`. Pass when Start proceeds.
- [ ] Lane 7. RD VAT call with TLS verify on. Save `tls-on.png`. Pass when the request uses the default CA store.
- [ ] Lane 8. Set `ALLOW_INSECURE_TLS=1`. Save `tls-off.png`. Pass when the warning appears once.
- [ ] Lane 9. Logout. Save `logout.png`. Pass when the session and password are cleared and Accel Mode is hidden.
- [ ] Lane 10. Failed login then successful login. Save `login-retry.png`. Pass when only the success writes the session.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Login round trip against the mock.
- [ ] Probe. `python tools/perf_probe.py --scenario login` at the parent head and at the PR head, interleaved, five runs each.
- [ ] Baseline. Record the parent head median from five runs first.
- [ ] Rule. Fail when the head median is more than 10 percent above the parent median.

**Review gate.** The operator reviews before merge.

- [ ] Copy lane 2 and lane 8 screenshots into `projects/auto_page/autopageMKII/docs/media/pr-04-review-login.png` and `pr-04-review-tls.png`.
- [ ] Record a 30 to 60 second video of the failed login and the TLS warning. Save it as `projects/auto_page/autopageMKII/docs/media/pr-04-review.mp4`.
- [ ] Post the screenshots and the video in chat. Stop at merge-ready. Wait for the operator's click.

**Merge.**

- [ ] Root's clean verdict at the exact head SHA.
- [ ] Review triage done.
- [ ] Rebased onto current trunk after the verdict, patch-id unchanged.
- [ ] The root appends PR-04 to the stack. The operator lands the chain.

## Stop auto-applying ambiguous coupons and prices (PR-05)

**Depends on.** PR-04.

**Files.**

- [ ] Edit `functions/pos/pricing_engine.py` at the candidate scoring and apply path.
- [ ] Edit `functions/pos/pricing_engine.py` at `reconcile_and_verify`.
- [ ] Edit `functions/pos/cp_data_loader.py` only if the candidate set needs a stable order.
- [ ] Edit the `reconcile_and_verify` call site in `autopage_MKII_ver5.x.x.py`.
- [ ] Edit the three coupon test files named in the file boundaries.

**Build.**

- [ ] Add `CP_SCORE_MARGIN` and `CP_PRICE_TOLERANCE` to the config. Default the margin to 50 score points and the tolerance to 0.05 THB.
- [ ] Block the order with `CP_AMBIGUOUS` when the top two candidates differ by less than the margin, or when their sale prices differ by less than the tolerance and their names differ.
- [ ] Do not raise on ambiguity. Set `is_skip=True`, leave the cart unchanged, and surface the candidate list in the UI.
- [ ] Write the decision to `logs/cp_decisions.jsonl` with order number, sku, chosen name, chosen price, alternatives, margin, and mode.
- [ ] Keep the admin override. An explicit pick clears the block for that SKU only.

**You see.**

- [ ] Two equal-price CPs produce `cp decision=BLOCKED candidates=2 margin=0`.
- [ ] A single exact CP produces `cp decision=APPLIED name=... price=...`.
- [ ] The blocked order stays at `Your Turn` and the cart is unchanged.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `tests/test_preselected_coupon_recommendation.py` covers exact match, equal pair, close pair, expired date, missing CP, and admin override. `tests/test_realtime_ambiguity_and_remark.py` covers the blocked order path. Run `python -m pytest tests/test_preselected_coupon_recommendation.py tests/test_realtime_ambiguity_and_remark.py -q`.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on the inherited parent model at the PR head, per the boot recipe.

- [ ] Lane 1. One exact CP. Save `cp-exact.png`. Pass when the CP is applied and the total matches the fixture.
- [ ] Lane 2. Two equal-price CPs. Save `cp-equal.png`. Pass when the order blocks and both candidates are visible.
- [ ] Lane 3. Two CPs inside the margin. Save `cp-close.png`. Pass when the order blocks.
- [ ] Lane 4. Admin picks the second candidate. Save `cp-override.png`. Pass when the second CP is applied and the block clears.
- [ ] Lane 5. No CP for the SKU. Save `cp-missing.png`. Pass when the order fails with `CP_MISSING`.
- [ ] Lane 6. Expired CP. Save `cp-expired.png`. Pass when the expired candidate is excluded.
- [ ] Lane 7. Combo coupon. Save `cp-combo.png`. Pass when the combo is applied once and the remark is not duplicated.
- [ ] Lane 8. Seller voucher plus CP. Save `cp-voucher.png`. Pass when the final total equals the fixture.
- [ ] Lane 9. Wrong cart price before reconcile. Save `cp-price.png`. Pass when the reconcile corrects it and logs the delta.
- [ ] Lane 10. Decision log. Save `cp-log.png`. Pass when `logs/cp_decisions.jsonl` has one row per SKU.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Reconcile time for a three-SKU order.
- [ ] Probe. `python tools/perf_probe.py --scenario reconcile` at the parent head and at the PR head, interleaved, five runs each.
- [ ] Baseline. Record the parent head median from five runs first.
- [ ] Rule. Fail when the head median is more than 10 percent above the parent median.

**Review gate.** The operator reviews before merge.

- [ ] Copy lane 2 and lane 4 screenshots into `projects/auto_page/autopageMKII/docs/media/pr-05-review-blocked.png` and `pr-05-review-override.png`.
- [ ] Record a 30 to 60 second video of the blocked coupon and the admin override. Save it as `projects/auto_page/autopageMKII/docs/media/pr-05-review.mp4`.
- [ ] Post the screenshots and the video in chat. Stop at merge-ready. Wait for the operator's click.

**Merge.**

- [ ] Root's clean verdict at the exact head SHA.
- [ ] Review triage done.
- [ ] Rebased onto current trunk after the verdict, patch-id unchanged.
- [ ] The root appends PR-05 to the stack. The operator lands the chain.

## Recover from bad input and remove dead UI paths (PR-06)

**Depends on.** PR-05.

**Files.**

- [ ] Edit `define_marketplace`, `select_excel`, and `open_file_by_default` in `autopage_MKII_ver5.x.x.py`.
- [ ] Edit `load_subdistrict_cache` in `autopage_MKII_ver5.x.x.py`.
- [ ] Delete `update_mp_frame`, `on_thread_done`, and the duplicate `on_canvas_configure`.
- [ ] Edit `check_threads` to use the logger.
- [ ] Edit `tests/test_unit_autopage.py` if present, and add focused tests in `tests/`.

**Build.**

- [ ] Make `define_marketplace` return a result object instead of indexing `matches[0]`. On no match, show one message and restore the previous file selection.
- [ ] Validate the workbook before `select_excel` updates any label.
- [ ] Make `open_file_by_default` stop calling `format_cp_excel` on order exports. Only CP workbooks get formatted.
- [ ] Make `load_subdistrict_cache` read the documented cache path or delete the dead path variable. Do not compute a path and ignore it.
- [ ] Delete the dead methods and the duplicate override. Confirm no caller remains with a grep and record it in the PR body.
- [ ] Replace the Thai `print` in `check_threads` with `logger.info`.

**You see.**

- [ ] Selecting a random `.xlsx` shows one error and keeps the previous marketplace and file label.
- [ ] Opening the order export does not rewrite it.
- [ ] The log no longer raises `UnicodeEncodeError` on a cp1252 console.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Add tests for no marketplace match, canceled dialog, wrong file type, dead-path removal, and the cp1252 console. Run `python -m pytest tests -q`.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on the inherited parent model at the PR head, per the boot recipe.

- [ ] Lane 1. Select a random workbook. Save `bad-marketplace.png`. Pass when one error appears and the old file stays selected.
- [ ] Lane 2. Cancel the file dialog. Save `cancel-dialog.png`. Pass when nothing changes.
- [ ] Lane 3. Valid Shopee fixture. Save `shopee-ok.png`. Pass when the table fills.
- [ ] Lane 4. Valid Lazada fixture. Save `lazada-ok.png`. Pass when the table fills and the derived workbook exists.
- [ ] Lane 5. Open the order export. Save `open-export.png`. Pass when the file is unchanged on disk.
- [ ] Lane 6. Open the CP workbook. Save `open-cp.png`. Pass when the formatted file opens.
- [ ] Lane 7. Missing subdistrict cache. Save `cache-missing.png`. Pass when the app falls back without a crash.
- [ ] Lane 8. Address edit popup. Save `address-popup.png`. Pass when it opens.
- [ ] Lane 9. Double Start. Save `double-start.png`. Pass when the second press is ignored or queued, not interleaved.
- [ ] Lane 10. Stop then Start. Save `stop-start.png`. Pass when the old cycle ends and the new cycle starts.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Import time for a 1,000-row fixture.
- [ ] Probe. `python tools/perf_probe.py --scenario import-1000` at the parent head and at the PR head, interleaved, five runs each.
- [ ] Baseline. Record the parent head median from five runs first.
- [ ] Rule. Fail when the head median is more than 10 percent above the parent median.

**Review gate.** The operator reviews before merge.

- [ ] Copy lane 1 and lane 8 screenshots into `projects/auto_page/autopageMKII/docs/media/pr-06-review-bad-input.png` and `pr-06-review-address.png`.
- [ ] Record a 30 to 60 second video of the bad file recovery and the address popup. Save it as `projects/auto_page/autopageMKII/docs/media/pr-06-review.mp4`.
- [ ] Post the screenshots and the video in chat. Stop at merge-ready. Wait for the operator's click.

**Merge.**

- [ ] Root's clean verdict at the exact head SHA.
- [ ] Review triage done.
- [ ] Rebased onto current trunk after the verdict, patch-id unchanged.
- [ ] The root appends PR-06 to the stack. The operator lands the chain.

## Make concurrency and cancellation explicit (PR-07)

**Depends on.** PR-06.

**Files.**

- [ ] Edit `search_order`, `operation_start`, and `auto_add_product_threaded` in `autopage_MKII_ver5.x.x.py`.
- [ ] Edit `update_log`, `update_gui`, `update_gui_remark`, and `update_gui_note`.
- [ ] Edit `tests/test_thread_concurrency.py` and `tests/test_start_repress_hang.py`.

**Build.**

- [ ] Add one reentrant lock for every WebDriver call. Wrap `get_tabs`, `operation_start`, and `auto_add_product_threaded`.
- [ ] Marshal every Tk write through `self.root.after(0, ...)`. Do not touch a widget from a worker thread.
- [ ] Join the previous search and operation threads with a 2 second timeout before starting a new cycle. Log `cycle join timeout=2s` when the join fails.
- [ ] Capture worker exceptions and write them to the log and the status label. Do not let a daemon thread die silently.
- [ ] Keep the generation counter. Add one test that starts a new cycle while the old one is mid-order.

**You see.**

- [ ] Twenty Start and Stop cycles leave zero live worker threads.
- [ ] No `RuntimeError: main thread is not in main loop` appears in the log.
- [ ] A driver death surfaces as one error and one reconnect attempt, not an infinite loop.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `tests/test_thread_concurrency.py` covers the lock, the Tk marshal, and the join timeout. `tests/test_start_repress_hang.py` covers repress then Stop. Run `python -m pytest tests/test_thread_concurrency.py tests/test_start_repress_hang.py -q`.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on the inherited parent model at the PR head, per the boot recipe.

- [ ] Lane 1. Press Start twice within 200 ms. Save `double-start.png`. Pass when one order runs and the second press is rejected.
- [ ] Lane 2. Stop mid-order. Save `stop-mid.png`. Pass when the driver stops within 2 seconds.
- [ ] Lane 3. Refresh the POS page mid-order. Save `refresh-mid.png`. Pass when the refresh path recovers or fails once, without a loop.
- [ ] Lane 4. Skip an accel order. Save `accel-skip.png`. Pass when the next order starts cleanly.
- [ ] Lane 5. Delete an accel order. Save `accel-delete.png`. Pass when it is removed from the queue and the next order starts.
- [ ] Lane 6. Two POS tabs. Save `two-tabs.png`. Pass when the bot uses the SMCO tab and leaves the other tab alone.
- [ ] Lane 7. Kill Chrome mid-order. Save `chrome-death.png`. Pass when the log shows one classified death and no retry storm.
- [ ] Lane 8. Reconnect. Save `reconnect.png`. Pass when the next order runs.
- [ ] Lane 9. Reset memory while idle. Save `memory-reset.png`. Pass when the app stays responsive.
- [ ] Lane 10. Twenty Start and Stop cycles. Save `stress-20.png`. Pass when the thread count returns to baseline and the log has no Tk error.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Start to `Your Turn` for the standard fixture.
- [ ] Probe. `python tools/perf_probe.py --scenario order-cycle` at the parent head and at the PR head, interleaved, five runs each.
- [ ] Baseline. Record the parent head median from five runs first.
- [ ] Rule. Fail when the head median is more than 10 percent above the parent median.

**Review gate.** None. PR-07 is not review-gated.

**Merge.**

- [ ] Root's clean verdict at the exact head SHA.
- [ ] Review triage done.
- [ ] Rebased onto current trunk after the verdict, patch-id unchanged.
- [ ] The root appends PR-07 to the stack. The operator lands the chain.

## Fix encoding and build hygiene (PR-08)

**Depends on.** PR-07.

**Files.**

- [ ] Create `tools/check_encoding.py`.
- [ ] Create `requirements-dev.txt`.
- [ ] Edit `AutopageMKIIver5.0.1LITE.spec`.
- [ ] Delete or repair `order_display_manager.py`.
- [ ] Edit `README_autopage_MKII.md` with the run and test commands.

**Build.**

- [ ] Add `tools/check_encoding.py`. It accepts UTF-8 files, reports the legacy cp874 main file as an allowed exception, and fails on any new non-UTF-8 file.
- [ ] Point the spec entry at `autopage_MKII_ver5.x.x.py` and list the `functions` package, the assets, and the tables.
- [ ] Delete the broken root shim, or make it re-export the real class with no swallowed `ImportError`.
- [ ] Add `requirements-dev.txt` with `pytest` and the version used at trunk.
- [ ] Write the run command, the test command, and the mock command in the README.

**You see.**

- [ ] `python tools/check_encoding.py` exits 0 and prints one allowed legacy file.
- [ ] The built exe launches and reaches the main window.
- [ ] `from order_display_manager import OrderDisplayManager` works or the file is gone.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Add a test for the encoding checker and the shim. Run `python -m pytest tests -q` and `python tools/check_encoding.py`.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on the inherited parent model at the PR head, per the boot recipe.

- [ ] Lane 1. Build the exe from the spec. Save `build.png`. Pass when the build exits 0.
- [ ] Lane 2. Launch the exe. Save `exe-boot.png`. Pass when the main window opens.
- [ ] Lane 3. Import a fixture in the exe. Save `exe-import.png`. Pass when rows appear.
- [ ] Lane 4. Run one mock order in the exe. Save `exe-order.png`. Pass when it reaches `Your Turn`.
- [ ] Lane 5. Open the CP file in the exe. Save `exe-cp.png`. Pass when the label updates.
- [ ] Lane 6. Launch from a path with a space. Save `exe-space.png`. Pass when it opens.
- [ ] Lane 7. Delete the temp Chrome profile and launch. Save `exe-no-profile.png`. Pass when the app reports the missing debug port once.
- [ ] Lane 8. Run the encoding checker. Save `encoding.png`. Pass when it exits 0.
- [ ] Lane 9. Import `OrderDisplayManager`. Save `shim.png`. Pass when the class imports.
- [ ] Lane 10. Run the README commands on a clean shell. Save `readme.png`. Pass when each command exits 0.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Time from exe start to the main window.
- [ ] Probe. `python tools/perf_probe.py --scenario exe-startup` at the parent head and at the PR head, interleaved, five runs each.
- [ ] Baseline. Record the parent head median from five runs first.
- [ ] Rule. Fail when the head median is more than 10 percent above the parent median.

**Review gate.** None. PR-08 is not review-gated.

**Merge.**

- [ ] Root's clean verdict at the exact head SHA.
- [ ] Review triage done.
- [ ] Rebased onto current trunk after the verdict, patch-id unchanged.
- [ ] The root appends PR-08 to the stack. The operator lands the chain.

## Close the program

- [ ] Every box above is checked with its evidence.
- [ ] Reply to the operator with the report the execution playbook names.

## Appendix A. Prototype evidence

No prototype branch was created. These probes ran on 2026-10-21 against the working tree.

- `python -m pytest -q` collected 192 tests and ended with 6 failed, 186 passed, 46 warnings in 86.55 seconds. The failures are `scratch/test_record_completed_order_sn.py`, three in `tests/test_baseurlfinder.py`, and two in `tests/test_coupon_date_suggestion.py`.
- `python -m pytest --collect-only -q` reports rootdir `projects` and configfile `projects/pytest.ini`.
- `tests/mock_smco/mock_smco_server.py` serves `tests/mock_smco/assets/pos_page.html` on port 8765 and answers every POST with `{"status": "ok", "mock": true}`.
- The run also exposed a `UnicodeEncodeError` in `check_threads` at `autopage_MKII_ver5.x.x.py:3765` when stdout is cp1252.

Unproven until PR-01 lands. Whether `tools/ui_probe.py` can drive every widget on the operator's Windows build, and whether the mock page covers every selector the bot touches.

## Appendix B. Alternatives rejected

- Refactor `Bot_POS` first. It does not reduce the top data risk and it makes every later diff harder to review. Deferred until the behavior is covered by tests.
- Convert the whole source file to UTF-8 first. A 9,259-line diff with no runtime payoff hides the real changes. The encoding check in PR-08 prevents new offenders.
- Apply a low-confidence coupon with a warning. Auto invoice submits without a human, so a warning is not a control.
- Keep `verify=False` for the internal POS. It becomes an explicit dev flag instead of the default.
- Skip the failing tests to get a green suite. It hides the baseline and defeats PR-02.

## Appendix C. Risks

| Risk                                          | PR that covers it | What the owner watches                                                     |
| --------------------------------------------- | ----------------- | -------------------------------------------------------------------------- |
| Wrong customer or tax invoice reaches the POS | PR-03             | Ambiguity rate in`logs/cp_decisions.jsonl` and the customer decision log |
| Wrong account enters orders                   | PR-04             | Login failures and session expiry blocks                                   |
| Ambiguous coupon undercharges or overcharges  | PR-05             | `CP_AMBIGUOUS` rate and admin overrides                                  |
| Operator blocked by a bad file                | PR-06             | Error dialog count and recovery                                            |
| Interleaved orders or dead threads            | PR-07             | Thread count after 20 cycles                                               |
| Build ships the wrong entry file              | PR-08             | Spec entry and exe smoke test                                              |
| No control skill for Tkinter                  | PR-01             | `tools/ui_probe.py` coverage of every lane                               |
| Mock POS misses a selector                    | PR-01             | Lane failures that name the missing element                                |
| Live lanes touch real customer data           | All live PRs      | Fixtures only, no production workbook                                      |

## Appendix D. Links and reading list

- `projects/auto_page/autopageMKII/AGENTS.md`
- `projects/auto_page/autopageMKII/README_autopage_MKII.md`
- `projects/auto_page/autopageMKII/functions/pos/pricing_engine.py`
- `projects/auto_page/autopageMKII/functions/pos/payment_handler.py`
- `projects/auto_page/autopageMKII/functions/browser_manager.py`
- `projects/auto_page/autopageMKII/tests/mock_smco/mock_smco_server.py`
- PR-03, PR-04, and PR-05 get `skills/how/SKILL.md` and `skills/interrogate/SKILL.md` before the owner edits.
- Every owner keeps a `decisions.tsv` trail per `skills/show-me-your-work/SKILL.md`. The trail stays local and returns in the owner report.
