# Integration Checklist

Before connecting a module:

- confirm producer/consumer contract
- confirm field names and types
- confirm IDs
- confirm timestamp format/timezone
- confirm coordinate convention
- confirm nullability
- confirm evidence URL/reference format
- confirm error format
- add an integration fixture
- run build/lint/tests

The frontend should be able to switch from mock data to backend data without rewriting presentation components.
