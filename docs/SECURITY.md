# Security Architecture & Requirements

## 1. Secrets Management & Isolation
- **Environment Isolation:** Secrets and API keys must reside solely in `.env` files and environment variables. The `.env` file is permanently excluded via `.gitignore` in both the project root and `backend/`.
- **Pre-Commit Checks:** Secret scanning tools verify that private keys, credentials, and tokens are never committed.
- **Service Role Key Protection:** The `SUPABASE_SERVICE_ROLE_KEY` possesses elevated database and storage administrative privileges. It must only exist in `backend/.env` and never be prefixed with `VITE_` or exposed in client bundles.
- **Documentation Hygiene:** No real credentials, tokens, or private passwords may ever be committed, printed, or copied into project documentation.

---

## 2. API Key & Endpoint Restrictions
- **Google Maps API Key:** Must be restricted by **HTTP Referrer** in the Google Cloud Console to authorized domains (e.g., `http://localhost:5173/*` for local development, production URLs for deployments).
- **API Restrictions:** Scope keys strictly to required APIs (Maps JavaScript API).
- **CORS Configuration:** The FastAPI backend enforces strict origin checking via `CORS_ORIGINS`. Only trusted dashboard domains are permitted to invoke REST and WebSocket APIs.

---

## 3. Subsystem Boundary & Least Privilege Access
- **AI to Backend API Boundary:** Edge AI nodes, dashcams, and hardware receivers communicate with the backend solely through authenticated HTTP REST APIs (`POST /api/v1/telemetry`, `POST /api/v1/observations`, `POST /api/v1/incidents`).
- **No Direct Database Access for Edge Nodes:** Edge sensing units do not receive database credentials, connection strings, or direct SQL access. They operate strictly as API clients via `BackendIngestAdapter`.
- **Sanitized Error Gateway (HTTP 503):** All database connection errors, pooler dropouts, and query operational failures are intercepted by custom exception handlers (`app/core/errors.py`) and returned to clients as sanitized HTTP 503 `DATABASE_CONNECTION_ERROR` responses. Internal connection strings, hostnames, and credentials are never exposed in error payloads.

---

## 4. Evidence Storage & Access Control
- **Signed URLs:** Direct access to raw evidence images and video clips stored in Supabase Storage (`road-evidence`) must use time-limited pre-signed HTTPS URLs generated via the backend evidence service (`get_signed_evidence_url()`).
- **Bucket Visibility:** The `road-evidence` storage bucket is private; public anonymous bucket listing is disabled.
- **Sensitive Data Redaction:** Face and private vehicle license plate blurring should be applied at the edge or ingestion stage before public dashboard display where required by privacy regulations.

---

## 5. Network Security & Input Validation
- **SQL Injection Prevention:** All database access is mediated through SQLAlchemy ORM or strictly parameterized queries. User input is never concatenated directly into raw SQL.
- **Payload Validation:** All external data from edge devices and WebSocket streams must undergo Pydantic schema validation (`ObservationCreate`, `TelemetryCreate`, `IncidentCreate`) prior to processing or persistence.
- **Content Security Policy (CSP):** The frontend application enforces CSP headers preventing unauthorized script injection.

---

## 6. Dependency & Repository Hygiene
- **Dependency Auditing:** Run `npm audit` and `pip-audit` periodically to identify and patch vulnerable packages.
- **Git History Integrity:** Never use force-push (`git push --force`) on shared team branches.
