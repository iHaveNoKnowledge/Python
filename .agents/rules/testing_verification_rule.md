# 🧪 Testing & Regression Verification Rule

Whenever modifying, refactoring, or optimizing any function across the codebase (especially in `functions/pos/`, `autopage_MKII_ver5.x.x.py`, or financial/order logic):

1. **Mandatory Test Execution**:
   - Always run the corresponding unit/integration test suites located in `projects/auto_page/autopageMKII/tests/` (e.g. `python -m unittest projects/auto_page/autopageMKII/tests/test_sonic_blow_cp_selector.py`).
   - Confirm all tests exit with `OK` / code 0.

2. **No Regression & Logic Integrity**:
   - Ensure modifications do not break existing workflows, locators, or safeguards (e.g., pure Selenium clicks without JS event bypasses, backdrop clearance, multi-SKU candidate matching).
   - If a function's logic is updated, update or add test cases to lock in the new correct behavior.

3. **Verify Before Finish**:
   - Never conclude a task or report completion until automated tests have passed.
