# Development Environment Setup

## 1. Prerequisites
- **Node.js:** v18.0.0+ (v20+ LTS recommended)
- **Package Manager:** `npm` (bundled with Node.js)
- **Google Maps Platform Account:** With Maps JavaScript API enabled and a Vector Map ID configured.

---

## 2. Quickstart (`urban-dashboard`)

1. **Install Dependencies:**
   ```bash
   cd urban-dashboard
   npm install
   ```

2. **Configure Environment Variables:**
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

3. **Start Development Server:**
   ```bash
   npm run dev
   ```
   The application will be accessible at `http://localhost:5173`.

---

## 3. Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `VITE_GOOGLE_MAPS_API_KEY` | Yes | — | Google Maps JavaScript API key with vector map access. |
| `VITE_GOOGLE_MAPS_MAP_ID` | Yes | — | Google Cloud Vector Map ID for 3D vector rendering & Advanced Markers. |
| `VITE_API_BASE_URL` | Yes | `http://localhost:8000` | Base URL for FastAPI backend REST endpoints. |
| `VITE_USE_MOCK` | Yes | `true` | When `true`, uses typed local fixtures in `src/data/` without requiring backend. |

---

## 4. Key Security Rules
- **Never commit `.env`:** Keep `.env` strictly in `.gitignore`.
- **API Key Restrictions:** Configure HTTP referrer restrictions in Google Cloud Console (`localhost:5173/*` and production domains).
- **No Console Key Output:** Do not print or log API keys or bearer tokens in source code or debug logs.
