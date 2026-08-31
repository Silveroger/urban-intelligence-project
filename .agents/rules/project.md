# Project Rule

Always read `AGENT_CONTEXT.md` and relevant `docs/` files before implementation.

Treat the repository as the shared source of truth.

Requirements:
- Preserve existing architecture unless a documented decision changes it.
- Implement only the requested scope.
- Prefer small composable changes.
- Reuse existing types/services/components.
- Keep feature flags/config centralized.
- Update documentation for interface or architecture changes.
- Never commit secrets or `.env`.
