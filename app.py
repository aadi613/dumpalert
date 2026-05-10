import streamlit as st
from google import genai
from google.genai import types
import json
import random
import time
from datetime import datetime
from PIL import Image
import folium
from streamlit_folium import st_folium
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="DumpAlert — Illegal Dumping Reporter",
    page_icon="🗑️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Styling ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stTabs [data-baseweb="tab"] { font-size: 16px; font-weight: 600; }
    .severity-card {
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
    }
    .ticket-box {
        background: #1a1a2e;
        border: 2px solid #00d4ff;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
if "reports" not in st.session_state:
    st.session_state.reports = []

# ── Helpers ────────────────────────────────────────────────────────────────────
def severity_color(score: int) -> str:
    if score <= 3:
        return "#28a745"
    if score <= 6:
        return "#ffc107"
    if score <= 8:
        return "#fd7e14"
    return "#dc3545"


DEMO_RESULTS = [
    {
        "waste_detected": True,
        "waste_type": "mixed",
        "severity": 8,
        "severity_label": "High",
        "description": "A large pile of mixed household and construction waste has been illegally dumped on an open roadside area. The dump contains plastic bags, broken furniture, and debris spread across approximately 3 square metres. The waste appears to have accumulated over several days.",
        "health_risk": "High",
        "estimated_volume": "Medium (1–5 m³)",
        "recommended_action": "Dispatch a cleanup crew within 24 hours and install CCTV or signage to deter future dumping."
    },
    {
        "waste_detected": True,
        "waste_type": "plastic",
        "severity": 5,
        "severity_label": "Medium",
        "description": "Scattered plastic bottles, bags and packaging material are visible across the area. The waste appears to be consumer plastic litter that has accumulated over time. No hazardous materials are immediately visible.",
        "health_risk": "Low",
        "estimated_volume": "Small (<1 m³)",
        "recommended_action": "Schedule a routine cleanup and place waste bins nearby to prevent recurrence."
    },
    {
        "waste_detected": True,
        "waste_type": "construction",
        "severity": 9,
        "severity_label": "Critical",
        "description": "Large quantities of construction debris including broken concrete, metal rods, and asbestos-like material have been dumped illegally. The volume and nature of the waste poses significant safety and environmental hazards. Immediate intervention is required.",
        "health_risk": "High",
        "estimated_volume": "Large (>5 m³)",
        "recommended_action": "Immediately cordon off the area, conduct hazardous material assessment, and arrange specialist disposal."
    },
]


def classify_waste(image: Image.Image, api_key: str) -> dict:
    client = genai.Client(api_key=api_key)
    prompt = """Analyze this image for illegal waste dumping.
Return ONLY a JSON object — no markdown, no explanation — with these exact keys:
{
  "waste_detected": true or false,
  "waste_type": "one of: plastic / chemical / construction / organic / electronic / mixed / other",
  "severity": integer 1-10,
  "severity_label": "one of: Low / Medium / High / Critical",
  "description": "2-3 sentences describing what you see",
  "health_risk": "one of: None / Low / Medium / High",
  "estimated_volume": "one of: Small (<1 m³) / Medium (1–5 m³) / Large (>5 m³)",
  "recommended_action": "one sentence on what authorities should do"
}"""
    import io
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    image_bytes = buf.getvalue()
    response = client.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            prompt,
        ]
    )
    raw = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def classify_waste_demo(image: Image.Image) -> dict:
    time.sleep(2)  # simulate analysis delay
    # pick result based on image size for variety
    idx = image.size[0] % len(DEMO_RESULTS)
    return DEMO_RESULTS[idx]


