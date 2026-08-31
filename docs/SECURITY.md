# Security Architecture & Requirements

## 1. Secrets Management
- **Environment Isolation:** Secrets and API keys must reside solely in `.env` and environment variables. The `.env` file is permanently excluded via `.gitignore`.
- **Pre-Commit Checks:** Secret scanning tools should verify that private keys, credentials, and tokens are never committed.

---

## 2. API Key Restrictions
- **Google Maps API Key:** Must be restricted by **HTTP Referrer** in the Google Cloud Console to authorized domains (e.g., `http://localhost:5173/*` for local development, production URLs for deployments).
- **API Restrictions:** Scope keys strictly to required APIs (Maps JavaScript API).

---

## 3. Evidence Storage & Access Control
- **Signed URLs:** Direct access to raw evidence images and video clips stored in object storage should use time-limited pre-signed HTTPS URLs.
- **Sensitive Data Redaction:** Face and private vehicle license plate blurring must be applied at the edge or ingestion stage where required by privacy regulations before public dashboard display.

---

## 4. Network Security & Input Validation
- **CORS Policies:** Backend FastAPI endpoints must enforce strict CORS policies in production environments, permitting requests only from authorized dashboard domains.
- **Payload Validation:** All external data from edge devices and WebSocket streams must undergo schema validation (Pydantic / TypeScript type assertions) prior to processing or persistence.
- **Content Security Policy (CSP):** The frontend application should enforce CSP headers preventing unauthorized script injection.

---

## 5. Dependency & Repository Hygiene
- **Dependency Auditing:** Run `npm audit` periodically to identify and patch vulnerable packages.
- **Git History Integrity:** Never use force-push (`git push --force`) on shared team branches.
