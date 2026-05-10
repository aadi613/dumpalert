from fastapi import FastAPI, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from PIL import Image
import json, random, io, os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

reports_db = []

DEMO_RESULTS = [
    {
        "waste_detected": True, "image_quality": "Good",
        "waste_type": "mixed", "severity": 8, "severity_label": "High",
        "description": "A large pile of mixed household and construction waste has been illegally dumped on an open roadside area. The dump contains plastic bags, broken furniture, and debris spread across approximately 3 square metres. Waste appears to have accumulated over several days.",
        "health_risk": "High", "estimated_volume": "Medium (1–5 m³)", "estimated_weight_kg": 380,
        "recommended_action": "Dispatch a cleanup crew within 24 hours and install CCTV to deter future dumping."
    },
    {
        "waste_detected": True, "image_quality": "Good",
        "waste_type": "plastic", "severity": 5, "severity_label": "Medium",
        "description": "Scattered plastic bottles, bags and packaging material are visible across the area. Consumer plastic litter accumulated over time with no immediately visible hazardous materials.",
        "health_risk": "Low", "estimated_volume": "Small (<1 m³)", "estimated_weight_kg": 45,
        "recommended_action": "Schedule routine cleanup and install waste bins nearby to prevent recurrence."
    },
    {
        "waste_detected": True, "image_quality": "Good",
        "waste_type": "construction", "severity": 9, "severity_label": "Critical",
        "description": "Large quantities of construction debris including broken concrete, metal rods, and asbestos-like material dumped illegally. Volume and nature of waste poses significant safety and environmental hazards requiring immediate response.",
        "health_risk": "High", "estimated_volume": "Large (>5 m³)", "estimated_weight_kg": 2400,
        "recommended_action": "Immediately cordon off area, conduct hazardous material assessment, and arrange specialist disposal."
    },
]

CATEGORY_MAP = {
    "plastic":      {"id": 3, "name": "Garbage Dump",            "swachhata_code": "GD"},
    "chemical":     {"id": 7, "name": "Chemical / Hazardous",    "swachhata_code": "HW"},
    "construction": {"id": 5, "name": "Construction Debris",     "swachhata_code": "CD"},
    "organic":      {"id": 2, "name": "Organic Waste",           "swachhata_code": "OW"},
    "electronic":   {"id": 6, "name": "E-Waste",                 "swachhata_code": "EW"},
    "mixed":        {"id": 3, "name": "Garbage Dump",            "swachhata_code": "GD"},
}

def civic_credits(severity: int, weight_kg: int) -> int:
    k = 1.2 if severity >= 8 else (1.0 if severity >= 5 else 0.8)
    return int((severity * 10 + min(weight_kg, 1000) / 10) * k)

def find_duplicate(lat: float, lon: float):
    for r in reports_db:
        dlat = (r["lat"] - lat) * 111000
        dlon = (r["lon"] - lon) * 111000 * 0.85
        if (dlat**2 + dlon**2) ** 0.5 < 100:
            return r
    return None

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/api/analyze")
async def analyze(
    image: UploadFile = File(...),
    demo_mode: str = Form("true"),
    lat: float = Form(19.076),
    lon: float = Form(72.877),
):
    duplicate = find_duplicate(lat, lon)

    if demo_mode.lower() == "true":
        raw_bytes = await image.read()
        result = DEMO_RESULTS[len(raw_bytes) % len(DEMO_RESULTS)].copy()
    else:
        api_key = os.getenv("GEMINI_API_KEY", "")
        raw_bytes = await image.read()
        pil_img = Image.open(io.BytesIO(raw_bytes))
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG")

        client = genai.Client(api_key=api_key)
        prompt = """Multi-phase illegal waste analysis:
PHASE 1 – Image Quality: Is the photo clear enough to analyze?
PHASE 2 – Identification: What type of waste is present?
PHASE 3 – Severity Assessment: How severe is the illegal dumping (1-10)?
PHASE 4 – Weight Estimation: Using reference objects visible (cars, bins, curbs), estimate weight in kg.

Return ONLY a valid JSON object, no markdown:
{
  "waste_detected": true or false,
  "image_quality": "Good / Blurry / Too Dark / Unclear",
  "waste_type": "plastic / chemical / construction / organic / electronic / mixed / other",
  "severity": integer 1-10,
  "severity_label": "Low / Medium / High / Critical",
  "description": "2-3 sentences describing the scene",
  "health_risk": "None / Low / Medium / High",
  "estimated_volume": "Small (<1 m³) / Medium (1-5 m³) / Large (>5 m³)",
  "estimated_weight_kg": integer,
  "recommended_action": "one sentence"
}"""
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=[types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg"), prompt]
        )
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)

    if result.get("waste_detected"):
        result["civic_credits"] = civic_credits(
            result.get("severity", 5), result.get("estimated_weight_kg", 100)
        )

    if duplicate:
        result["duplicate"] = {"ticket_id": duplicate["ticket_id"], "waste_type": duplicate["waste_type"]}

    return result

@app.post("/api/file-report")
async def file_report(data: dict):
    ticket_id = f"DA-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000,9999)}"
    cat = CATEGORY_MAP.get(data.get("waste_type", "mixed"), CATEGORY_MAP["mixed"])
    report = {
        "ticket_id": ticket_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "waste_type":         data.get("waste_type", "Unknown"),
        "severity":           data.get("severity", 5),
        "severity_label":     data.get("severity_label", "Medium"),
        "address":            data.get("address", ""),
        "lat":                data.get("lat", 0),
        "lon":                data.get("lon", 0),
        "health_risk":        data.get("health_risk", "Unknown"),
        "estimated_weight_kg":data.get("estimated_weight_kg", 0),
        "civic_credits":      data.get("civic_credits", 0),
        "status": "Open",
    }
    reports_db.append(report)
    return {"ticket_id": ticket_id, "status": "Open", "platform": data.get("platform", "Open311"), "category": cat}

@app.get("/api/reports")
async def get_reports():
    return reports_db

app.mount("/", StaticFiles(directory="static", html=True), name="static")
