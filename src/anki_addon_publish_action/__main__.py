import argparse
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeVar

import requests

DEFAULT_BASE_URL = "https://ankiweb.net"
LOGIN_PATH = "/svc/account/login"
UPLOAD_PATH = "/svc/shared/upload-addon"
USER_AGENT = "anki-addon-publish-action/1.0"
LOGGER = logging.getLogger("anki_upload")
T = TypeVar("T")


class UploadError(RuntimeError):
    """Raised when the upload flow cannot complete."""


@dataclass(frozen=True)
class UploadMetadata:
    addon_id: int | None
    name: str
    tags: str
    support_page: str

    def as_env(self) -> dict[str, str]:
        return {
            "ANKI_ADDON_ID": "" if self.addon_id is None else str(self.addon_id),
            "ANKI_NAME": self.name,
            "ANKI_TAGS": self.tags,
            "ANKI_SUPPORT_PAGE": self.support_page,
        }


@dataclass(frozen=True)
class ActionConfig:
    username: str
    password: str
    addon_path: Path
    metadata: UploadMetadata
    description: str
    base_url: str
    timeout_seconds: int


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="[anki-upload] %(message)s")


def encode_varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("Varint values must be non-negative")

    encoded = bytearray()
    while True:
        chunk = value & 0x7F
        value >>= 7
        if value:
            encoded.append(chunk | 0x80)
        else:
            encoded.append(chunk)
            return bytes(encoded)


def encode_length_delimited(field_tag: int, value: str) -> bytes:
    value_bytes = value.encode("utf-8")
    return bytes([field_tag]) + encode_varint(len(value_bytes)) + value_bytes


def encode_length_delimited_bytes(field_tag: int, value: bytes) -> bytes:
    return bytes([field_tag]) + encode_varint(len(value)) + value


def encode_varint_field(field_tag: int, value: int) -> bytes:
    return bytes([field_tag]) + encode_varint(value)


def encode_login_payload(username: str, password: str) -> bytes:
    return encode_length_delimited(0x0A, username) + encode_length_delimited(0x12, password)


def build_upload_metadata_payload(
    addon_id: int | None,
    name: str,
    tags: str,
    support_page: str,
    description: str,
) -> bytes:
    flags_message = encode_varint_field(0x08, 1) + encode_varint_field(0x10, 1)
    payload = bytearray()
    if addon_id is not None:
        payload.extend(encode_varint_field(0x08, addon_id))
    payload.extend(encode_length_delimited(0x12, name))
    if tags:
        payload.extend(encode_length_delimited(0x1A, tags))
    if support_page:
        payload.extend(encode_length_delimited(0x22, support_page))
    payload.extend(encode_length_delimited(0x2A, description))
    payload.extend(encode_length_delimited_bytes(0x32, flags_message))
    return bytes(payload)


def build_upload_payload(
    addon_id: int | None,
    name: str,
    tags: str,
    support_page: str,
    description: str,
    addon_bytes: bytes,
) -> bytes:
    metadata_message = build_upload_metadata_payload(
        addon_id,
        name,
        tags,
        support_page,
        description,
    )
    file_message = encode_length_delimited_bytes(0x0A, addon_bytes)
    return (
        encode_length_delimited_bytes(0x0A, metadata_message)
        + encode_length_delimited_bytes(0x12, file_message)
    )


def preview_response(response: requests.Response, limit: int = 200) -> str:
    content_type = response.headers.get("Content-Type", "")
    if "text" in content_type or "json" in content_type:
        text = response.text.strip().replace("\n", " ")
        return text[:limit]
    if len(response.content) <= 16:
        return f"{response.content.hex()} ({len(response.content)} bytes of {content_type or 'binary data'})"
    return f"<{len(response.content)} bytes of {content_type or 'binary data'}>"


def load_description(description: str | None) -> str:
    if description is not None:
        return description.strip()
    return ""


