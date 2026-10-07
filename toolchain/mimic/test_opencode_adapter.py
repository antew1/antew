"""Checks for the output contract between Mimic and OpenCode."""
import importlib.util
import json
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "mimic_opencode.py"
SPEC = importlib.util.spec_from_file_location("mimic_opencode", SCRIPT)
ADAPTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPTER)


def event(kind, text=""):
    return json.dumps({"type": kind, "part": {"text": text}})


class OpenCodeOutputTests(unittest.TestCase):
    def test_python_text_is_extracted_without_status_events(self):
        output = "\n".join([
            "initializing",
            event("step_start"),
            event("text", "```python\ndef answer():\n    return 42\n```"),
            event("step_finish"),
        ])
        self.assertEqual(
            ADAPTER.python_from_events(output),
            "def answer():\n    return 42\n",
        )

    def test_provider_error_rejects_partial_code(self):
        output = "\n".join([event("text", "answer = 42"), event("error")])
        with self.assertRaisesRegex(RuntimeError, "provider error"):
            ADAPTER.python_from_events(output)

    def test_empty_or_invalid_code_cannot_be_reported_as_success(self):
        for output in (
            event("step_finish"),
            event("text", "This is an explanation, not Python."),
        ):
            with self.subTest(output=output):
                with self.assertRaises(RuntimeError):
                    ADAPTER.python_from_events(output)

    def test_provider_diagnostics_do_not_disclose_credentials(self):
        secret = "oc_sk_private_credential_do_not_log"
        raw = json.dumps({
            "type": "error",
            "error": {
                "name": "APICallError",
                "data": {
                    "statusCode": 401,
                    "message": secret,
                    "responseBody": secret,
                },
            },
        })
        self.assertEqual(ADAPTER.failure_detail(raw), "HTTP 401")
        with self.assertRaises(RuntimeError) as caught:
            ADAPTER.python_from_events(raw)
        self.assertNotIn(secret, str(caught.exception))


if __name__ == "__main__":
    unittest.main()

