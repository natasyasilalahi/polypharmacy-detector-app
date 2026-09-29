import uuid
from fastapi import FastAPI, Cookie, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Polypharmacy Collision Detector")

# ---------------------------------------------------------------------------
# In-memory stores (prototype / demo only)
# ---------------------------------------------------------------------------

# { username: hashed_password }  — stores plain text for demo simplicity
USERS: dict[str, str] = {}

# { session_token: username }
SESSIONS: dict[str, str] = {}

# ---------------------------------------------------------------------------
# Auth Models
# ---------------------------------------------------------------------------

class AuthRequest(BaseModel):
    username: str
    password: str


# ---------------------------------------------------------------------------
# Auth Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/register")
def register(payload: AuthRequest, response: Response):
    username = payload.username.strip().lower()
    if not username or not payload.password:
        return JSONResponse({"ok": False, "message": "Username dan password tidak boleh kosong."}, status_code=400)
    if username in USERS:
        return JSONResponse({"ok": False, "message": "Username sudah digunakan."}, status_code=409)
    USERS[username] = payload.password
    token = str(uuid.uuid4())
    SESSIONS[token] = username
    response.set_cookie("session", token, httponly=True, samesite="lax", max_age=86400)
    return {"ok": True, "username": username}


@app.post("/api/login")
def login(payload: AuthRequest, response: Response):
    username = payload.username.strip().lower()
    if USERS.get(username) != payload.password:
        return JSONResponse({"ok": False, "message": "Username atau password salah."}, status_code=401)
    token = str(uuid.uuid4())
    SESSIONS[token] = username
    response.set_cookie("session", token, httponly=True, samesite="lax", max_age=86400)
    return {"ok": True, "username": username}


@app.post("/api/logout")
def logout(response: Response, session: Optional[str] = Cookie(default=None)):
    if session and session in SESSIONS:
        del SESSIONS[session]
    response.delete_cookie("session")
    return {"ok": True}


@app.get("/api/me")
def me(session: Optional[str] = Cookie(default=None)):
    if session and session in SESSIONS:
        return {"ok": True, "username": SESSIONS[session]}
    return JSONResponse({"ok": False}, status_code=401)


# ---------------------------------------------------------------------------
# Drug interaction Models
# ---------------------------------------------------------------------------

class DrugCheckRequest(BaseModel):
    drugs: List[str]


class InteractionResult(BaseModel):
    status: str
    level: str
    color: str
    interactions: List[dict]
    summary: str
    risk_score: int


# ---------------------------------------------------------------------------
# Interaction rules (static / demo data)
# ---------------------------------------------------------------------------

