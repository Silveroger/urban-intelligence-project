---
name: ai-integration
description: Integrates computer-vision outputs into stable event contracts with validation, confidence handling, evidence references, and failure handling.
---
# AI Integration
Read `docs/AI_CONTRACT.md` and `AGENT_CONTEXT.md`.
Treat model output as untrusted input.
Validate output before persistence/use.
Preserve confidence, severity, timestamps, IDs, location, and evidence references.
Keep model-specific logic isolated from domain/business logic.
