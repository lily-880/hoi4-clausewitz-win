#!/usr/bin/env python3
"""CLI boundary tests for the read-only input capture entry.

These tests never call the live capture() backend. Production SHA/PE/version
gates stay inside capture(); this module injects results or errors, or points
the undocumented test seam at a local callable. Live Windows capture is not
run here.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
CALLING = ROOT / "calling"
sys.path.insert(0, str(CALLING))

import input_capture_live as cli
from input_observation import ObservationError

SCRIPT = Path(cli.__file__).resolve()
BACKEND_MODULES = ("mem", "pe", "gamestate", "handle", "process", "config")
PREFIX_KEY = b"    finally:p.close()\r\n"
PREFIX_SHA256 = "3561ac297740742496c3650c7c801a312f56e0381ef34f1950f22150923ca2c4"
FILE_SHA256 = {
    "calling/input_loaded_fields.py":
        "1aecf151e7f221fa2f1a6b86b37a9d15bf2a44d0f7f649f552b2af8f808e65b5",
    "calling/input_observation.py":
        "27a9a3ad6cab8a419e423486948b8952f4f4ee2bdc9084787a514c126738ccd6",
    "calling/tables/generalissimo_input.schema.json":
        "9a941dd3931b635591582b0d2ba3fe7ab1ceb3554a2d30af54154e61071b45ee",
    "research/t201_full_capture_recursive_a.json":
        "88dff7111ab117a3d94c9d57a219c2e55b62c6108e6f62a20021c7f5d964147e",
    "research/t201_full_capture_recursive_b.json":
        "8f6bad1187e8a0adb8782211417afee9bd0f505b61eb96d92a49f5223d75bda7",
}
FIXTURES = (
    ROOT / "research" / "t201_full_capture_recursive_a.json",
    ROOT / "research" / "t201_full_capture_recursive_b.json",
)
SCHEMA_PATH = CALLING / "tables" / "generalissimo_input.schema.json"
LEGACY_KEYS = ("pid", "version", "units", "provinces", "templates", "complete_input")

for _name in BACKEND_MODULES:
    if _name in sys.modules:
        raise RuntimeError("backend imported during test import: %s" % _name)


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def one_json(text):
    if not isinstance(text, str) or not text.endswith("\n"):
        raise AssertionError("expected one JSON document ending in newline, got %r" % (text[:240],))
    value, end = json.JSONDecoder().raw_decode(text)
    if text[end:].strip() != "":
        raise AssertionError("extra stdout after JSON: %r" % text[end:end + 240])
    if text.count("\n") != 1:
        raise AssertionError("expected a single-line JSON document")
    return value


def minimal_result(complete=False, version="1.19.5.0.7c6c", pid=11, units=2,
                   provinces=3, templates=4):
    return {
        "pid": pid,
        "game_version": version,
        "read_only": True,
        "complete_input": complete,
        "observation": {
            "world": {
                "own_units": [{"unit_id": i} for i in range(units)],
                "provinces": [{"province_id": i} for i in range(provinces)],
            }
        },
        "evidence": {"template_handle_registry_checks": templates},
    }


def assert_no_backend_import(testcase, verbose_stderr):
    for name in BACKEND_MODULES:
        testcase.assertNotIn("import '%s'" % name, verbose_stderr)
        testcase.assertNotIn("import '%s." % name, verbose_stderr)


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self._saved_capture = cli.capture

        def bomb():
            raise AssertionError("refusing live capture()")

        cli.capture = bomb
        self._saved_env = os.environ.pop(cli._TEST_CAPTURE_ENV, None)
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        cli.capture = self._saved_capture
        if self._saved_env is None:
            os.environ.pop(cli._TEST_CAPTURE_ENV, None)
        else:
            os.environ[cli._TEST_CAPTURE_ENV] = self._saved_env
        self._tmp.cleanup()

    def invoke(self, argv, impl=None):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(list(argv), capture_impl=impl)
        return code, out.getvalue(), err.getvalue()

    def run_script(self, argv, *, seam=None, extra_env=None, verbose=False):
        env = os.environ.copy()
        env.pop(cli._TEST_CAPTURE_ENV, None)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        if seam:
            env[cli._TEST_CAPTURE_ENV] = seam
            env["PYTHONPATH"] = os.pathsep.join(
                [str(self.seam_dir), env.get("PYTHONPATH", "")]
            ).rstrip(os.pathsep)
        if extra_env:
            env.update(extra_env)
        cmd = [sys.executable]
        if verbose:
            cmd.append("-v")
        cmd.append(str(SCRIPT))
        cmd.extend(argv)
        return subprocess.run(
            cmd, cwd=self.tmp, env=env, capture_output=True,
            text=True, encoding="utf-8", check=False,
        )


class TestSourceGates(CliTestCase):
    def test_capture_prefix_and_reader_files_unchanged(self):
        data = SCRIPT.read_bytes()
        end = data.index(PREFIX_KEY) + len(PREFIX_KEY)
        self.assertEqual(hashlib.sha256(data[:end]).hexdigest(), PREFIX_SHA256)
        prefix = data[:end]
        for token in (
            b"exe_sha256", b"PE(", b"Draft202012Validator",
            b"'complete_input':False", b"version_verified=True",
            b"unknown executable fingerprint",
        ):
            self.assertIn(token, prefix)
        suffix = data[end:]
        for token in (
            b"skip-fingerprint", b"fake-live", b"fake_live",
            b"CLAUSEWITZ_ALLOW_POST", b"D:\\", b"D:/",
        ):
            self.assertNotIn(token, suffix)
        for rel, digest in FILE_SHA256.items():
            self.assertEqual(_sha256(ROOT / rel), digest, rel)

    def test_import_and_help_do_not_load_windows_backend(self):
        for name in BACKEND_MODULES:
            self.assertNotIn(name, sys.modules)
        code, stdout, stderr = self.invoke(["--help"])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(stderr, "")
        self.assertIn("--out", stdout)
        self.assertIn("--json", stdout)
        self.assertIn("incomplete_input", stdout)
        self.assertIn("fingerprint_mismatch", stdout)
        self.assertIn("export_failed", stdout)
        lowered = stdout.lower()
        self.assertNotIn("skip-fingerprint", lowered)
        self.assertNotIn("fake-live", lowered)
        self.assertNotIn(cli._TEST_CAPTURE_ENV, stdout)
        for name in BACKEND_MODULES:
            self.assertNotIn(name, sys.modules)


class TestUsage(CliTestCase):
    def test_missing_empty_invalid_and_unknown_do_not_call_capture(self):
        out = self.tmp / "out.json"
        out.write_text("KEEP", encoding="utf-8")

        def boom():
            raise AssertionError("capture called")

        cases = [
            ([], "missing_out", False),
            (["--out"], "invalid_args", False),
            (["--out="], "empty_out", False),
            (["--out", ""], "empty_out", False),
            (["--out", "   "], "empty_out", False),
            (["--out", "bad\x00name.json"], "invalid_out", False),
            (["--out", str(self.tmp)], "invalid_out", False),
            (["--skip-fingerprint", "--out", str(out)], "invalid_args", False),
            (["--fake-live", "--out", str(out)], "invalid_args", False),
            (["--json"], "missing_out", True),
            (["--json", "--out", ""], "empty_out", True),
            (["--json", "--out", str(self.tmp)], "invalid_out", True),
            (["--json", "--skip-fingerprint"], "invalid_args", True),
            (["--json", "--offline", "--out", str(out)], "invalid_args", True),
        ]
        for argv, code_name, machine in cases:
            with self.subTest(argv=argv):
                code, stdout, stderr = self.invoke(argv, impl=boom)
                self.assertEqual(code, cli.EXIT_USAGE)
                self.assertIn(code_name, stderr)
                self.assertNotIn("capture called", stderr)
                self.assertNotIn("Traceback", stdout)
                self.assertNotIn("Traceback", stderr)
                self.assertEqual(out.read_text(encoding="utf-8"), "KEEP")
                if machine:
                    doc = one_json(stdout)
                    self.assertEqual(doc["status"], "error")
                    self.assertEqual(doc["stage"], "usage")
                    self.assertEqual(doc["code"], code_name)
                    self.assertFalse(doc["artifact_written"])
                    self.assertFalse(doc["input_accepted"])
                    self.assertIs(doc["complete_input"], False)
                    self.assertEqual(doc["exit_code"], cli.EXIT_USAGE)
                    for absent in ("pid", "units", "provinces", "templates"):
                        self.assertNotIn(absent, doc)
                else:
                    self.assertEqual(stdout, "")
                    self.assertIn("usage:", stderr)

    def test_help_wins_over_json_and_does_not_emit_a_document(self):
        code, stdout, stderr = self.invoke(["--json", "--help"])
        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(stderr, "")
        self.assertIn("--json", stdout)
        with self.assertRaises(json.JSONDecodeError):
            json.loads(stdout)


class TestLegacyAndMachine(CliTestCase):
    def test_legacy_summary_keys_and_partial_exit_zero(self):
        out = self.tmp / "legacy.json"
        result = minimal_result()
        code, stdout, stderr = self.invoke(["--out", str(out)], impl=lambda: result)
        self.assertEqual(code, cli.EXIT_OK)
        self.assertEqual(stderr, "")
        doc = one_json(stdout)
        self.assertEqual(list(doc), list(LEGACY_KEYS))
        self.assertEqual(doc, {
            "pid": 11,
            "version": "1.19.5.0.7c6c",
            "units": 2,
            "provinces": 3,
            "templates": 4,
            "complete_input": False,
        })
        self.assertNotIn("status", doc)
        self.assertNotIn("artifact_written", doc)
        written = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(written, result)
        self.assertIs(written["complete_input"], False)

    def test_machine_partial_is_one_document_and_not_accepted(self):
        out = self.tmp / "machine.json"
        result = minimal_result()
        result["schema_validation"] = {"valid": False, "error_count": 52}
        code, stdout, stderr = self.invoke(
            ["--json", "--out", str(out)], impl=lambda: result)
        self.assertEqual(code, cli.EXIT_PARTIAL)
        self.assertEqual(stderr, "")
        doc = one_json(stdout)
        self.assertEqual(doc["status"], "partial")
        self.assertEqual(doc["stage"], "result")
        self.assertEqual(doc["code"], "incomplete_input")
        self.assertTrue(doc["artifact_written"])
        self.assertFalse(doc["input_accepted"])
        self.assertIs(doc["complete_input"], False)
        self.assertEqual(doc["exit_code"], cli.EXIT_PARTIAL)
        self.assertEqual(doc["schema_valid"], False)
        self.assertEqual(doc["schema_error_count"], 52)
        self.assertIn("not accepted", doc["message"])
        for key in LEGACY_KEYS:
            self.assertIn(key, doc)
        self.assertEqual(doc["out"], str(out))
        self.assertEqual(json.loads(out.read_text(encoding="utf-8")), result)

    def test_schema_valid_shape_stays_incomplete_unless_capture_says_so(self):
        out = self.tmp / "shape.json"
        shaped = minimal_result(complete=False)
        shaped["schema_validation"] = {"valid": True, "error_count": 0}
        code, stdout, stderr = self.invoke(
            ["--json", "--out", str(out)], impl=lambda: shaped)
        self.assertEqual(stderr, "")
        doc = one_json(stdout)
        self.assertEqual(code, cli.EXIT_PARTIAL)
        self.assertEqual(doc["status"], "partial")
        self.assertTrue(doc["schema_valid"])
        self.assertFalse(doc["input_accepted"])
        self.assertIs(doc["complete_input"], False)
        accepted = minimal_result(complete=True)
        out2 = self.tmp / "accepted.json"
        code2, stdout2, stderr2 = self.invoke(
            ["--out", str(out2), "--json"], impl=lambda: accepted)
        self.assertEqual(stderr2, "")
        doc2 = one_json(stdout2)
        self.assertEqual(code2, cli.EXIT_OK)
        self.assertEqual(doc2["status"], "complete")
        self.assertTrue(doc2["input_accepted"])
        self.assertIs(doc2["complete_input"], True)
        # The CLI does not invent this. capture() still hardcodes false.
        prefix = SCRIPT.read_bytes().split(PREFIX_KEY)[0]
        self.assertIn(b"'complete_input':False", prefix)

    def test_unicode_roundtrip_stdout_and_artifact(self):
        folder = self.tmp / "目录"
        folder.mkdir()
        out = folder / "捕获.json"
        result = minimal_result(version="1.19.5.0.测试")
        result["note"] = "未验证字段保持省略"
        code, stdout, stderr = self.invoke(
            ["--json", "--out", str(out)], impl=lambda: result)
        self.assertEqual(code, cli.EXIT_PARTIAL)
        self.assertEqual(stderr, "")
        self.assertNotIn("\\u", stdout)
        doc = one_json(stdout)
        self.assertEqual(doc["version"], "1.19.5.0.测试")
        self.assertTrue(str(out).endswith("捕获.json"))
        self.assertEqual(doc["out"], str(out))
        text = out.read_text(encoding="utf-8")
        self.assertIn("未验证字段保持省略", text)
        self.assertNotIn("\\u", text)
        self.assertEqual(json.loads(text)["note"], result["note"])

    def test_repeated_invocation_overwrites_and_stays_partial(self):
        out = self.tmp / "repeat.json"
        calls = []

        def impl():
            calls.append(len(calls) + 1)
            return minimal_result(pid=calls[-1])

        first = self.invoke(["--json", "--out", str(out)], impl=impl)
        second = self.invoke(["--json", "--out", str(out)], impl=impl)
        self.assertEqual(calls, [1, 2])
        self.assertEqual(first[0], cli.EXIT_PARTIAL)
        self.assertEqual(second[0], cli.EXIT_PARTIAL)
        self.assertEqual(one_json(first[1])["pid"], 1)
        self.assertEqual(one_json(second[1])["pid"], 2)
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["pid"], 2)
        legacy = self.invoke(["--out", str(out)], impl=impl)
        self.assertEqual(legacy[0], cli.EXIT_OK)
        self.assertEqual(one_json(legacy[1])["complete_input"], False)
        self.assertEqual(calls, [1, 2, 3])


class TestFailures(CliTestCase):
    def _assert_error(self, argv, impl, stage, code_name, exit_code, sentinel="KEEP"):
        out = self.tmp / "err.json"
        out.write_text(sentinel, encoding="utf-8")
        code, stdout, stderr = self.invoke(argv, impl=impl)
        self.assertEqual(code, exit_code)
        self.assertNotIn("Traceback", stdout)
        self.assertNotIn("Traceback", stderr)
        self.assertNotIn("refusing live capture", stderr)
        machine = "--json" in argv
        if machine:
            doc = one_json(stdout)
            self.assertEqual(doc["status"], "error")
            self.assertEqual(doc["stage"], stage)
            self.assertEqual(doc["code"], code_name)
            self.assertFalse(doc["artifact_written"])
            self.assertFalse(doc["input_accepted"])
            self.assertIs(doc["complete_input"], False)
            self.assertEqual(doc["exit_code"], exit_code)
            for absent in ("pid", "units", "provinces", "templates"):
                self.assertNotIn(absent, doc)
            self.assertNotEqual(doc["status"], "complete")
            self.assertNotEqual(doc["status"], "partial")
        else:
            self.assertEqual(stdout, "")
        self.assertIn(code_name, stderr)
        self.assertEqual(out.read_text(encoding="utf-8"), sentinel)
        return code, stdout, stderr

    def test_backend_fingerprint_permission_and_observation(self):
        def backend():
            raise ImportError("No module named mem")

        def fingerprint():
            raise ObservationError("unknown executable fingerprint; no layout reads")

        def denied():
            raise PermissionError(13, "Permission denied")

        def rejected():
            raise ObservationError("not in campaign map")

        def invalid():
            return {"complete_input": False}

        def not_bool():
            result = minimal_result()
            result["complete_input"] = "false"
            return result

        def internal():
            raise RuntimeError("backend down")

        specs = [
            (backend, "backend", "backend_unavailable"),
            (fingerprint, "fingerprint", "fingerprint_mismatch"),
            (denied, "backend", "permission_denied"),
            (rejected, "backend", "observation_rejected"),
            (invalid, "backend", "invalid_result"),
            (not_bool, "backend", "invalid_result"),
            (internal, "backend", "internal_error"),
        ]
        for impl, stage, code_name in specs:
            for machine in (False, True):
                argv = ["--out", str(self.tmp / "err.json")]
                if machine:
                    argv.insert(0, "--json")
                with self.subTest(code=code_name, machine=machine):
                    self._assert_error(argv, impl, stage, code_name, cli.EXIT_BACKEND)

    def test_bad_seam_does_not_fall_through_to_live_capture(self):
        out = self.tmp / "seam.json"
        os.environ[cli._TEST_CAPTURE_ENV] = "   "
        code, stdout, stderr = self.invoke(["--json", "--out", str(out)])
        doc = one_json(stdout)
        self.assertEqual(code, cli.EXIT_BACKEND)
        self.assertEqual(doc["code"], "backend_unavailable")
        self.assertIn("empty", doc["message"])
        self.assertNotIn("refusing live capture", stderr)
        self.assertFalse(out.exists())
        os.environ[cli._TEST_CAPTURE_ENV] = "input_cli_test_seam_missing:from_file"
        code, stdout, stderr = self.invoke(["--json", "--out", str(out)])
        doc = one_json(stdout)
        self.assertEqual(code, cli.EXIT_BACKEND)
        self.assertEqual(doc["stage"], "backend")
        self.assertNotIn("refusing live capture", stderr)
        self.assertFalse(out.exists())

    def test_output_io_and_permission_are_export_failures(self):
        missing = self.tmp / "missing-parent" / "out.json"
        calls = []
        code, stdout, stderr = self.invoke(
            ["--json", "--out", str(missing)],
            impl=lambda: calls.append(1) or minimal_result(),
        )
        self.assertEqual(calls, [1])
        self.assertEqual(code, cli.EXIT_EXPORT)
        doc = one_json(stdout)
        self.assertEqual(doc["stage"], "output")
        self.assertEqual(doc["code"], "export_failed")
        self.assertFalse(doc["artifact_written"])
        self.assertFalse(missing.exists())
        self.assertFalse(missing.parent.exists())
        self.assertNotIn("Traceback", stderr)

        existing = self.tmp / "locked.json"
        existing.write_text("KEEP", encoding="utf-8")
        with mock.patch.object(
            Path, "write_text", side_effect=PermissionError(13, "Permission denied")
        ):
            code, stdout, stderr = self.invoke(
                ["--json", "--out", str(existing)], impl=lambda: minimal_result())
        doc = one_json(stdout)
        self.assertEqual(code, cli.EXIT_EXPORT)
        self.assertEqual(doc["stage"], "output")
        self.assertEqual(doc["code"], "permission_denied")
        self.assertFalse(doc["artifact_written"])
        self.assertFalse(doc["input_accepted"])
        self.assertEqual(existing.read_text(encoding="utf-8"), "KEEP")

        with mock.patch.object(Path, "write_text", side_effect=OSError(28, "No space left")):
            code, stdout, stderr = self.invoke(
                ["--out", str(existing)], impl=lambda: minimal_result())
        self.assertEqual(code, cli.EXIT_EXPORT)
        self.assertEqual(stdout, "")
        self.assertIn("export_failed", stderr)
        self.assertEqual(existing.read_text(encoding="utf-8"), "KEEP")


class TestFixtures(CliTestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.validator = Draft202012Validator(cls.schema)

    def _assert_fixture(self, path):
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.assertIs(raw["complete_input"], False)
        self.assertIs(raw["read_only"], True)
        self.assertIs(raw["schema_validation"]["valid"], False)
        self.assertEqual(raw["schema_validation"]["error_count"], 52)
        stored = raw["schema_validation"]["errors"]
        self.assertEqual(len(stored), 52)
        self.assertTrue(all("required property" in err["message"] for err in stored))
        recomputed = list(self.validator.iter_errors(raw["observation"]))
        self.assertEqual(len(recomputed), 52)
        self.assertTrue(all("required property" in err.message for err in recomputed))
        self.assertIn("blocking_checks", raw)
        self.assertIn("omitted", raw["blocking_checks"]["provinces"])
        blob = json.dumps(raw, ensure_ascii=False)
        for token in (
            "isolated_omitted", "incomplete_types_omitted", "infantry_specials_omitted",
        ):
            self.assertIn(token, blob)
        return raw

    def test_both_full_fixtures_stay_incomplete_with_52_required_errors(self):
        seen = set()
        for path in FIXTURES:
            with self.subTest(path=path.name):
                self.assertEqual(
                    _sha256(path),
                    FILE_SHA256["research/" + path.name],
                )
                raw = self._assert_fixture(path)
                seen.add(path.name)
                out = self.tmp / path.name
                code, stdout, stderr = self.invoke(
                    ["--json", "--out", str(out)], impl=lambda raw=raw: raw)
                self.assertEqual(code, cli.EXIT_PARTIAL)
                self.assertEqual(stderr, "")
                doc = one_json(stdout)
                self.assertEqual(doc["status"], "partial")
                self.assertFalse(doc["input_accepted"])
                self.assertIs(doc["complete_input"], False)
                self.assertEqual(doc["schema_valid"], False)
                self.assertEqual(doc["schema_error_count"], 52)
                written = json.loads(out.read_text(encoding="utf-8"))
                self.assertEqual(written, raw)
                self.assertEqual(len(written["schema_validation"]["errors"]), 52)
                again = list(self.validator.iter_errors(written["observation"]))
                self.assertEqual(len(again), 52)
        self.assertEqual(len(seen), 2)


class TestSubprocess(CliTestCase):
    def setUp(self):
        super().setUp()
        self.seam_dir = self.tmp / "seam"
        self.seam_dir.mkdir()
        (self.seam_dir / "input_cli_test_seam.py").write_text(
            "import json, os\n"
            "from pathlib import Path\n"
            "\n"
            "def from_file():\n"
            "    return json.loads(Path(os.environ['CLI_RESULT_FILE']).read_text(encoding='utf-8'))\n"
            "\n"
            "def fingerprint():\n"
            "    from input_observation import ObservationError\n"
            "    raise ObservationError('unknown executable fingerprint; no layout reads')\n"
            "\n"
            "def backend_missing():\n"
            "    raise ImportError('No module named mem')\n"
            "\n"
            "def count_and_return():\n"
            "    path = Path(os.environ['CLI_COUNT_FILE'])\n"
            "    n = int(path.read_text(encoding='utf-8')) if path.exists() else 0\n"
            "    path.write_text(str(n + 1), encoding='utf-8')\n"
            "    return from_file()\n",
            encoding="utf-8",
        )
        (self.seam_dir / "input_cli_test_seam_trap.py").write_text(
            "raise RuntimeError('seam module imported')\n",
            encoding="utf-8",
        )

    def test_script_help_and_usage_without_windows_imports(self):
        help_run = self.run_script(["--help"], verbose=True)
        self.assertEqual(help_run.returncode, cli.EXIT_OK)
        self.assertIn("--out", help_run.stdout)
        self.assertIn("--json", help_run.stdout)
        self.assertIn("exit status:", help_run.stdout)
        assert_no_backend_import(self, help_run.stderr)
        self.assertNotIn("seam module imported", help_run.stderr)

        trapped = self.run_script(
            ["--help"], seam="input_cli_test_seam_trap:from_file", verbose=True)
        self.assertEqual(trapped.returncode, cli.EXIT_OK)
        self.assertNotIn("seam module imported", trapped.stdout + trapped.stderr)
        assert_no_backend_import(self, trapped.stderr)

        missing = self.run_script([], verbose=True)
        self.assertEqual(missing.returncode, cli.EXIT_USAGE)
        self.assertEqual(missing.stdout, "")
        self.assertIn("--out is required", missing.stderr)
        assert_no_backend_import(self, missing.stderr)

        machine = self.run_script(["--json"], verbose=True)
        self.assertEqual(machine.returncode, cli.EXIT_USAGE)
        doc = one_json(machine.stdout)
        self.assertEqual(doc["status"], "error")
        self.assertEqual(doc["stage"], "usage")
        self.assertEqual(doc["code"], "missing_out")
        self.assertNotIn('"status"', machine.stderr)
        assert_no_backend_import(self, machine.stderr)

        rejected = self.run_script(
            ["--skip-fingerprint", "--out", str(self.tmp / "x.json")],
            seam="input_cli_test_seam_trap:from_file",
            verbose=True,
        )
        self.assertEqual(rejected.returncode, cli.EXIT_USAGE)
        self.assertNotIn("seam module imported", rejected.stdout + rejected.stderr)
        assert_no_backend_import(self, rejected.stderr)

    def test_script_machine_and_legacy_roundtrip(self):
        result = minimal_result(version="1.19.5.0.测试")
        result_path = self.tmp / "result.json"
        result_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        out = self.tmp / "目录" / "捕获.json"
        out.parent.mkdir()
        env = {"CLI_RESULT_FILE": str(result_path)}
        legacy = self.run_script(
            ["--out", str(out)],
            seam="input_cli_test_seam:from_file",
            extra_env=env,
        )
        self.assertEqual(legacy.returncode, cli.EXIT_OK)
        self.assertEqual(legacy.stderr, "")
        summary = one_json(legacy.stdout)
        self.assertEqual(list(summary), list(LEGACY_KEYS))
        self.assertEqual(summary["version"], "1.19.5.0.测试")
        self.assertIs(summary["complete_input"], False)
        self.assertNotIn("\\u", legacy.stdout)

        machine = self.run_script(
            ["--json", "--out", str(out)],
            seam="input_cli_test_seam:from_file",
            extra_env=env,
            verbose=True,
        )
        self.assertEqual(machine.returncode, cli.EXIT_PARTIAL)
        doc = one_json(machine.stdout)
        self.assertEqual(doc["status"], "partial")
        self.assertEqual(doc["exit_code"], cli.EXIT_PARTIAL)
        self.assertFalse(doc["input_accepted"])
        self.assertEqual(doc["version"], "1.19.5.0.测试")
        self.assertNotIn("\\u", machine.stdout)
        assert_no_backend_import(self, machine.stderr)
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["game_version"], result["game_version"])

    def test_script_error_exit_codes(self):
        out = self.tmp / "no.json"
        fingerprint = self.run_script(
            ["--json", "--out", str(out)],
            seam="input_cli_test_seam:fingerprint",
            verbose=True,
        )
        self.assertEqual(fingerprint.returncode, cli.EXIT_BACKEND)
        doc = one_json(fingerprint.stdout)
        self.assertEqual(doc["stage"], "fingerprint")
        self.assertEqual(doc["code"], "fingerprint_mismatch")
        self.assertFalse(out.exists())
        assert_no_backend_import(self, fingerprint.stderr)
        self.assertNotIn('"status"', fingerprint.stderr)

        backend = self.run_script(
            ["--json", "--out", str(out)],
            seam="input_cli_test_seam:backend_missing",
            verbose=True,
        )
        self.assertEqual(backend.returncode, cli.EXIT_BACKEND)
        self.assertEqual(one_json(backend.stdout)["code"], "backend_unavailable")
        assert_no_backend_import(self, backend.stderr)

        missing_mod = self.run_script(
            ["--json", "--out", str(out)],
            seam="input_cli_test_seam_missing:from_file",
            verbose=True,
        )
        self.assertEqual(missing_mod.returncode, cli.EXIT_BACKEND)
        self.assertEqual(one_json(missing_mod.stdout)["stage"], "backend")
        self.assertFalse(out.exists())
        assert_no_backend_import(self, missing_mod.stderr)

        result_path = self.tmp / "result.json"
        result_path.write_text(json.dumps(minimal_result()), encoding="utf-8")
        export_out = self.tmp / "missing-parent" / "out.json"
        export = self.run_script(
            ["--json", "--out", str(export_out)],
            seam="input_cli_test_seam:count_and_return",
            extra_env={
                "CLI_RESULT_FILE": str(result_path),
                "CLI_COUNT_FILE": str(self.tmp / "count.txt"),
            },
            verbose=True,
        )
        self.assertEqual(export.returncode, cli.EXIT_EXPORT)
        doc = one_json(export.stdout)
        self.assertEqual(doc["stage"], "output")
        self.assertEqual(doc["code"], "export_failed")
        self.assertFalse(export_out.exists())
        self.assertEqual((self.tmp / "count.txt").read_text(encoding="utf-8"), "1")
        assert_no_backend_import(self, export.stderr)

    def test_script_repeated_fixture_roundtrip(self):
        count = self.tmp / "count.txt"
        for path in FIXTURES:
            out = self.tmp / ("out-" + path.name)
            exits = []
            for _ in range(2):
                proc = self.run_script(
                    ["--json", "--out", str(out)],
                    seam="input_cli_test_seam:count_and_return",
                    extra_env={
                        "CLI_RESULT_FILE": str(path),
                        "CLI_COUNT_FILE": str(count),
                    },
                )
                exits.append(proc.returncode)
                self.assertEqual(proc.stderr, "")
                doc = one_json(proc.stdout)
                self.assertEqual(doc["status"], "partial")
                self.assertEqual(doc["schema_error_count"], 52)
                self.assertIs(doc["schema_valid"], False)
                self.assertFalse(doc["input_accepted"])
                self.assertIs(doc["complete_input"], False)
            self.assertEqual(exits, [cli.EXIT_PARTIAL, cli.EXIT_PARTIAL])
            written = json.loads(out.read_text(encoding="utf-8"))
            original = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(written, original)
            self.assertEqual(len(written["schema_validation"]["errors"]), 52)
            self.assertIs(written["complete_input"], False)
        self.assertEqual(count.read_text(encoding="utf-8"), "4")


if __name__ == "__main__":
    unittest.main()
