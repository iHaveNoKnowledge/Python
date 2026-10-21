import importlib.util
import os
import sys

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

CHECKER_PATH = os.path.join(PROJECT_DIR, "tools", "check_encoding.py")


def load_checker():
    spec = importlib.util.spec_from_file_location("check_encoding", CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = load_checker()


def test_utf8_thai_file_passes(tmp_path):
    path = tmp_path / "thai_utf8.py"
    path.write_text("# คำนวณราคาออกบิลต่อชิ้น\n", encoding="utf-8")

    assert checker.check_file(str(path)) is None


def test_cp874_file_fails_with_hint(tmp_path):
    path = tmp_path / "thai_cp874.py"
    path.write_bytes("# คำนวณราคาออกบิลต่อชิ้น\n".encode("cp874"))

    reason = checker.check_file(str(path))

    assert reason is not None
    assert "not UTF-8" in reason
    assert "cp874" in reason


def test_main_exit_codes(tmp_path, capsys):
    good = tmp_path / "good"
    good.mkdir()
    (good / "ok.py").write_text("# ภาษาไทย\n", encoding="utf-8")

    assert checker.main(["check_encoding", str(good)]) == 0
    assert "OK 1 files are UTF-8" in capsys.readouterr().out

    (good / "bad.py").write_bytes("# ภาษาไทย\n".encode("cp874"))

    assert checker.main(["check_encoding", str(good)]) == 1
    output = capsys.readouterr().out
    assert "bad.py: not UTF-8" in output
    assert "1 of 2 files are not UTF-8" in output
