# SIH 26124 Agent Operating Context

Read `AGENT_CONTEXT.md` at repository root before implementation.

## Source of truth
1. `AGENT_CONTEXT.md` = compact architecture/product context for agents.
2. `docs/PROJECT.md` = current project status and scope.
3. `docs/ARCHITECTURE.md` = system boundaries and ownership.
4. `docs/*_CONTRACT.md` = interface contracts.
5. `docs/DECISIONS.md` = accepted architecture decisions.
6. Source code + tests = implementation truth.

If documentation and code disagree, stop and identify the conflict. Do not silently invent behavior.

## Engineering rules
- Inspect before modifying.
- Make the smallest correct change.
- Preserve working architecture.
- Do not duplicate utilities, services, types, or business logic.
- Do not change API/database contracts silently.
- Never commit secrets.
- Do not add dependencies unless needed and justified.
- Validate all external input.
- Keep frontend, backend, AI, and database responsibilities separated.
- Run relevant tests, lint, and build/type checks after changes.
- Do not claim success without verification.
- Update docs when an architectural/interface decision changes.

## Token efficiency
- Read only the relevant docs/files for the task.
- Prefer existing abstractions over new ones.
- Do not regenerate working code.
- Do not output large explanations unless requested.
- Report changed files, verification, and blockers concisely.

## Team safety
- Do not force-push.
- Do not reset/delete unrelated work.
- Avoid editing files owned by another subsystem unless required by an explicit interface change.