def build_complaint(c: dict, address: str, lat: float, lon: float) -> str:
    return f"""To the Environmental Complaints Department,

I am reporting an illegal waste dumping incident that requires prompt attention.

INCIDENT SUMMARY
────────────────
Date / Time  : {datetime.now().strftime("%B %d, %Y at %H:%M")}
Location     : {address or "See GPS coordinates below"}
GPS          : {lat:.6f}, {lon:.6f}
Waste Type   : {c.get("waste_type", "Unknown").title()}
Severity     : {c.get("severity", "?")} / 10  ({c.get("severity_label", "")})
Volume       : {c.get("estimated_volume", "Unknown")}
Health Risk  : {c.get("health_risk", "Unknown")}

DESCRIPTION
───────────
{c.get("description", "")}

RECOMMENDED ACTION
──────────────────
{c.get("recommended_action", "Please dispatch a cleanup crew to assess and remove the waste.")}

Photographic evidence and GPS coordinates are attached to this report.
Kindly acknowledge receipt and advise on the expected response timeline.

Submitted via DumpAlert Automated Reporting System
Filed: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"""


def new_ticket() -> str:
    return f"DA-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"


def folium_color(label: str) -> str:
    return {"Low": "green", "Medium": "orange", "High": "red", "Critical": "darkred"}.get(label, "orange")


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/waste.png", width=60)
    st.title("DumpAlert")
    st.caption("AI-powered illegal dumping reporter")
    st.divider()

    demo_mode = st.toggle("Demo Mode (no API key needed)", value=True)
    st.caption("Use Demo Mode for presentations when API is unavailable.")

    if not demo_mode:
        api_key = st.text_input(
            "Gemini API Key",
            value=os.getenv("GEMINI_API_KEY", ""),
            type="password",
            help="Free key at aistudio.google.com"
        )
        if not api_key:
            st.warning("Paste your Gemini API key or enable Demo Mode.")
    else:
        api_key = ""
        st.success("Demo Mode ON — AI results are simulated.")

    st.divider()
    st.subheader("Stats")
    reports = st.session_state.reports
    st.metric("Reports Filed", len(reports))
    if reports:
        avg = sum(r["severity"] for r in reports) / len(reports)
        critical = sum(1 for r in reports if r["severity"] >= 8)
        st.metric("Avg Severity", f"{avg:.1f} / 10")
        st.metric("Critical Cases", critical)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📷 Report a Dump", "📄 Complaint & File", "📊 Dashboard"])

