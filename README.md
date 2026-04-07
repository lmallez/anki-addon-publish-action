# 📦 anki-addon-publish-action

[![CI](https://github.com/lmallez/anki-addon-publish-action/actions/workflows/ci.yml/badge.svg)](https://github.com/lmallez/anki-addon-publish-action/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

GitHub Action for updating existing AnkiWeb add-ons with `.ankiaddon` packages.

It uses AnkiWeb's internal binary endpoints, so treat the direct upload path as useful but fragile.

Always pass `anki-user` and `anki-password` from GitHub Actions secrets like `${{ secrets.ANKI_USER }}` and `${{ secrets.ANKI_PASSWORD }}`. Do not hardcode credentials in workflow files.

Security details and limits are documented in [SECURITY.md](./SECURITY.md).

## 🛡️ Important note

This project is unofficial. It is not affiliated with or endorsed by Anki or AnkiWeb.

The direct upload path uses AnkiWeb's internal/private endpoints, not a documented public API. That means:

- the upload flow may break without notice if AnkiWeb changes
- there is no stability or support guarantee from AnkiWeb
- you should not present this action as an official AnkiWeb integration

If you publish or depend on this action, treat the direct upload mode as experimental.

This action is designed for updates only. Create the add-on manually on AnkiWeb first, then use this action in CI with the add-on `id` to publish new versions.

## ✨ What it does

- updates an existing AnkiWeb add-on from GitHub Actions
- accepts metadata inputs: `name`, `tags`, `support-page`, and `description`
- keeps credentials in GitHub secrets
- exposes a small CLI for local debugging when needed

## 🚀 GitHub Action

```yaml
name: Publish add-on

on:
  release:
    types: [published]

jobs:
  upload:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./ # replace with owner/repo@ref after publishing
        with:
          file: dist/my-addon.ankiaddon
          anki-user: ${{ secrets.ANKI_USER }}
          anki-password: ${{ secrets.ANKI_PASSWORD }}
          id: ${{ vars.ANKI_ADDON_ID }}
          name: Example Add-on
          support-page: https://github.com/owner/repo
          tags: example,utility
          description-file: addon/description.md
          timeout-seconds: 30
```

To use this action from another repository, publish this repository to GitHub and reference it with `uses: lmallez/anki-addon-publish-action@ref`.

Example from a different repository:

```yaml
name: Publish add-on

on:
  release:
    types: [published]

jobs:
  upload:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build addon
        run: zip -r dist/my-addon.ankiaddon addon_src

      - name: Upload to AnkiWeb
        uses: lmallez/anki-addon-publish-action@v0.1.0
        with:
          file: dist/my-addon.ankiaddon
          anki-user: ${{ secrets.ANKI_USER }}
          anki-password: ${{ secrets.ANKI_PASSWORD }}
          id: ${{ vars.ANKI_ADDON_ID }}
          name: Example Add-on
          support-page: https://github.com/owner/repo
          tags: example,utility
          description-file: addon/description.md
```

In the consuming repository:

- add `ANKI_USER` and `ANKI_PASSWORD` as GitHub Actions secrets and pass them to `anki-user` and `anki-password`
- create the add-on listing manually on AnkiWeb first, then store its numeric id in a workflow variable like `${{ vars.ANKI_ADDON_ID }}`
- make sure the workflow creates the `.ankiaddon` file before the upload step
- prefer a fixed release tag like `@v0.1.0` or a commit SHA over `@main`
- use a commit SHA if you want the most reproducible setup

### ⚙️ Inputs

- `file`: path to the `.ankiaddon` archive. Required.
- `anki-user`: AnkiWeb username or email. Required. Pass it from a GitHub Actions secret.
- `anki-password`: AnkiWeb password. Required. Pass it from a GitHub Actions secret.
- `id`: existing AnkiWeb add-on id. Required. This action updates an existing listing and does not create new ones.
- `name`: add-on display name. Required.
- `tags`: optional comma-separated tags.
- `support-page`: optional support page URL. A GitHub repository URL is a valid choice.
- `description`: optional inline description text.
- `description-file`: optional path to a UTF-8 text file containing the description.
- `timeout-seconds`: defaults to `30`.

### 📤 Outputs

- `uploaded_file`
- `name`

## 🧱 Release flow

1. Create the add-on listing manually on AnkiWeb.
2. Copy the add-on id from the AnkiWeb edit URL.
3. Save that id as a GitHub Actions variable such as `ANKI_ADDON_ID`.
4. Build your `.ankiaddon` in CI.
5. Run this action to publish updates.

## 💻 CLI usage

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Run tests:

```bash
python3 -m unittest discover -s tests -v
```

Run the uploader directly:

```bash
export ANKI_USER="you@example.com"
export ANKI_PASSWORD="your-password"

PYTHONPATH=src python -m anki_addon_publish_action \
  --file mock-addon.ankiaddon \
  --id 1658294868 \
  --name "Example Add-on" \
  --support-page "https://github.com/owner/repo" \
  --tags "example,utility" \
  --description-file examples/description.md
```

Create a new add-on listing from the CLI:

```bash
export ANKI_USER="you@example.com"
export ANKI_PASSWORD="your-password"

PYTHONPATH=src python -m anki_addon_publish_action \
  --create \
  --file mock-addon.ankiaddon \
  --name "Example Add-on" \
  --support-page "https://github.com/owner/repo" \
  --tags "example,utility" \
  --description-file examples/description.md
```

`--create` is CLI-only and is intentionally not exposed by the GitHub Action.
Use either `description` or `description-file`, not both.

## 🗂️ Repository layout

- `src/anki_addon_publish_action/`: action source code
- `tests/`: unit tests
- `examples/mock_addon/`: minimal sample add-on source for local experiments
- `.github/workflows/ci.yml`: public CI workflow for tests and CLI smoke checks

## 🧾 Metadata model

This package does not inspect the `.ankiaddon` archive to infer metadata. The action or CLI caller is responsible for passing the values it wants to use.

- `name` must be provided explicitly
- `id` must be provided explicitly for updates and for GitHub Action usage
- `--create` can be used from the CLI to create a new add-on listing without an existing id
- `description` can be provided as an inline string or loaded from `description-file`
- `tags` and `support-page` are forwarded when provided

## 🤝 Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## 🔐 Security

See [SECURITY.md](./SECURITY.md).

## 📄 License

This project is available under the [MIT License](./LICENSE).
