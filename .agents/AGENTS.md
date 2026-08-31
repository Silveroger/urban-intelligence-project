# SIH 26124 Agent Operating Context

Read `AGENT_CONTEXT.md` at the repository root before implementation.

## Authoritative Documentation Hierarchy
1. `AGENT_CONTEXT.md` = Executive briefing, critical constraints, agent rules.
2. `docs/PRD.md` = Product requirements, user personas, feature scope, acceptance criteria.
3. `docs/TECH_STACK.md` = Technologies, libraries, versions, infrastructure.
4. `docs/ARCHITECTURE.md` = System architecture, data flow, subsystem boundaries, integration.
5. `docs/API_CONTRACT.md`, `docs/AI_CONTRACT.md`, `docs/DATABASE_SCHEMA.md` = Interface and schema contracts.
6. `docs/MODULE_OWNERSHIP.md` = Subsystem ownership and paths.
7. `docs/DECISIONS.md` = Accepted Architecture Decision Records (ADRs).
8. `docs/AGENT_STATE.md` = Temporary implementation baseline and active milestone.
9. `docs/BACKLOG.md` = Priority task backlog.
10. `docs/ENVIRONMENT.md` = Development setup and environment variables.
11. `docs/SECURITY.md` = Security architecture and secrets management.
12. `docs/TESTING.md` = Testing procedures and verification commands.
13. `docs/FRONTEND_ARCHITECTURE.md` = Frontend state, map lifecycle, directory layout.
14. Source code + tests = Implementation truth.

If documentation and code disagree, stop and identify the conflict. Do not silently invent behavior.

## Engineering Rules
- Inspect before modifying.
- Make the smallest correct change.
- Preserve working architecture.
- Do not duplicate utilities, services, types, or business logic.
- Do not change API/database contracts silently.
- Never commit secrets or `.env`.
- Do not add dependencies unless needed and justified.
- Validate all external input.
- Keep frontend, backend, AI, and database responsibilities separated.
- Run relevant tests, lint, and build/type checks after changes (`npm run lint && npm run build`).
- Do not claim success without verification.
- Update docs when an architectural/interface decision changes.

## Token Efficiency
- Read only the relevant docs/files for the task.
- Prefer existing abstractions over new ones.
- Do not regenerate working code.
- Do not output large explanations unless requested.
- Report changed files, verification, and blockers concisely.

## Team Safety
- Do not force-push.
- Do not reset/delete unrelated work.
- Avoid editing files owned by another subsystem unless required by an explicit interface change.