# ══ TAB 1 — REPORT ════════════════════════════════════════════════════════════
with tab1:
    st.title("Report Illegal Dumping")
    st.caption("Upload a photo → AI classifies the waste in seconds")

    left, right = st.columns([1, 1], gap="large")

    with left:
        st.subheader("Step 1 — Photo")
        source = st.radio("Photo source", ["Upload image", "Use camera"], horizontal=True)
        img = None

        if source == "Upload image":
            f = st.file_uploader("Choose a photo", type=["jpg", "jpeg", "png"])
            if f:
                img = Image.open(f)
                st.image(img, use_container_width=True)
        else:
            shot = st.camera_input("Take a photo")
            if shot:
                img = Image.open(shot)

        st.subheader("Step 2 — Location")
        address = st.text_input("Street address (optional)", placeholder="e.g. 12 Ring Road, Mumbai")
        c1, c2 = st.columns(2)
        with c1:
            lat = st.number_input("Latitude", value=19.0760, format="%.4f")
        with c2:
            lon = st.number_input("Longitude", value=72.8777, format="%.4f")
        st.caption("Right-click any spot in Google Maps → copy coordinates")

        go = st.button(
            "Analyze Waste with AI",
            type="primary",
            use_container_width=True,
            disabled=not img
        )

    with right:
        st.subheader("Step 3 — AI Result")

        if go and img:
            with st.spinner("Gemini AI is analyzing your photo…"):
                try:
                    if demo_mode:
                        result = classify_waste_demo(img)
                    else:
                        result = classify_waste(img, api_key)
                    st.session_state.update({
                        "cls": result,
                        "img": img,
                        "address": address,
                        "lat": lat,
                        "lon": lon,
                    })
                except json.JSONDecodeError:
                    st.error("AI returned an unexpected format. Try again.")
                    result = None
                except Exception as e:
                    st.error(f"API error: {e}")
                    result = None

        if "cls" in st.session_state:
            c = st.session_state.cls
            color = severity_color(c.get("severity", 5))

            if not c.get("waste_detected"):
                st.warning("No illegal dumping detected. Try a clearer photo showing the waste.")
            else:
                pct = c.get("severity", 5) * 10
                st.markdown(f"""
<div style="background:#1e1e1e;border-radius:12px;padding:20px;border-left:6px solid {color}">
  <div style="color:{color};font-size:22px;font-weight:700">
    {c.get("severity_label","?")} Severity &nbsp;·&nbsp; {c.get("severity","?")}/10
  </div>
  <div style="background:#333;border-radius:8px;height:10px;margin:10px 0">
    <div style="background:{color};width:{pct}%;border-radius:8px;height:10px"></div>
  </div>
  <table style="color:#ccc;width:100%;font-size:14px">
    <tr><td><b>Waste type</b></td><td>{c.get("waste_type","").title()}</td></tr>
    <tr><td><b>Health risk</b></td><td>{c.get("health_risk","Unknown")}</td></tr>
    <tr><td><b>Volume</b></td><td>{c.get("estimated_volume","Unknown")}</td></tr>
  </table>
  <hr style="border-color:#444;margin:12px 0">
  <p style="color:#bbb;font-size:14px;margin:0">{c.get("description","")}</p>
</div>
""", unsafe_allow_html=True)

                st.info(f"**Recommended action:** {c.get('recommended_action', '')}")

                # mini map
                m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=15)
                folium.Marker(
                    [st.session_state.lat, st.session_state.lon],
                    popup=f"{c.get('waste_type','').title()} dump · severity {c.get('severity','')}",
                    icon=folium.Icon(color="red", icon="exclamation-sign")
                ).add_to(m)
                st_folium(m, height=220, width=None, returned_objects=[])

                st.success("Analysis done — go to **Complaint & File** tab to submit your report.")

# ══ TAB 2 — COMPLAINT ════════════════════════════════════════════════════════
with tab2:
    st.title("Auto-Generated Complaint")

    if "cls" not in st.session_state:
        st.info("Complete the analysis in the **Report a Dump** tab first.")
    else:
        c = st.session_state.cls
        color = severity_color(c.get("severity", 5))

        col_letter, col_meta = st.columns([2, 1], gap="large")

        with col_letter:
            st.subheader("Complaint Letter")
            st.caption("Fully editable — review before filing")
            draft = build_complaint(
                c,
                st.session_state.get("address", ""),
                st.session_state.get("lat", 0.0),
                st.session_state.get("lon", 0.0),
            )
            edited = st.text_area("Edit complaint text", value=draft, height=420)

            council_email = st.text_input("Council / authority email", value="complaints@municipality.gov")

            file_btn = st.button("Submit Report via Open311", type="primary", use_container_width=True)

            if file_btn:
                with st.spinner("Connecting to Open311 API…"):
                    time.sleep(1.8)
                ticket_id = new_ticket()
                report_entry = {
                    "ticket_id": ticket_id,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "waste_type": c.get("waste_type", "Unknown"),
                    "severity": c.get("severity", 5),
                    "severity_label": c.get("severity_label", "Medium"),
                    "address": st.session_state.get("address", "Unknown"),
                    "lat": st.session_state.get("lat", 0.0),
                    "lon": st.session_state.get("lon", 0.0),
                    "health_risk": c.get("health_risk", "Unknown"),
                    "status": "Open",
                    "email": council_email,
                }
                st.session_state.reports.append(report_entry)
                st.session_state.last_ticket = ticket_id
                st.rerun()

        with col_meta:
            st.subheader("Report Card")
            st.markdown(f"""
<div style="background:#1e1e1e;border-radius:12px;padding:18px;border-top:4px solid {color}">
  <div style="color:{color};font-size:28px;font-weight:800">{c.get("severity_label","?")}</div>
  <div style="color:#888;font-size:12px;margin-bottom:12px">Severity Classification</div>
  <div style="color:#ddd"><b>Type:</b> {c.get("waste_type","").title()}</div>
  <div style="color:#ddd"><b>Health Risk:</b> {c.get("health_risk","?")}</div>
  <div style="color:#ddd"><b>Volume:</b> {c.get("estimated_volume","?")}</div>
  <div style="color:#ddd"><b>Score:</b> {c.get("severity","?")}/10</div>
</div>
""", unsafe_allow_html=True)

            if "last_ticket" in st.session_state:
                st.success("Report successfully filed!")
                st.markdown(f"""
<div style="background:#0d1b2a;border:2px solid #00d4ff;border-radius:10px;padding:16px;text-align:center;margin-top:12px">
  <div style="color:#888;font-size:12px">TICKET ID</div>
  <div style="color:#00d4ff;font-size:26px;font-weight:800;letter-spacing:2px">{st.session_state.last_ticket}</div>
  <div style="color:#888;font-size:12px;margin-top:4px">Status: 🟡 Open</div>
</div>
""", unsafe_allow_html=True)
                st.caption("Show this ticket ID when following up with authorities")

