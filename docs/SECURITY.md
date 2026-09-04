# Security Architecture & Requirements

## 1. Secrets Management
- **Environment Isolation:** Secrets and API keys must reside solely in `.env` and runtime environment variables. The `.env` file is permanently excluded via `.gitignore`.
- **Pre-Commit Checks:** Secret scanning tools should verify that private keys, credentials, and tokens are never committed to version control.

---

## 2. API Key Restrictions & Cloud Security
- **Google Maps API Key:** Must be restricted by **HTTP Referrer** in the Google Cloud Console to authorized domains (e.g., `http://localhost:5173/*` for local development, production URLs for deployments).
- **API Restrictions:** Scope keys strictly to required APIs (Maps JavaScript API).
- **Supabase Keys:** `VITE_SUPABASE_ANON_KEY` is designed for public client usage governed by PostgreSQL Row Level Security (RLS). Secret service keys (`service_role`) must never be embedded in frontend builds.

---

## 3. Database Row Level Security (RLS)
All Supabase tables (`gps_records`, `observations`, `incidents`, `road_segments`) enforce RLS policies:
- Inserts are permitted from authenticated or anonymous fleet ingest nodes with validation constraints.
- Public read access is granted for active client dashboard visualization.

---

## 4. Evidence Storage & Access Control
- **Static File Isolation:** The `/evidence` and `/static/uploads` directories are sanitized to prevent directory traversal attacks.
- **Sensitive Data Redaction:** Face and private vehicle license plate blurring should be applied at the edge or ingestion stage where required by privacy regulations before public dashboard display.

---

## 5. Network Security & Input Validation
- **CORS Policies:** Backend FastAPI endpoints must enforce strict CORS policies in production environments, permitting requests only from authorized dashboard domains.
- **Payload Validation:** All external data from edge devices and WebSocket streams must undergo schema validation (Pydantic models / TypeScript interfaces) prior to processing or persistence.
- **Content Security Policy (CSP):** The frontend application should enforce CSP headers preventing unauthorized script injection.

---

## 6. Dependency & Repository Hygiene
- **Dependency Auditing:** Run `npm audit` periodically to identify and patch vulnerable packages.
- **Git History Integrity:** Never use force-push (`git push --force`) on shared team branches.
