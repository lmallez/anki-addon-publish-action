import argparse
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from anki_addon_publish_action import __main__ as main


class EncodeLoginPayloadTests(unittest.TestCase):
    def test_uses_varint_length_encoding(self) -> None:
        username = "u" * 130
        payload = main.encode_login_payload(username, "pw")

        self.assertEqual(payload[0], 0x0A)
        self.assertEqual(payload[1:3], bytes([0x82, 0x01]))

    def test_encodes_expected_small_payload(self) -> None:
        self.assertEqual(
            main.encode_login_payload("a", "b"),
            bytes([0x0A, 0x01, 0x61, 0x12, 0x01, 0x62]),
        )

    def test_build_upload_payload_includes_id_for_updates(self) -> None:
        payload = main.build_upload_payload(123, "Demo", "", "", "Desc", b"PK")

        self.assertEqual(
            payload,
            bytes(
                [
                    0x0A,
                    0x14,
                    0x08,
                    0x7B,
                    0x12,
                    0x04,
                    0x44,
                    0x65,
                    0x6D,
                    0x6F,
                    0x2A,
                    0x04,
                    0x44,
                    0x65,
                    0x73,
                    0x63,
                    0x32,
                    0x04,
                    0x08,
                    0x01,
                    0x10,
                    0x01,
                    0x12,
                    0x04,
                    0x0A,
                    0x02,
                    0x50,
                    0x4B,
                ]
            ),
        )

    def test_build_upload_payload_includes_tags_and_support_page(self) -> None:
        payload = main.build_upload_payload(
            123,
            "Demo",
            "demo,utility",
            "https://example.com/support",
            "Desc",
            b"PK",
        )

        self.assertEqual(
            payload,
            bytes(
                [
                    0x0A,
                    0x3F,
                    0x08,
                    0x7B,
                    0x12,
                    0x04,
                    0x44,
                    0x65,
                    0x6D,
                    0x6F,
                    0x1A,
                    0x0C,
                    0x64,
                    0x65,
                    0x6D,
                    0x6F,
                    0x2C,
                    0x75,
                    0x74,
                    0x69,
                    0x6C,
                    0x69,
                    0x74,
                    0x79,
                    0x22,
                    0x1B,
                    0x68,
                    0x74,
                    0x74,
                    0x70,
                    0x73,
                    0x3A,
                    0x2F,
                    0x2F,
                    0x65,
                    0x78,
                    0x61,
                    0x6D,
                    0x70,
                    0x6C,
                    0x65,
                    0x2E,
                    0x63,
                    0x6F,
                    0x6D,
                    0x2F,
                    0x73,
                    0x75,
                    0x70,
                    0x70,
                    0x6F,
                    0x72,
                    0x74,
                    0x2A,
                    0x04,
                    0x44,
                    0x65,
                    0x73,
                    0x63,
                    0x32,
                    0x04,
                    0x08,
                    0x01,
                    0x10,
                    0x01,
                    0x12,
                    0x04,
                    0x0A,
                    0x02,
                    0x50,
                    0x4B,
                ]
            ),
        )

    def test_build_upload_payload_omits_id_for_create_mode(self) -> None:
        payload = main.build_upload_payload(None, "Demo", "", "", "Desc", b"PK")

        self.assertEqual(
            payload,
            bytes(
                [
                    0x0A,
                    0x12,
                    0x12,
                    0x04,
                    0x44,
                    0x65,
                    0x6D,
                    0x6F,
                    0x2A,
                    0x04,
                    0x44,
                    0x65,
                    0x73,
                    0x63,
                    0x32,
                    0x04,
                    0x08,
                    0x01,
                    0x10,
                    0x01,
                    0x12,
                    0x04,
                    0x0A,
                    0x02,
                    0x50,
                    0x4B,
                ]
            ),
        )