# ══ TAB 3 — DASHBOARD ════════════════════════════════════════════════════════
with tab3:
    st.title("Reports Dashboard")

    if not st.session_state.reports:
        st.info("No reports yet. File your first report in the **Report a Dump** tab.")
    else:
        rpts = st.session_state.reports

        # KPI row
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Reports", len(rpts))
        k2.metric("Open", sum(1 for r in rpts if r["status"] == "Open"))
        k3.metric("High / Critical", sum(1 for r in rpts if r["severity"] >= 7))
        avg_s = sum(r["severity"] for r in rpts) / len(rpts)
        k4.metric("Avg Severity", f"{avg_s:.1f} / 10")

        st.divider()

        # Map
        st.subheader("All Reported Locations")
        clat = sum(r["lat"] for r in rpts) / len(rpts)
        clon = sum(r["lon"] for r in rpts) / len(rpts)
        m2 = folium.Map(location=[clat, clon], zoom_start=12)
        for r in rpts:
            folium.Marker(
                [r["lat"], r["lon"]],
                popup=folium.Popup(
                    f"<b>{r['ticket_id']}</b><br>{r['waste_type'].title()}<br>Severity: {r['severity']}/10<br>Status: {r['status']}",
                    max_width=200
                ),
                tooltip=r["ticket_id"],
                icon=folium.Icon(color=folium_color(r["severity_label"]), icon="exclamation-sign")
            ).add_to(m2)
        st_folium(m2, height=380, width=None, returned_objects=[])

        st.divider()

        # Report list
        st.subheader("Filed Reports")
        for r in reversed(rpts):
            color = severity_color(r["severity"])
            with st.expander(f"{r['ticket_id']}  ·  {r['waste_type'].title()}  ·  {r['timestamp']}"):
                a, b, c_ = st.columns(3)
                with a:
                    st.markdown(f"**Severity:** <span style='color:{color}'>{r['severity']}/10 ({r['severity_label']})</span>", unsafe_allow_html=True)
                    st.write(f"**Health Risk:** {r['health_risk']}")
                with b:
                    st.write(f"**Address:** {r['address'] or 'Not provided'}")
                    st.write(f"**GPS:** {r['lat']:.4f}, {r['lon']:.4f}")
                with c_:
                    new_status = st.selectbox(
                        "Status",
                        ["Open", "In Progress", "Resolved"],
                        index=["Open", "In Progress", "Resolved"].index(r["status"]),
                        key=r["ticket_id"]
                    )
                    r["status"] = new_status
