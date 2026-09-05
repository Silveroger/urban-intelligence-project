# Security Architecture & Requirements

## 1. Secrets Management
- **Environment Isolation:** Secrets and API keys must reside solely in `.env` and environment variables. The `.env` file is permanently excluded via `.gitignore` in both the project root and `backend/`.
- **Pre-Commit Checks:** Secret scanning tools verify that private keys, credentials, and tokens are never committed.
- **Service Role Key Protection:** The `SUPABASE_SERVICE_ROLE_KEY` possesses elevated database and storage administrative privileges. It must only exist in `backend/.env` and never be prefixed with `VITE_` or exposed in client bundles.

---

## 2. API Key & Endpoint Restrictions
- **Google Maps API Key:** Must be restricted by **HTTP Referrer** in the Google Cloud Console to authorized domains (e.g., `http://localhost:5173/*` for local development, production URLs for deployments).
- **API Restrictions:** Scope keys strictly to required APIs (Maps JavaScript API).
- **CORS Configuration:** The FastAPI backend enforces strict origin checking via `CORS_ORIGINS`. Only trusted dashboard domains are permitted to invoke REST and WebSocket APIs.

---

## 3. Evidence Storage & Access Control
- **Signed URLs:** Direct access to raw evidence images and video clips stored in Supabase Storage (`road-evidence`) must use time-limited pre-signed HTTPS URLs generated via the backend evidence service.
- **Bucket Visibility:** The `road-evidence` storage bucket is private; public anonymous bucket listing is disabled.
- **Sensitive Data Redaction:** Face and private vehicle license plate blurring must be applied at the edge or ingestion stage where required by privacy regulations before public dashboard display.

---

## 4. Network Security & Input Validation
- **SQL Injection Prevention:** All database access is mediated through SQLAlchemy ORM or strictly parameterized `text()` queries. User input is never concatenated directly into raw SQL.
- **Payload Validation:** All external data from edge devices and WebSocket streams must undergo Pydantic schema validation (`ObservationCreate`, `TelemetryCreate`, `IncidentCreate`) prior to processing or persistence.
- **Content Security Policy (CSP):** The frontend application should enforce CSP headers preventing unauthorized script injection.

---

## 5. Dependency & Repository Hygiene
- **Dependency Auditing:** Run `npm audit` and `pip-audit` periodically to identify and patch vulnerable packages.
- **Git History Integrity:** Never use force-push (`git push --force`) on shared team branches.