class MainFlowTests(unittest.TestCase):
    def test_missing_file_raises_upload_error(self) -> None:
        with self.assertRaises(main.UploadError):
            main.validate_addon_path("/tmp/does-not-exist.ankiaddon")

    def test_missing_id_raises_upload_error(self) -> None:
        args = argparse.Namespace(
            addon_file="/tmp/demo.ankiaddon",
            id=None,
            create=False,
            name="Example Add-on",
            tags=None,
            support_page=None,
            description=None,
            description_file=None,
            base_url=main.DEFAULT_BASE_URL,
            timeout_seconds=None,
        )

        with self.assertRaisesRegex(main.UploadError, "Missing add-on id"):
            with mock.patch.dict(
                os.environ,
                {"ANKI_USER": "user@example.com", "ANKI_PASSWORD": "secret"},
                clear=False,
            ):
                main.resolve_config(args)

    def test_create_mode_is_rejected_in_github_actions(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".ankiaddon") as addon_file:
            args = argparse.Namespace(
                addon_file=addon_file.name,
                id=None,
                create=True,
                name="Example Add-on",
                tags=None,
                support_page=None,
                description=None,
                description_file=None,
                base_url=main.DEFAULT_BASE_URL,
                timeout_seconds=None,
            )

            with self.assertRaisesRegex(main.UploadError, "--create is only available outside GitHub Actions"):
                with mock.patch.dict(
                    os.environ,
                    {
                        "ANKI_USER": "user@example.com",
                        "ANKI_PASSWORD": "secret",
                        "GITHUB_ACTIONS": "true",
                    },
                    clear=False,
                ):
                    main.resolve_config(args)

    def test_invalid_addon_id_from_env_raises_upload_error(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".ankiaddon") as addon_file:
            args = argparse.Namespace(
                addon_file=addon_file.name,
                id=None,
                create=False,
                name="Example Add-on",
                tags=None,
                support_page=None,
                description=None,
                description_file=None,
                base_url=None,
                timeout_seconds=None,
            )

            with self.assertRaisesRegex(main.UploadError, r"Invalid ANKI_ADDON_ID"):
                with mock.patch.dict(
                    os.environ,
                    {
                        "ANKI_USER": "user@example.com",
                        "ANKI_PASSWORD": "secret",
                        "ANKI_ADDON_ID": "abc",
                    },
                    clear=False,
                ):
                    main.resolve_config(args)

    def test_invalid_timeout_from_env_raises_upload_error(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".ankiaddon") as addon_file:
            args = argparse.Namespace(
                addon_file=addon_file.name,
                id=123,
                create=False,
                name="Example Add-on",
                tags=None,
                support_page=None,
                description=None,
                description_file=None,
                base_url=None,
                timeout_seconds=None,
            )

            with self.assertRaisesRegex(main.UploadError, r"Invalid ANKI_TIMEOUT_SECONDS"):
                with mock.patch.dict(
                    os.environ,
                    {
                        "ANKI_USER": "user@example.com",
                        "ANKI_PASSWORD": "secret",
                        "ANKI_TIMEOUT_SECONDS": "abc",
                    },
                    clear=False,
                ):
                    main.resolve_config(args)

    def test_timeout_must_be_positive(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".ankiaddon") as addon_file:
            args = argparse.Namespace(
                addon_file=addon_file.name,
                id=123,
                create=False,
                name="Example Add-on",
                tags=None,
                support_page=None,
                description=None,
                description_file=None,
                base_url=None,
                timeout_seconds=0,
            )

            with self.assertRaisesRegex(main.UploadError, r"Invalid ANKI_TIMEOUT_SECONDS"):
                with mock.patch.dict(
                    os.environ,
                    {"ANKI_USER": "user@example.com", "ANKI_PASSWORD": "secret"},
                    clear=False,
                ):
                    main.resolve_config(args)

    def test_consume_env_removes_value_from_environment(self) -> None:
        with mock.patch.dict(os.environ, {"ANKI_PASSWORD": "secret"}, clear=False):
            self.assertEqual(main.consume_env("ANKI_PASSWORD"), "secret")
            self.assertNotIn("ANKI_PASSWORD", os.environ)

    def test_writes_github_output_when_present(self) -> None:
        with tempfile.NamedTemporaryFile() as output_file:
            with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": output_file.name}, clear=False):
                main.write_github_output("uploaded_file", "/tmp/demo.ankiaddon")
                output_file.flush()
                contents = Path(output_file.name).read_text(encoding="utf-8")

        self.assertEqual(contents, "uploaded_file=/tmp/demo.ankiaddon\n")

    def test_load_description_prefers_inline_value(self) -> None:
        self.assertEqual(main.load_description("Hello", None), "Hello")

    def test_load_description_returns_empty_without_value(self) -> None:
        self.assertEqual(main.load_description(None, None), "")

    def test_load_description_reads_from_file(self) -> None:
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8") as description_file:
            description_file.write("Hello from file\n")
            description_file.flush()

            self.assertEqual(main.load_description(None, description_file.name), "Hello from file")

    def test_load_description_rejects_both_inline_and_file(self) -> None:
        with tempfile.NamedTemporaryFile("w+", encoding="utf-8") as description_file:
            with self.assertRaisesRegex(main.UploadError, "Description is ambiguous"):
                main.load_description("Hello", description_file.name)

    def test_load_description_rejects_missing_file(self) -> None:
        with self.assertRaisesRegex(main.UploadError, "Description file does not exist"):
            main.load_description(None, "/tmp/does-not-exist-description.txt")


if __name__ == "__main__":
    unittest.main()
