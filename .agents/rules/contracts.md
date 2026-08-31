# Contract Rule

Before changing an API, event schema, shared type, database field, or externally consumed payload:

1. Inspect the current contract document.
2. Identify all consumers.
3. Update the contract document first or in the same change.
4. Update affected implementations and tests.
5. Report breaking changes explicitly.

Never silently rename fields or change coordinate/timestamp conventions.