RULES = [
    # ── CRITICAL ────────────────────────────────────────────────────────────
    {
        "drugs": {"warfarin", "ibuprofen"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 40,
        "alternatives": ["Ganti ibuprofen dengan Parasetamol (asetaminofen) untuk nyeri ringan-sedang."],
        "description": (
            "Warfarin + Ibuprofen: NSAID seperti ibuprofen menghambat agregasi trombosit "
            "dan dapat menyebabkan erosi lambung, meningkatkan risiko perdarahan serius "
            "(GI bleeding, intrakranial). Hindari kombinasi ini; gunakan parasetamol sebagai alternatif."
        ),
    },
    {
        "drugs": {"warfarin", "aspirin"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 45,
        "alternatives": ["Pertimbangkan monoterapi warfarin; bila antiplatelet diperlukan, konsultasikan dengan dokter spesialis."],
        "description": (
            "Warfarin + Aspirin: Kombinasi dua antikoagulan/antiplatelet sangat meningkatkan "
            "risiko perdarahan berat. Dapat menyebabkan perdarahan gastrointestinal, intrakranial, "
            "atau fatal. Hindari kecuali atas indikasi khusus dengan pemantauan ketat."
        ),
    },
    {
        "drugs": {"metformin", "alcohol"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 42,
        "alternatives": ["Hindari konsumsi alkohol sepenuhnya selama terapi metformin."],
        "description": (
            "Metformin + Alkohol: Konsumsi alkohol bersamaan dengan metformin meningkatkan risiko "
            "asidosis laktat yang berpotensi mengancam jiwa. Alkohol juga mengganggu kontrol gula "
            "darah dan dapat menyebabkan hipoglikemia mendalam."
        ),
    },
    {
        "drugs": {"ssri", "maoi"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 50,
        "alternatives": ["Tunggu minimal 14 hari setelah menghentikan MAOI sebelum memulai SSRI. Konsultasikan psikiater."],
        "description": (
            "SSRI + MAOI: Kombinasi ini dapat menyebabkan sindrom serotonin yang mengancam jiwa — "
            "ditandai agitasi, tremor, hipertermia, kejang, dan koma. Jangan gunakan bersamaan; "
            "tunggu minimal 14 hari setelah menghentikan MAOI sebelum memulai SSRI."
        ),
    },
    {
        "drugs": {"simvastatin", "amiodarone"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 40,
        "alternatives": ["Ganti simvastatin dengan rosuvastatin atau pravastatin yang tidak dimetabolisme CYP3A4."],
        "description": (
            "Simvastatin + Amiodarone: Amiodarone menghambat enzim CYP3A4 sehingga meningkatkan "
            "kadar simvastatin secara drastis, meningkatkan risiko miopati dan rabdomiolisis "
            "(kerusakan otot berat) yang dapat menyebabkan gagal ginjal akut."
        ),
    },
    {
        "drugs": {"digoxin", "amiodarone"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 45,
        "alternatives": ["Kurangi dosis digoxin 50% dan pantau kadar digoxin serum secara ketat setiap minggu."],
        "description": (
            "Digoxin + Amiodarone: Amiodarone meningkatkan kadar digoxin dalam darah secara "
            "signifikan (hingga 2x lipat), berisiko menyebabkan toksisitas digoxin: mual, "
            "aritmia berbahaya, bahkan henti jantung. Dosis digoxin harus dikurangi 50% dan "
            "kadar digoxin harus dipantau ketat."
        ),
    },
    # ── MODERATE ────────────────────────────────────────────────────────────
    {
        "drugs": {"lisinopril", "potassium"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 20,
        "alternatives": ["Monitor kadar kalium serum secara rutin; kurangi atau hentikan suplemen kalium bila tidak diperlukan."],
        "description": (
            "Lisinopril + Potassium: ACE inhibitor seperti lisinopril mengurangi ekskresi kalium "
            "oleh ginjal. Suplemen kalium tambahan dapat menyebabkan hiperkalemia (kadar kalium "
            "tinggi) yang berpotensi menyebabkan aritmia jantung. Pantau elektrolit secara berkala."
        ),
    },
    {
        "drugs": {"metformin", "ibuprofen"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 22,
        "alternatives": ["Gunakan parasetamol sebagai analgesik alternatif; hindari NSAID pada pasien dengan gangguan ginjal."],
        "description": (
            "Metformin + Ibuprofen: NSAID seperti ibuprofen dapat menurunkan fungsi ginjal, "
            "mengurangi ekskresi metformin, dan meningkatkan risiko asidosis laktat. Gunakan "
            "dengan hati-hati pada pasien usia lanjut atau dengan gangguan ginjal."
        ),
    },
    {
        "drugs": {"ciprofloxacin", "antacid"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 18,
        "alternatives": ["Berikan ciprofloxacin 2 jam sebelum atau 6 jam setelah antasida untuk menghindari chelasi."],
        "description": (
            "Ciprofloxacin + Antasida: Antasida yang mengandung aluminium atau magnesium "
            "mengikat ciprofloxacin di saluran cerna dan menurunkan penyerapannya hingga 90%. "
            "Berikan ciprofloxacin 2 jam sebelum atau 6 jam setelah antasida."
        ),
    },
    {
        "drugs": {"amlodipine", "simvastatin"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 20,
        "alternatives": ["Batasi dosis simvastatin maksimal 20 mg/hari; pertimbangkan beralih ke rosuvastatin."],
        "description": (
            "Amlodipine + Simvastatin: Amlodipine menghambat metabolisme simvastatin melalui "
            "CYP3A4, meningkatkan konsentrasi plasma simvastatin dan risiko miopati. Dosis "
            "simvastatin tidak boleh melebihi 20 mg/hari bila dikombinasikan dengan amlodipine."
        ),
    },
    {
        "drugs": {"fluoxetine", "tramadol"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 25,
        "alternatives": ["Pertimbangkan analgesik alternatif non-opioid; bila tramadol diperlukan, gunakan dosis minimal dan pantau ketat."],
        "description": (
            "Fluoxetine + Tramadol: Fluoxetine menghambat CYP2D6 yang dibutuhkan untuk aktivasi "
            "tramadol, menurunkan efektivitasnya. Selain itu, kombinasi ini meningkatkan risiko "
            "sindrom serotonin ringan hingga sedang. Pantau respons klinis dengan cermat."
        ),
    },
    {
        "drugs": {"spironolactone", "potassium"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 18,
        "alternatives": ["Hentikan suplemen kalium bila tidak ada indikasi defisiensi; monitor kadar kalium serum secara rutin."],
        "description": (
            "Spironolactone + Potassium: Spironolactone adalah diuretik hemat kalium. Pemberian "
            "suplemen kalium bersamaan dapat menyebabkan hiperkalemia, terutama pada pasien dengan "
            "gangguan ginjal. Monitor kadar kalium serum secara rutin."
        ),
    },
]


# ---------------------------------------------------------------------------
# Drug check endpoint
# ---------------------------------------------------------------------------

@app.post("/api/check-drugs", response_model=InteractionResult)
def check_drugs(payload: DrugCheckRequest, session: Optional[str] = Cookie(default=None)):
    if not session or session not in SESSIONS:
        return JSONResponse({"message": "Unauthorized"}, status_code=401)

    drug_set = {d.strip().lower() for d in payload.drugs if d.strip()}
    found_interactions = []
    highest_status = "safe"
    total_score = 0

    for rule in RULES:
        if rule["drugs"].issubset(drug_set):
            found_interactions.append({
                "drugs": list(rule["drugs"]),
                "level": rule["level"],
                "description": rule["description"],
                "alternatives": rule.get("alternatives", []),
            })
            total_score += rule.get("score", 0)
            if rule["status"] == "critical":
                highest_status = "critical"
            elif rule["status"] == "moderate" and highest_status != "critical":
                highest_status = "moderate"

    risk_score = min(total_score, 100)

    if highest_status == "critical":
        color, level, summary = "red", "Kritis", "Ditemukan interaksi berbahaya! Segera konsultasikan dengan dokter atau apoteker."
    elif highest_status == "moderate":
        color, level, summary = "yellow", "Sedang", "Ditemukan interaksi yang perlu diperhatikan. Pemantauan klinis disarankan."
    else:
        color, level, summary = "green", "Aman", "Tidak ditemukan interaksi berbahaya yang diketahui pada kombinasi obat ini."

    return InteractionResult(
        status=highest_status,
        level=level,
        color=color,
        interactions=found_interactions,
        summary=summary,
        risk_score=risk_score,
    )


# ---------------------------------------------------------------------------
# Drug catalogue endpoint (for autocomplete & kamus)
# ---------------------------------------------------------------------------

@app.get("/api/drugs")
def get_drugs(session: Optional[str] = Cookie(default=None)):
    if not session or session not in SESSIONS:
        return JSONResponse({"message": "Unauthorized"}, status_code=401)
    # Collect all unique drug names from RULES
    all_drugs = sorted({drug for rule in RULES for drug in rule["drugs"]})
    pairs = [
        {
            "drugs": list(rule["drugs"]),
            "level": rule["level"],
            "status": rule["status"],
        }
        for rule in RULES
    ]
    return {"drugs": all_drugs, "pairs": pairs}


# ---------------------------------------------------------------------------
# Serve frontend pages
# ---------------------------------------------------------------------------

app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
def root():
    return FileResponse("index.html")

@app.get("/login")
def login_page():
    return FileResponse("login.html")

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return FileResponse("not_found.html", status_code=404)
