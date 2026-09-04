# Development Environment Setup

## 1. Prerequisites
- **Node.js:** v18.0.0+ (v20+ LTS recommended)
- **Python:** 3.10+ (3.11 recommended)
- **Package Manager:** `npm` (bundled with Node.js) and `pip`
- **Google Maps Platform Account:** With Maps JavaScript API enabled and a Vector Map ID configured.
- **Supabase Account / Project:** For cloud PostgreSQL + PostGIS database and Realtime streaming.

---

## 2. Quickstart

### 2.1 Frontend Dashboard (`src/`)
1. **Install Dependencies:**
   ```bash
   npm install
   ```

2. **Configure Environment Variables:**
   Copy `.env.example` to `.env` (or configure existing `.env`):
   ```bash
   cp .env.example .env
   ```

3. **Start Development Server:**
   ```bash
   npm run dev
   ```
   The dashboard will be accessible at `http://localhost:5173`.

### 2.2 Backend & Spatial Server (`backend/`)
1. **Install Python Dependencies:**
   ```bash
   pip install -r backend/requirements.txt
   ```

2. **Start FastAPI Backend:**
   ```bash
   python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   Interactive API documentation will be available at `http://localhost:8000/docs`.

### 2.3 Edge AI Live Scanner (`ai/`)
1. **Run Live Video & Detection Scanner:**
   ```bash
   python run_live_scanner.py
   ```
   Opens a real-time HUD window running OpenCV + YOLO perception over sample dashcam video and synchronized GPS tracks.

### 2.4 Supabase Database Verification (`scripts/`)
1. **Test Cloud Database & Tables:**
   ```bash
   node scripts/verify_supabase.cjs
   ```

---

## 3. Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `VITE_GOOGLE_MAPS_API_KEY` | Yes | — | Google Maps JavaScript API key with vector map access. |
| `VITE_GOOGLE_MAPS_MAP_ID` | Yes | — | Google Cloud Vector Map ID for 3D vector rendering & Advanced Markers. |
| `VITE_API_BASE_URL` | Yes | `http://localhost:8000` | Base URL for FastAPI backend REST endpoints. |
| `VITE_USE_MOCK` | Yes | `true` | When `true`, uses typed local fixtures in `src/data/` without requiring backend. |
| `VITE_SUPABASE_URL` | Yes | — | Supabase project HTTPS URL. |
| `VITE_SUPABASE_ANON_KEY` | Yes | — | Supabase anonymous API key for public RLS access. |

---

## 4. Key Security Rules
- **Never commit `.env`:** Keep `.env` strictly in `.gitignore`.
- **API Key Restrictions:** Configure HTTP referrer restrictions in Google Cloud Console (`localhost:5173/*` and production domains).
- **No Console Key Output:** Do not print or log API keys or bearer tokens in source code or debug logs.
