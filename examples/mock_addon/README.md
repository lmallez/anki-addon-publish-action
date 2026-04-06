# Mock Upload Test Add-on

This package exists to exercise the AnkiWeb upload path with a minimal, well-formed `.ankiaddon`.

It includes:

- `__init__.py` so Anki can load the add-on
- `manifest.json` with package metadata
- `config.json` and `config.md` as optional but common add-on files
- `user_files/README.txt` so the preserved user files directory is present

The zip archive is built without a top-level folder, as required by Anki's add-on sharing docs.
