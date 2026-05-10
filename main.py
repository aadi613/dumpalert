from fastapi import FastAPI, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import json, random, io, os, base64, requests as _req
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
        "description": "A large pile of mixed household and construction waste has been illegally dumped on an open roadside area. The dump contains plastic bags, broken furniture, and debris spread across approximately 3 square metres. Waste appears to have accumulated over several days based on weathering patterns.",
        "health_risk": "High", "estimated_volume": "Medium (1–5 m³)", "estimated_weight_kg": 380,
        "recommended_action": "Dispatch a cleanup crew within 24 hours and install CCTV to deter future dumping."
    },
    {
        "waste_detected": True, "image_quality": "Good",
        "waste_type": "plastic", "severity": 5, "severity_label": "Medium",
        "description": "Scattered plastic bottles, bags and packaging material are visible across the area. Consumer plastic litter has accumulated over time with no immediately visible hazardous materials. The spread covers roughly 10 square metres of public land.",
        "health_risk": "Low", "estimated_volume": "Small (<1 m³)", "estimated_weight_kg": 45,
        "recommended_action": "Schedule routine cleanup within 72 hours and install waste bins nearby to prevent recurrence."
    },
    {
        "waste_detected": True, "image_quality": "Good",
        "waste_type": "construction", "severity": 9, "severity_label": "Critical",
        "description": "Large quantities of construction debris including broken concrete, metal rods, and asbestos-like sheeting have been dumped illegally. The volume and hazardous nature of the waste poses immediate safety risks to nearby residents and wildlife.",
        "health_risk": "High", "estimated_volume": "Large (>5 m³)", "estimated_weight_kg": 2400,
        "recommended_action": "Immediately cordon off the area, conduct a hazardous material assessment, and arrange specialist disposal within 12 hours."
    },
    {
        "waste_detected": True, "image_quality": "Good",
        "waste_type": "organic", "severity": 4, "severity_label": "Medium",
        "description": "A decomposing pile of organic waste including food scraps, garden trimmings, and biodegradable material is visible. The waste is attracting insects and poses a moderate public health risk due to odour and potential disease vectors.",
        "health_risk": "Medium", "estimated_volume": "Small (<1 m³)", "estimated_weight_kg": 120,
        "recommended_action": "Remove within 48 hours and treat area with disinfectant to prevent pest infestation."
    },
    {
        "waste_detected": True, "image_quality": "Good",
        "waste_type": "electronic", "severity": 7, "severity_label": "High",
        "description": "Discarded electronic waste including CRT monitors, circuit boards, and cables has been illegally dumped. E-waste contains toxic materials such as lead, cadmium, and mercury that can leach into the soil and contaminate groundwater.",
        "health_risk": "High", "estimated_volume": "Small (<1 m³)", "estimated_weight_kg": 210,
        "recommended_action": "Engage a certified e-waste recycler for collection and ensure the site is tested for heavy metal contamination."
    },
    {
        "waste_detected": True, "image_quality": "Good",
        "waste_type": "chemical", "severity": 10, "severity_label": "Critical",
        "description": "Unlabelled chemical drums and industrial containers have been illegally abandoned at this location. Visible liquid seepage suggests active leakage of potentially hazardous substances into surrounding soil. This constitutes an environmental emergency.",
        "health_risk": "High", "estimated_volume": "Medium (1–5 m³)", "estimated_weight_kg": 850,
        "recommended_action": "Immediately alert hazmat authorities, isolate the area within a 50m radius, and do not approach without protective equipment."
    },
    {
        "waste_detected": True, "image_quality": "Good",
        "waste_type": "mixed", "severity": 6, "severity_label": "Medium",
        "description": "A moderate accumulation of mixed domestic and commercial waste including cardboard, plastic wrapping, and metal cans has been dumped near a drainage channel. The proximity to water infrastructure raises the risk of blockage and flooding.",
        "health_risk": "Medium", "estimated_volume": "Medium (1–5 m³)", "estimated_weight_kg": 290,
        "recommended_action": "Clear waste within 48 hours, prioritising material near the drainage channel to prevent blockage."
    },
    {
        "waste_detected": True, "image_quality": "Good",
        "waste_type": "construction", "severity": 6, "severity_label": "Medium",
        "description": "Builder's rubble including broken tiles, sand bags, and timber offcuts has been deposited on public land. The dump appears to be from a nearby renovation project. No immediately hazardous materials are visible but the volume obstructs pedestrian access.",
        "health_risk": "Low", "estimated_volume": "Medium (1–5 m³)", "estimated_weight_kg": 620,
        "recommended_action": "Issue a notice to identify responsible party and arrange removal within 5 business days."
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
    try:
        duplicate = find_duplicate(lat, lon)

        if demo_mode.lower() == "true":
            await image.read()
            result = random.choice(DEMO_RESULTS).copy()
        else:
            api_key = os.getenv("OPENROUTER_API_KEY", "")
            raw_bytes = await image.read()
            pil_img = Image.open(io.BytesIO(raw_bytes))
            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG")
            b64 = base64.b64encode(buf.getvalue()).decode()

            prompt = """Analyze this image for illegal waste dumping. Return ONLY a valid JSON object, no markdown:
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
            resp = _req.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "meta-llama/llama-3.2-11b-vision-instruct:free",
                    "messages": [{"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                        {"type": "text", "text": prompt}
                    ]}]
                },
                timeout=30
            )
            resp_json = resp.json()
            if "choices" not in resp_json:
                raise ValueError(f"OpenRouter error: {resp_json}")
            raw = resp_json["choices"][0]["message"]["content"].strip().replace("```json","").replace("```","").strip()
            result = json.loads(raw)

        if result.get("waste_detected"):
            result["civic_credits"] = civic_credits(
                result.get("severity", 5), result.get("estimated_weight_kg", 100)
            )

        if duplicate:
            result["duplicate"] = {"ticket_id": duplicate["ticket_id"], "waste_type": duplicate["waste_type"]}

        return result

    except Exception as e:
        return {
            "waste_detected": False,
            "error": str(e),
            "image_quality": "Error",
            "description": f"Analysis failed: {str(e)}"
        }

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
