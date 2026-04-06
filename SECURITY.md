# Security

## Credentials

- store `ANKI_USER` and `ANKI_PASSWORD` in GitHub Actions secrets
- prefer environment secrets with required reviewers over plain repository secrets when possible
- do not hardcode credentials in workflow files
- do not paste live cookies or session tokens into issues, logs, or pull requests

## Logging

This project keeps runtime logging minimal and does not log request bodies, passwords, or cookies during normal operation.

Error messages may include a short preview of the upstream response body when AnkiWeb rejects a request. Treat failed workflow logs as operational data and avoid pasting them publicly without review.

## Local usage

For local runs, prefer environment variables or the interactive password prompt. The CLI intentionally does not accept the password as a command-line flag, which reduces exposure in shell history and process listings.

## Limits

No credentialed automation can be made absolutely risk-free.

Residual risk still exists if:

- the GitHub runner or local machine is compromised
- another workflow step or third-party action is malicious
- credentials are exposed outside this action before it runs
- upstream services or infrastructure are compromised

If you need stronger isolation, use a dedicated GitHub workflow with minimal additional steps and rotate the Anki password if you ever suspect exposure.

## Recommended GitHub setup

- store Anki credentials in a protected GitHub Actions environment
- require reviewer approval before workflows can access that environment
- protect changes to `.github/workflows/` and `action.yml` with `CODEOWNERS`
- keep the publishing job small and avoid unnecessary third-party actions in the same job
