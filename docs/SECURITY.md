# Security Baseline

- `.env` and secrets are never committed.
- Use `.env.example`.
- Google Maps/browser keys must be appropriately restricted.
- Do not log credentials, tokens, or sensitive evidence.
- Validate API input and AI output.
- Keep CORS restrictive outside local development.
- Review third-party dependencies before adding them.
- Never use force-push as a recovery mechanism.
