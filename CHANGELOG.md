# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-04-06

### Added

- Initial public release of the GitHub Action
- Direct AnkiWeb login and update flow for existing add-ons
- Local unit tests and CI workflow

### Changed

- Invalid numeric settings now fail with user-facing `UploadError` messages instead of Python tracebacks
- Runtime dependencies are pinned for reproducible action installs

### Notes

- The action uses AnkiWeb private endpoints and should be treated as unofficial and potentially fragile
