# DumpAlert — AI-Powered Illegal Dumping Reporter

A prototype civic-tech web application that uses Vision-Language AI to classify illegal
waste dumps from photos and automatically files complaints to municipal authorities via
Open311 / Swachhata-MoHUA in under 10 seconds.

---

## The Problem

Most people see illegal dumping but never report it. The reason is friction:
- Complex forms, unclear categories, long submission flows
- Complaints rejected for "unclear image" even when photo is fine
- No feedback on whether the issue was resolved
- Result: a data gap that leaves municipalities unable to respond efficiently

**DumpAlert removes that friction entirely.**

---

## System Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER FLOW (10 seconds)                        │
└─────────────────────────────────────────────────────────────────────┘

  📷 Photo            🤖 AI Analysis          📋 Complaint          ✅ Filed
  ─────────           ──────────────          ────────────          ───────
  User uploads   →    Gemini Vision      →    Auto-drafted     →    Open311 /
  or captures         classifies waste        complaint letter       Swachhata
  a photo             in 4 phases             with all details       API call
                                                                     + Ticket ID


┌─────────────────────────────────────────────────────────────────────┐
│                      TECHNICAL PIPELINE                              │
└─────────────────────────────────────────────────────────────────────┘

  Browser (HTML/CSS/JS)
       │
       │  HTTP POST /api/analyze  (multipart image + lat + lon)
       ▼
  FastAPI Backend (Python)
       │
       ├── Duplicate Check ──── GPS distance < 100m? → warn user
       │
       ├── Demo Mode? ──────── Yes → return pre-set realistic result
       │                       No  ↓
       │
       └── Gemini 2.0 Flash (Vision-Language Model)
               │
               │  4-phase prompt:
               │  Phase 1 → Image Quality Check  (Good / Blurry / Too Dark)
               │  Phase 2 → Waste Identification (plastic / chemical / construction...)
               │  Phase 3 → Severity Assessment  (score 1–10 + label)
               │  Phase 4 → Weight Estimation    (using reference objects in image)
               │
               └── Returns JSON → FastAPI → Browser renders result card
                                                    │
                                                    ▼
                                          Complaint Tab:
                                          Auto-drafted letter
                                          Platform: Open311 or Swachhata-MoHUA
                                                    │
                                                    ▼
                                          POST /api/file-report
                                          → Ticket ID generated (DA-YYYYMMDD-XXXX)
                                          → Category mapped (GD / HW / CD / EW...)
                                          → Stored in session DB
                                                    │
                                                    ▼
                                          Dashboard Tab:
                                          Leaflet map + metrics + report history
```

---

## Features (backed by research)

| Feature | Research Basis | Implementation |
|---|---|---|
| Vision-Language classification | Gemini 1.5 Flash zero-shot (Novelis, 2024) | 4-phase Gemini prompt |
| Weight estimation | Human-mimetic VLM approach (PMC, 2025) | Added to AI prompt |
| Image quality check | Prevents "unclear image" rejection (MoHUA docs) | Phase 1 of prompt |
| Severity scoring 1–10 | Harm-block adaptation (Vertex AI docs) | Returned in JSON |
| Open311 GeoReport v2 | open311.org standard | API structure in backend |
| Swachhata-MoHUA | India MoHUA API (swachh.city/docs) | Category ID mapping |
| Duplicate detection | Cosine similarity clustering (ResearchGate, 2024) | GPS distance < 100m |
| Civic Credits formula | `R = severity × weight × K_incentive` (ResearchGate) | Calculated per report |

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | HTML + CSS + Vanilla JS | No framework needed, full design control |
| Backend | Python + FastAPI | Fast, async, easy file upload handling |
| AI Model | Google Gemini 2.0 Flash | Free tier, multimodal, 194 tokens/sec |
| Maps | Leaflet.js | Free, no API key, OpenStreetMap tiles |
| Server | Uvicorn (ASGI) | Works with FastAPI out of the box |
| Styling | Pure CSS (Inter font) | No Bootstrap dependency |

---

## File Structure

```
environment_el/
│
├── main.py                  ← FastAPI backend (API routes + Gemini calls)
├── .env                     ← API keys (never commit this to GitHub)
├── README.md                ← This file
│
└── static/                  ← Frontend (served by FastAPI)
    ├── index.html           ← Single-page app structure (3 tabs)
    ├── style.css            ← Dark theme UI (CSS variables, no framework)
    └── app.js               ← All frontend logic (vanilla JS)
