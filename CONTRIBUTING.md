# Contributing

Thanks for helping improve `anki-addon-publish-action`.

## Before you open a PR

- open an issue first for behavior changes or larger refactors
- keep changes focused and easy to review
- avoid introducing support for undocumented AnkiWeb behavior unless it is backed by a real capture or reproducible test

## Local setup

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m anki_addon_publish_action --help
```

## Expectations

- update tests when request encoding or config handling changes
- keep the README aligned with actual supported behavior
- do not commit credentials, cookies, or captured session tokens

## Scope

This project intentionally focuses on updating existing AnkiWeb add-ons from CI. Manual first-time add-on creation remains out of scope.