def write_github_output(name: str, value: Any) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return

    with open(output_path, "a", encoding="utf-8") as output_file:
        output_file.write(f"{name}={value}\n")


def resolve_setting(value: str | None, env_name: str) -> str | None:
    return value if value is not None else os.environ.get(env_name)


def consume_env(env_name: str) -> str | None:
    value = os.environ.get(env_name)
    if value is not None:
        os.environ.pop(env_name, None)
    return value


def resolve_int_setting(value: int | None, env_name: str, default: int) -> int:
    if value is not None:
        return value

    raw_value = os.environ.get(env_name)
    if raw_value is None:
        return default

    return parse_int_value(raw_value, env_name)


def parse_int_value(raw_value: str, setting_name: str, minimum: int | None = None) -> int:
    expected = "an integer" if minimum is None else "an integer greater than or equal to 1"
    try:
        value = int(raw_value)
    except ValueError as error:
        raise UploadError(
            f"Invalid {setting_name}: expected {expected}, got {raw_value!r}."
        ) from error

    if minimum is not None and value < minimum:
        raise UploadError(f"Invalid {setting_name}: expected {expected}, got {raw_value!r}.")

    return value


def validate_addon_path(raw_path: str) -> Path:
    addon_path = Path(raw_path).expanduser().resolve()
    if not addon_path.is_file():
        raise UploadError(f"Addon file does not exist: {addon_path}")
    return addon_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or update an AnkiWeb add-on with an .ankiaddon file"
    )
    parser.add_argument("--file", dest="addon_file", help="Path to the .ankiaddon file")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--id", type=int, help="Existing AnkiWeb add-on id to update")
    mode_group.add_argument(
        "--create",
        action="store_true",
        help="Create a new AnkiWeb add-on listing. CLI only, not available in GitHub Actions.",
    )
    parser.add_argument("--name", help="Add-on display name")
    parser.add_argument("--tags", help="Comma-separated add-on tags")
    parser.add_argument("--support-page", help="Support page URL")
    parser.add_argument("--description", help="Inline add-on description text")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="AnkiWeb base URL")
    parser.add_argument("--timeout-seconds", type=int, help="HTTP request timeout in seconds")
    return parser.parse_args()


def build_metadata(
    addon_id: int | None,
    name: str,
    tags: str | None,
    support_page: str | None,
    description: str | None,
) -> tuple[UploadMetadata, str]:
    metadata = UploadMetadata(
        addon_id=addon_id,
        name=name,
        tags=tags or "",
        support_page=support_page or "",
    )
    resolved_description = load_description(description)
    return metadata, resolved_description


def running_in_github_actions() -> bool:
    return os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def resolve_config(args: argparse.Namespace) -> ActionConfig:
    username = consume_env("ANKI_USER")
    password = consume_env("ANKI_PASSWORD")
    addon_file = resolve_setting(args.addon_file, "ANKI_ADDON_FILE")
    addon_id_value = resolve_setting(None if args.id is None else str(args.id), "ANKI_ADDON_ID")
    description = resolve_setting(args.description, "ANKI_DESCRIPTION")
    name = resolve_setting(args.name, "ANKI_NAME")
    tags = resolve_setting(args.tags, "ANKI_TAGS")
    support_page = resolve_setting(args.support_page, "ANKI_SUPPORT_PAGE")
    timeout_seconds = resolve_int_setting(args.timeout_seconds, "ANKI_TIMEOUT_SECONDS", 30)

    if not username or not password:
        raise UploadError("Missing Anki credentials. Set ANKI_USER and ANKI_PASSWORD.")
    if not addon_file:
        raise UploadError("Missing addon file. Set ANKI_ADDON_FILE or pass --file.")
    if args.create and running_in_github_actions():
        raise UploadError("--create is only available outside GitHub Actions.")
    if not args.create and not addon_id_value:
        raise UploadError("Missing add-on id. Set ANKI_ADDON_ID or pass --id.")
    if not name:
        raise UploadError("Missing name. Set ANKI_NAME or pass --name.")
    addon_id = None if args.create else parse_int_value(addon_id_value, "ANKI_ADDON_ID", minimum=1)
    if timeout_seconds < 1:
        raise UploadError(
            f"Invalid ANKI_TIMEOUT_SECONDS: expected an integer greater than or equal to 1, got {timeout_seconds!r}."
        )
    addon_path = validate_addon_path(addon_file)
    metadata, description = build_metadata(
        addon_id=addon_id,
        name=name,
        tags=tags,
        support_page=support_page,
        description=description,
    )

    return ActionConfig(
        username=username,
        password=password,
        addon_path=addon_path,
        metadata=metadata,
        description=description,
        base_url=args.base_url,
        timeout_seconds=timeout_seconds,
    )