```

### What each file does

**main.py**
- Defines all API routes under `/api/*`
- Calls Gemini API with a 4-phase prompt
- Stores reports in memory (no database needed for prototype)
- Serves the static frontend files
- Calculates Civic Credits and checks for duplicates

**static/index.html**
- Three-tab single-page layout: Report, Complaint, Dashboard
- Camera modal for mobile photo capture
- All UI elements referenced by JS via IDs

**static/style.css**
- CSS custom properties (variables) for the dark theme
- No external CSS framework — fully custom
- Responsive layout with CSS Grid

**static/app.js**
- Tab switching, file upload, drag-and-drop
- GPS location via browser API
- Sends image to backend via `fetch()` + `FormData`
- Renders AI result card dynamically
- Initializes Leaflet maps for mini-map and dashboard

---

## API Endpoints

| Method | Endpoint | What it does |
|---|---|---|
| `GET` | `/` | Serves the frontend (index.html) |
| `POST` | `/api/analyze` | Sends image to Gemini, returns classification JSON |
| `POST` | `/api/file-report` | Creates a ticket, stores report, returns ticket ID |
| `GET` | `/api/reports` | Returns all filed reports (for dashboard) |

### Example `/api/analyze` response
```json
{
  "waste_detected": true,
  "image_quality": "Good",
  "waste_type": "construction",
  "severity": 9,
  "severity_label": "Critical",
  "description": "Large quantities of construction debris...",
  "health_risk": "High",
  "estimated_volume": "Large (>5 m³)",
  "estimated_weight_kg": 2400,
  "recommended_action": "Cordon off area and arrange specialist disposal.",
  "civic_credits": 300
}
```

---

## How to Run (Local)

### 1. Install dependencies
```bash
pip install fastapi uvicorn python-multipart google-genai pillow python-dotenv streamlit-folium folium
```

### 2. Add your Gemini API key
Edit the `.env` file:
```
GEMINI_API_KEY=your_key_here
```
Get a free key at: https://aistudio.google.com/apikey

### 3. Start the server
```bash
python -m uvicorn main:app --reload --port 8000
```

### 4. Open in browser
```
http://localhost:8000
```

---

## Why Localhost? (and how to deploy to a real URL)

**Why we use localhost for the prototype:**
Localhost runs entirely on your machine — no internet needed, no cost, no configuration.
For a demo or presentation this is ideal: fast, reliable, no external dependencies.

**To deploy to a real public URL (free):**

### Option A — Railway (easiest, recommended)
1. Create free account at railway.app
2. Push this project to GitHub
3. In Railway: New Project → Deploy from GitHub → select your repo
4. Add environment variable: `GEMINI_API_KEY = your_key`
5. Railway auto-detects Python and deploys — you get a URL like `dumpalert.railway.app`

### Option B — Render
1. Create free account at render.com
2. New Web Service → connect GitHub repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add `GEMINI_API_KEY` as environment variable

### requirements.txt (needed for deployment)
```
fastapi
uvicorn
python-multipart
google-genai
pillow
python-dotenv
```

---

## Comparison with Existing Systems

| Feature | DumpAlert | Swachhata-MoHUA | SeeClickFix | BBMP Sahaaya |
|---|---|---|---|---|
| Reporting time | ~10 sec | ~3 min | ~2 min | ~4 min |
| AI classification | ✅ | ❌ | ❌ | ❌ |
| Weight estimation | ✅ | ❌ | ❌ | ❌ |
| Auto-complaint draft | ✅ | ❌ | ❌ | ❌ |
| Image quality check | ✅ | ❌ | ❌ | ❌ |
| Duplicate detection | ✅ | ❌ | ✅ | ❌ |
| Civic gamification | ✅ | ❌ | ❌ | ❌ |
| Open311 standard | ✅ | ⚠️ | ✅ | ❌ |

---

## Known Prototype Limitations

- Ticket tracking is **simulated** — a production version would call the real Open311 or Swachhata API
- Reports are stored **in memory** — restarting the server clears them (production needs a database)
- No **user authentication** — production needs login for accountability
- Gemini free tier has **rate limits** — Demo Mode works without any API key

---

## Future Roadmap (from research paper)

- [ ] Real Open311 API integration (San Francisco, Chicago live endpoints)
- [ ] Real Swachhata-MoHUA vendor registration + POST complaints
- [ ] Before/After change detection to verify actual cleanup
- [ ] PostgreSQL database for persistent report storage
- [ ] User login + report history per citizen
- [ ] YOLOv12 for real-time video stream detection
- [ ] Multi-report clustering (cosine similarity)
- [ ] Push notifications when ticket status changes

---

## Research References

This prototype is backed by peer-reviewed research:
- Gemini 1.5 Flash benchmarks — artificialanalysis.ai
- YOLOv12 waste classification — mdpi.com/2673-6470/5/2/19
- Human-mimetic weight estimation — pmc.ncbi.nlm.nih.gov/articles/PMC8455030
- Open311 GeoReport v2 standard — open311.org/learn
- Swachhata-MoHUA API — swachh.city/assets/files/Integrate_With_Swachhata_App_V2.2.pdf
- Civic incentive coefficient — ResearchGate publication 390698186
- Duplicate detection via clustering — ResearchGate publication 271430208

Full bibliography: see attached research paper (42 citations).
