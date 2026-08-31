# Verification Rule

After meaningful code changes:

- Run the narrowest relevant tests first.
- Run lint.
- Run type/build checks when available.
- Test error and empty states where applicable.
- Inspect the git diff for accidental changes.
- Only claim completion after verification.

For UI changes, verify the rendered behavior when browser tooling is available.