class AnkiWebClient:
    def __init__(self, config: ActionConfig, session: requests.Session | None = None) -> None:
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.session = session or requests.Session()
        self.session.trust_env = False

    def _post(self, path: str, referer_path: str, data: bytes) -> requests.Response:
        return self.session.post(
            f"{self.base_url}{path}",
            headers={
                "Content-Type": "application/octet-stream",
                "Origin": self.base_url,
                "Referer": f"{self.base_url}{referer_path}",
                "User-Agent": USER_AGENT,
            },
            data=data,
            timeout=self.config.timeout_seconds,
        )

    def login(self) -> None:
        payload = encode_login_payload(self.config.username, self.config.password)
        response = self._post(LOGIN_PATH, "/account/login", payload)

        if response.status_code >= 400:
            raise UploadError(
                f"Login failed with HTTP {response.status_code}: {preview_response(response)}"
            )

        if not self.session.cookies.get_dict().get("ankiweb"):
            raise UploadError(
                "Login did not return an AnkiWeb session cookie "
                f"(HTTP {response.status_code}: {preview_response(response)}); "
                "credentials may be wrong or authentication may have changed"
            )

    def upload_addon(self) -> requests.Response:
        addon_bytes = self.config.addon_path.read_bytes()
        payload = build_upload_payload(
            self.config.metadata.addon_id,
            self.config.metadata.name,
            self.config.metadata.tags,
            self.config.metadata.support_page,
            self.config.description,
            addon_bytes,
        )

        if self.config.metadata.addon_id is None:
            referer_path = "/shared/upload"
        else:
            referer_path = f"/shared/upload?id={self.config.metadata.addon_id}"
        response = self._post(UPLOAD_PATH, referer_path, payload)

        if response.status_code >= 400:
            raise UploadError(
                f"Upload failed with HTTP {response.status_code}: {preview_response(response)}"
            )

        return response


def run_once(action_name: str, operation: Callable[[], T]) -> T:
    try:
        LOGGER.info("%s attempt 1/1", action_name)
        return operation()
    except (requests.RequestException, UploadError) as error:
        LOGGER.warning("%s failed: %s", action_name, error)
        raise UploadError(f"{action_name} failed after 1 attempt(s): {error}") from error


def write_outputs(config: ActionConfig) -> None:
    write_github_output("uploaded_file", str(config.addon_path))
    write_github_output("name", config.metadata.name)


def run(config: ActionConfig) -> int:
    LOGGER.info("Preparing upload for %s", config.addon_path.name)

    client = AnkiWebClient(config)
    try:
        run_once("Login", client.login)
        response = run_once("Upload", client.upload_addon)
        LOGGER.info("Upload completed with HTTP %s", response.status_code)

        write_outputs(config)
        return 0
    finally:
        client.session.cookies.clear()


def main() -> int:
    args = parse_args()
    configure_logging()
    return run(resolve_config(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except UploadError as error:
        LOGGER.error("%s", error)
        sys.exit(1)
