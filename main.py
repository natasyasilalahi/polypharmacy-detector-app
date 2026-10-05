import uuid
import re
import json
import time
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

# { share_token: { result_data } }  — Feature 5: Share hasil via link
SHARED_RESULTS: dict[str, dict] = {}

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

class PatientProfile(BaseModel):
    elderly: bool = False      # usia >= 65 tahun
    ckd: bool = False          # chronic kidney disease
    liver: bool = False        # gangguan hati
    pregnant: bool = False     # hamil

class DrugTiming(BaseModel):
    drug: str
    hour: int    # 0-23
    minute: int  # 0-59

class DrugCheckRequest(BaseModel):
    drugs: List[str]
    patient: Optional[PatientProfile] = None
    timings: Optional[List[DrugTiming]] = None


class InteractionResult(BaseModel):
    status: str
    level: str
    color: str
    interactions: List[dict]
    summary: str
    risk_score: int
    timing_warnings: Optional[List[dict]] = None
    patient_adjustments: Optional[List[dict]] = None


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
        "mechanism": "pharmacodynamic",
        "mechanism_detail": "NSAID menghambat COX-1 → inhibisi agregasi trombosit + erosi mukosa lambung → risiko perdarahan GI",
        "cyp": None,
        "alternatives": ["Ganti ibuprofen dengan Parasetamol (asetaminofen) untuk nyeri ringan-sedang."],
        "description": (
            "Warfarin + Ibuprofen: NSAID seperti ibuprofen menghambat agregasi trombosit "
            "dan dapat menyebabkan erosi lambung, meningkatkan risiko perdarahan serius "
            "(GI bleeding, intrakranial). Hindari kombinasi ini; gunakan parasetamol sebagai alternatif."
        ),
        "patient_risk": {
            "elderly": {"score_add": 20, "note": "Lansia: risiko perdarahan GI 3–4× lebih tinggi. Gunakan dosis minimal atau ganti ke parasetamol."},
            "ckd":     {"score_add": 25, "note": "CKD: NSAID memperburuk fungsi ginjal dan meningkatkan kadar warfarin. Kontraindikasi relatif."},
            "liver":   {"score_add": 15, "note": "Gangguan Hati: metabolisme warfarin terganggu, efek antikoagulan tidak terprediksi."},
        },
    },
    {
        "drugs": {"warfarin", "aspirin"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 45,
        "mechanism": "pharmacodynamic",
        "mechanism_detail": "Dual antiplatelet/antikoagulan → efek sinergis penghambatan hemostasis → perdarahan berat",
        "cyp": None,
        "alternatives": ["Pertimbangkan monoterapi warfarin; bila antiplatelet diperlukan, konsultasikan dengan dokter spesialis."],
        "description": (
            "Warfarin + Aspirin: Kombinasi dua antikoagulan/antiplatelet sangat meningkatkan "
            "risiko perdarahan berat. Dapat menyebabkan perdarahan gastrointestinal, intrakranial, "
            "atau fatal. Hindari kecuali atas indikasi khusus dengan pemantauan ketat."
        ),
        "patient_risk": {
            "elderly": {"score_add": 20, "note": "Lansia: risiko perdarahan fatal meningkat signifikan. Monitor INR setiap minggu."},
            "ckd":     {"score_add": 15, "note": "CKD: klirens ginjal berkurang, akumulasi kedua obat meningkat."},
        },
    },
    {
        "drugs": {"metformin", "alcohol"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 42,
        "mechanism": "pharmacodynamic",
        "mechanism_detail": "Alkohol + Metformin → inhibisi glukoneogenesis hepatik berlebih + peningkatan laktat → asidosis laktat",
        "cyp": None,
        "alternatives": ["Hindari konsumsi alkohol sepenuhnya selama terapi metformin."],
        "description": (
            "Metformin + Alkohol: Konsumsi alkohol bersamaan dengan metformin meningkatkan risiko "
            "asidosis laktat yang berpotensi mengancam jiwa. Alkohol juga mengganggu kontrol gula "
            "darah dan dapat menyebabkan hipoglikemia mendalam."
        ),
        "patient_risk": {
            "liver": {"score_add": 30, "note": "Gangguan Hati: risiko asidosis laktat sangat tinggi. KONTRAINDIKASI ABSOLUT."},
            "ckd":   {"score_add": 20, "note": "CKD: metformin terakumulasi → risiko asidosis laktat meningkat drastis."},
        },
    },
    {
        "drugs": {"ssri", "maoi"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 50,
        "mechanism": "pharmacodynamic",
        "mechanism_detail": "SSRI + MAOI → akumulasi serotonin berlebih di sinaps → sindrom serotonin (agitasi, hipertermia, kejang)",
        "cyp": None,
        "alternatives": ["Tunggu minimal 14 hari setelah menghentikan MAOI sebelum memulai SSRI. Konsultasikan psikiater."],
        "description": (
            "SSRI + MAOI: Kombinasi ini dapat menyebabkan sindrom serotonin yang mengancam jiwa — "
            "ditandai agitasi, tremor, hipertermia, kejang, dan koma. Jangan gunakan bersamaan; "
            "tunggu minimal 14 hari setelah menghentikan MAOI sebelum memulai SSRI."
        ),
        "patient_risk": {
            "elderly": {"score_add": 10, "note": "Lansia: metabolisme lebih lambat, washout period harus diperpanjang hingga 21 hari."},
        },
    },
    {
        "drugs": {"simvastatin", "amiodarone"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 40,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "Amiodarone inhibisi CYP3A4 → kadar simvastatin naik drastis → miopati/rabdomiolisis",
        "cyp": "CYP3A4",
        "alternatives": ["Ganti simvastatin dengan rosuvastatin atau pravastatin yang tidak dimetabolisme CYP3A4."],
        "description": (
            "Simvastatin + Amiodarone: Amiodarone menghambat enzim CYP3A4 sehingga meningkatkan "
            "kadar simvastatin secara drastis, meningkatkan risiko miopati dan rabdomiolisis "
            "(kerusakan otot berat) yang dapat menyebabkan gagal ginjal akut."
        ),
        "patient_risk": {
            "elderly": {"score_add": 15, "note": "Lansia: massa otot berkurang, rabdomiolisis berdampak lebih berat."},
            "ckd":     {"score_add": 20, "note": "CKD: gagal ginjal akibat rabdomiolisis lebih sulit pulih."},
        },
    },
    {
        "drugs": {"digoxin", "amiodarone"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 45,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "Amiodarone inhibisi P-glikoprotein & CYP → kadar digoxin meningkat 2× → toksisitas digoxin",
        "cyp": "P-gp / CYP",
        "alternatives": ["Kurangi dosis digoxin 50% dan pantau kadar digoxin serum secara ketat setiap minggu."],
        "description": (
            "Digoxin + Amiodarone: Amiodarone meningkatkan kadar digoxin dalam darah secara "
            "signifikan (hingga 2x lipat), berisiko menyebabkan toksisitas digoxin: mual, "
            "aritmia berbahaya, bahkan henti jantung. Dosis digoxin harus dikurangi 50% dan "
            "kadar digoxin harus dipantau ketat."
        ),
        "patient_risk": {
            "elderly": {"score_add": 20, "note": "Lansia: volume distribusi digoxin berkurang, toksisitas terjadi pada kadar lebih rendah."},
            "ckd":     {"score_add": 25, "note": "CKD: digoxin terutama diekskresikan ginjal — akumulasi sangat berbahaya."},
        },
    },
    # ── MODERATE ────────────────────────────────────────────────────────────
    {
        "drugs": {"lisinopril", "potassium"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 20,
        "mechanism": "pharmacodynamic",
        "mechanism_detail": "ACE inhibitor mengurangi aldosteron → retensi kalium ginjal + suplemen kalium → hiperkalemia",
        "cyp": None,
        "alternatives": ["Monitor kadar kalium serum secara rutin; kurangi atau hentikan suplemen kalium bila tidak diperlukan."],
        "description": (
            "Lisinopril + Potassium: ACE inhibitor seperti lisinopril mengurangi ekskresi kalium "
            "oleh ginjal. Suplemen kalium tambahan dapat menyebabkan hiperkalemia (kadar kalium "
            "tinggi) yang berpotensi menyebabkan aritmia jantung. Pantau elektrolit secara berkala."
        ),
        "patient_risk": {
            "elderly": {"score_add": 10, "note": "Lansia: fungsi ginjal menurun, ekskresi kalium berkurang — monitor lebih ketat."},
            "ckd":     {"score_add": 20, "note": "CKD: hiperkalemia sangat mungkin terjadi. Pertimbangkan hentikan suplemen kalium."},
        },
    },
    {
        "drugs": {"metformin", "ibuprofen"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 22,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "NSAID menurunkan aliran darah ginjal → GFR turun → klirens metformin berkurang → akumulasi → asidosis laktat",
        "cyp": None,
        "alternatives": ["Gunakan parasetamol sebagai analgesik alternatif; hindari NSAID pada pasien dengan gangguan ginjal."],
        "description": (
            "Metformin + Ibuprofen: NSAID seperti ibuprofen dapat menurunkan fungsi ginjal, "
            "mengurangi ekskresi metformin, dan meningkatkan risiko asidosis laktat. Gunakan "
            "dengan hati-hati pada pasien usia lanjut atau dengan gangguan ginjal."
        ),
        "patient_risk": {
            "elderly": {"score_add": 20, "note": "Lansia: kombinasi ini menjadi KRITIS. GFR sering sudah rendah pada lansia."},
            "ckd":     {"score_add": 30, "note": "CKD: kombinasi ini menjadi KRITIS. Kontraindikasi relatif kuat."},
        },
    },
    {
        "drugs": {"ciprofloxacin", "antacid"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 18,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "Kation Al³⁺/Mg²⁺ dalam antasida membentuk chelat tidak larut dengan ciprofloxacin → absorpsi turun 90%",
        "cyp": None,
        "alternatives": ["Berikan ciprofloxacin 2 jam sebelum atau 6 jam setelah antasida untuk menghindari chelasi."],
        "description": (
            "Ciprofloxacin + Antasida: Antasida yang mengandung aluminium atau magnesium "
            "mengikat ciprofloxacin di saluran cerna dan menurunkan penyerapannya hingga 90%. "
            "Berikan ciprofloxacin 2 jam sebelum atau 6 jam setelah antasida."
        ),
        "patient_risk": {},
        "timing_sensitive": True,
        "timing_gap_hours": 2,
    },
    {
        "drugs": {"amlodipine", "simvastatin"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 20,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "Amlodipine inhibisi parsial CYP3A4 → kadar simvastatin meningkat moderat → risiko miopati",
        "cyp": "CYP3A4",
        "alternatives": ["Batasi dosis simvastatin maksimal 20 mg/hari; pertimbangkan beralih ke rosuvastatin."],
        "description": (
            "Amlodipine + Simvastatin: Amlodipine menghambat metabolisme simvastatin melalui "
            "CYP3A4, meningkatkan konsentrasi plasma simvastatin dan risiko miopati. Dosis "
            "simvastatin tidak boleh melebihi 20 mg/hari bila dikombinasikan dengan amlodipine."
        ),
        "patient_risk": {
            "elderly": {"score_add": 10, "note": "Lansia: massa otot lebih rendah, gejala miopati mungkin tidak terdeteksi dini."},
        },
    },
    {
        "drugs": {"fluoxetine", "tramadol"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 25,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "Fluoxetine inhibisi CYP2D6 → aktivasi tramadol terganggu + akumulasi serotonin → sindrom serotonin ringan",
        "cyp": "CYP2D6",
        "alternatives": ["Pertimbangkan analgesik alternatif non-opioid; bila tramadol diperlukan, gunakan dosis minimal dan pantau ketat."],
        "description": (
            "Fluoxetine + Tramadol: Fluoxetine menghambat CYP2D6 yang dibutuhkan untuk aktivasi "
            "tramadol, menurunkan efektivitasnya. Selain itu, kombinasi ini meningkatkan risiko "
            "sindrom serotonin ringan hingga sedang. Pantau respons klinis dengan cermat."
        ),
        "patient_risk": {
            "elderly": {"score_add": 10, "note": "Lansia: risiko sedasi berlebih dan gangguan keseimbangan meningkat."},
        },
    },
    {
        "drugs": {"spironolactone", "potassium"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 18,
        "mechanism": "pharmacodynamic",
        "mechanism_detail": "Spironolactone blokir aldosteron → retensi kalium + suplemen kalium eksternal → hiperkalemia",
        "cyp": None,
        "alternatives": ["Hentikan suplemen kalium bila tidak ada indikasi defisiensi; monitor kadar kalium serum secara rutin."],
        "description": (
            "Spironolactone + Potassium: Spironolactone adalah diuretik hemat kalium. Pemberian "
            "suplemen kalium bersamaan dapat menyebabkan hiperkalemia, terutama pada pasien dengan "
            "gangguan ginjal. Monitor kadar kalium serum secara rutin."
        ),
        "patient_risk": {
            "elderly": {"score_add": 10, "note": "Lansia: fungsi ginjal berkurang, risiko hiperkalemia lebih tinggi."},
            "ckd":     {"score_add": 20, "note": "CKD: kombinasi ini menjadi KRITIS pada CKD stadium 3+."},
        },
    },
]

# Timing-sensitive pairs (drug_a, drug_b, min gap hours)
TIMING_PAIRS = [
    ({"ciprofloxacin", "antacid"}, 2, "Beri jarak minimal 2 jam antara ciprofloxacin dan antasida."),
    ({"amlodipine", "simvastatin"}, 0, None),  # no timing restriction, already handled by rules
]


# ---------------------------------------------------------------------------
# Drug check endpoint
# ---------------------------------------------------------------------------

@app.post("/api/check-drugs", response_model=InteractionResult)
def check_drugs(payload: DrugCheckRequest, session: Optional[str] = Cookie(default=None)):
    if not session or session not in SESSIONS:
        return JSONResponse({"message": "Unauthorized"}, status_code=401)

    drug_set = {d.strip().lower() for d in payload.drugs if d.strip()}
    patient = payload.patient or PatientProfile()
    timings = payload.timings or []

    found_interactions = []
    highest_status = "safe"
    total_score = 0
    patient_adjustments = []

    for rule in RULES:
        if rule["drugs"].issubset(drug_set):
            base_score = rule.get("score", 0)
            adj_score = base_score
            adj_notes = []

            # Patient profile adjustments
            pat_risk = rule.get("patient_risk", {})
            if patient.elderly and "elderly" in pat_risk:
                adj_score += pat_risk["elderly"]["score_add"]
                adj_notes.append(pat_risk["elderly"]["note"])
            if patient.ckd and "ckd" in pat_risk:
                adj_score += pat_risk["ckd"]["score_add"]
                adj_notes.append(pat_risk["ckd"]["note"])
            if patient.liver and "liver" in pat_risk:
                adj_score += pat_risk["liver"]["score_add"]
                adj_notes.append(pat_risk["liver"]["note"])
            if patient.pregnant and "pregnant" in pat_risk:
                adj_score += pat_risk["pregnant"]["score_add"]
                adj_notes.append(pat_risk["pregnant"]["note"])

            # Recalculate status based on adjusted score
            effective_status = rule["status"]
            if adj_score >= 60:
                effective_status = "critical"
            elif adj_score >= 30 and effective_status == "safe":
                effective_status = "moderate"

            if adj_notes:
                patient_adjustments.append({
                    "drugs": list(rule["drugs"]),
                    "original_level": rule["level"],
                    "adjusted_score": min(adj_score, 100),
                    "notes": adj_notes,
                })

            found_interactions.append({
                "drugs": list(rule["drugs"]),
                "level": "Kritis" if effective_status == "critical" else rule["level"],
                "description": rule["description"],
                "alternatives": rule.get("alternatives", []),
                "mechanism": rule.get("mechanism"),
                "mechanism_detail": rule.get("mechanism_detail"),
                "cyp": rule.get("cyp"),
            })
            total_score += adj_score

            if effective_status == "critical":
                highest_status = "critical"
            elif effective_status == "moderate" and highest_status != "critical":
                highest_status = "moderate"

    risk_score = min(total_score, 100)

    # ── Timing warnings ────────────────────────────────────────────────────
    timing_warnings = []
    if timings and len(timings) >= 2:
        timing_map = {t.drug.strip().lower(): t.hour * 60 + t.minute for t in timings}

        for rule in RULES:
            if not rule["drugs"].issubset(drug_set):
                continue
            if not rule.get("timing_sensitive"):
                continue
            gap_h = rule.get("timing_gap_hours", 0)
            if gap_h <= 0:
                continue

            drugs_list = list(rule["drugs"])
            d1, d2 = drugs_list[0], drugs_list[1]
            if d1 in timing_map and d2 in timing_map:
                gap_actual = abs(timing_map[d1] - timing_map[d2])
                if gap_actual < gap_h * 60:
                    timing_warnings.append({
                        "drugs": drugs_list,
                        "gap_required_hours": gap_h,
                        "gap_actual_minutes": gap_actual,
                        "message": rule.get("alternatives", ["Atur jarak waktu minum obat."])[0],
                    })

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
        timing_warnings=timing_warnings if timing_warnings else None,
        patient_adjustments=patient_adjustments if patient_adjustments else None,
    )


# ---------------------------------------------------------------------------
# Drug catalogue endpoint (for autocomplete & kamus)
# ---------------------------------------------------------------------------

# Extended drug info catalogue for the scanner feature
# Brand name → generic name mapping for OCR (Feature 1)
BRAND_TO_GENERIC: dict[str, str] = {
    # Warfarin
    "coumadin": "warfarin", "jantoven": "warfarin",
    # Ibuprofen
    "advil": "ibuprofen", "motrin": "ibuprofen", "proris": "ibuprofen", "farsifen": "ibuprofen",
    # Aspirin
    "aspilets": "aspirin", "thrombo": "aspirin", "bayer": "aspirin",
    # Metformin
    "glucophage": "metformin", "diabex": "metformin",
    # Amiodarone
    "cordarone": "amiodarone", "pacerone": "amiodarone",
    # Simvastatin
    "zocor": "simvastatin", "lipcut": "simvastatin",
    # Digoxin
    "lanoxin": "digoxin",
    # Lisinopril
    "zestril": "lisinopril", "prinivil": "lisinopril",
    # Potassium
    "aspar": "potassium", "kcl": "potassium",
    # Ciprofloxacin
    "ciproxin": "ciprofloxacin", "baquinor": "ciprofloxacin",
    # Antacid
    "mylanta": "antacid", "promag": "antacid",
    # Amlodipine
    "norvasc": "amlodipine", "tensivask": "amlodipine",
    # Fluoxetine
    "prozac": "fluoxetine", "nopres": "fluoxetine",
    # Tramadol
    "tramal": "tramadol", "ultram": "tramadol",
    # Spironolactone
    "aldactone": "spironolactone",
    # Paracetamol
    "panadol": "paracetamol", "tempra": "paracetamol", "sanmol": "paracetamol", "biogesic": "paracetamol",
    # Amoxicillin
    "amoxil": "amoxicillin", "trimox": "amoxicillin", "yusimox": "amoxicillin",
    # Omeprazole
    "losec": "omeprazole", "prilosec": "omeprazole",
    # SSRI / MAOI brands
    "zoloft": "ssri", "lexapro": "ssri", "paxil": "ssri",
    "nardil": "maoi", "parnate": "maoi", "marplan": "maoi",
}

DRUG_INFO: dict[str, dict] = {
    "warfarin": {
        "name": "Warfarin",
        "category": "Antikoagulan",
        "description": "Obat pengencer darah yang mencegah pembekuan darah berlebih. Digunakan untuk mencegah stroke, emboli paru, dan trombosis vena dalam.",
        "common_brands": ["Coumadin", "Jantoven"],
        "side_effects": "Perdarahan, mudah memar, urin berwarna gelap.",
        "notes": "Membutuhkan pemantauan INR rutin. Banyak interaksi dengan obat dan makanan.",
    },
    "ibuprofen": {
        "name": "Ibuprofen",
        "category": "NSAID (Anti-Inflamasi Non-Steroid)",
        "description": "Obat pereda nyeri, demam, dan peradangan. Tersedia bebas untuk nyeri ringan hingga sedang.",
        "common_brands": ["Advil", "Motrin", "Proris", "Farsifen"],
        "side_effects": "Gangguan lambung, mual, peningkatan risiko perdarahan GI.",
        "notes": "Hindari pada pasien dengan riwayat tukak lambung atau gangguan ginjal.",
    },
    "aspirin": {
        "name": "Aspirin",
        "category": "Antiplatelet / NSAID",
        "description": "Digunakan sebagai antiplatelet dosis rendah untuk pencegahan serangan jantung dan stroke, serta pereda nyeri dan demam.",
        "common_brands": ["Aspilets", "Thrombo Aspilets", "Bayer Aspirin"],
        "side_effects": "Iritasi lambung, perdarahan, tinnitus pada dosis tinggi.",
        "notes": "Dosis rendah (80-100 mg) untuk kardioproteksi; dosis tinggi untuk analgesik.",
    },
    "metformin": {
        "name": "Metformin",
        "category": "Antidiabetik Oral (Biguanide)",
        "description": "Obat lini pertama untuk diabetes tipe 2. Menurunkan produksi glukosa di hati dan meningkatkan sensitivitas insulin.",
        "common_brands": ["Glucophage", "Metformin Hexal", "Diabex"],
        "side_effects": "Mual, diare, gangguan pencernaan (berkurang bila diminum bersama makan).",
        "notes": "Hentikan sebelum prosedur kontras radiologi. Hindari alkohol.",
    },
    "amiodarone": {
        "name": "Amiodarone",
        "category": "Antiaritmia Kelas III",
        "description": "Obat untuk mengobati aritmia jantung berat termasuk fibrilasi ventrikel dan takikardia ventrikel.",
        "common_brands": ["Cordarone", "Pacerone"],
        "side_effects": "Toksisitas paru, tiroid, hati, fotosensitivitas, deposit kornea.",
        "notes": "Half-life sangat panjang (40-55 hari). Banyak interaksi obat serius.",
    },
    "simvastatin": {
        "name": "Simvastatin",
        "category": "Statin (Penurun Kolesterol)",
        "description": "Obat untuk menurunkan kadar kolesterol LDL dan trigliserida, serta meningkatkan HDL dalam darah.",
        "common_brands": ["Zocor", "Simvastatin Generik", "Lipcut"],
        "side_effects": "Nyeri otot (miopati), peningkatan enzim hati.",
        "notes": "Diminum malam hari. Hindari jus grapefruit. Batasi dosis bila dikombinasi dengan amlodipine.",
    },
    "digoxin": {
        "name": "Digoxin",
        "category": "Glikosida Jantung",
        "description": "Digunakan untuk gagal jantung dan fibrilasi atrium. Memperkuat kontraksi jantung dan memperlambat denyut jantung.",
        "common_brands": ["Lanoxin", "Digoxin Generik"],
        "side_effects": "Mual, muntah, gangguan penglihatan (kuning/hijau), aritmia.",
        "notes": "Jendela terapeutik sempit — kadar toksik sangat dekat dengan kadar terapi. Monitor ketat.",
    },
    "lisinopril": {
        "name": "Lisinopril",
        "category": "ACE Inhibitor",
        "description": "Obat antihipertensi dan untuk gagal jantung. Menghambat enzim ACE sehingga menurunkan tekanan darah.",
        "common_brands": ["Zestril", "Prinivil", "Lisinopril Generik"],
        "side_effects": "Batuk kering persisten, hiperkalemia, penurunan tekanan darah berlebih.",
        "notes": "Kontraindikasi pada kehamilan. Pantau fungsi ginjal dan kadar kalium.",
    },
    "potassium": {
        "name": "Kalium (Potassium)",
        "category": "Suplemen Elektrolit",
        "description": "Suplemen kalium untuk mengatasi hipokalemia (kekurangan kalium). Penting untuk fungsi otot dan jantung.",
        "common_brands": ["KSR", "Aspar-K", "Kalium Klorida"],
        "side_effects": "Mual, iritasi lambung, hiperkalemia bila overdosis.",
        "notes": "Selalu monitor kadar kalium serum. Hindari kombinasi dengan ACE inhibitor atau diuretik hemat kalium.",
    },
    "ciprofloxacin": {
        "name": "Ciprofloxacin",
        "category": "Antibiotik Fluorokuinolon",
        "description": "Antibiotik spektrum luas untuk infeksi saluran kemih, pernapasan, GI, dan kulit.",
        "common_brands": ["Ciproxin", "Baquinor", "Ciprofloxacin Generik"],
        "side_effects": "Mual, diare, sakit kepala, tendinitis (jarang).",
        "notes": "Jangan diminum bersamaan dengan antasida. Dapat memperpanjang interval QT.",
    },
    "antacid": {
        "name": "Antasida",
        "category": "Antasida / Obat Lambung",
        "description": "Menetralkan asam lambung untuk mengatasi nyeri ulu hati, maag, dan refluks asam.",
        "common_brands": ["Mylanta", "Promag", "Antasida DOEN"],
        "side_effects": "Konstipasi (Al-Mg), diare (Mg), gangguan penyerapan mineral.",
        "notes": "Dapat menghambat penyerapan banyak obat lain. Beri jarak minimal 2 jam dengan obat lain.",
    },
    "amlodipine": {
        "name": "Amlodipine",
        "category": "Calcium Channel Blocker",
        "description": "Obat antihipertensi dan antiangina. Menghambat masuknya kalsium ke sel otot pembuluh darah sehingga pembuluh melebar.",
        "common_brands": ["Norvasc", "Tensivask", "Amlodipine Generik"],
        "side_effects": "Edema pergelangan kaki, sakit kepala, pusing, flushing.",
        "notes": "Kombinasi dengan simvastatin — batasi dosis simvastatin maks 20 mg/hari.",
    },
    "fluoxetine": {
        "name": "Fluoxetine",
        "category": "SSRI (Antidepresan)",
        "description": "Antidepresan golongan SSRI untuk depresi, gangguan panik, OCD, bulimia nervosa, dan PMDD.",
        "common_brands": ["Prozac", "Nopres", "Fluoxetine Generik"],
        "side_effects": "Insomnia, mual, agitasi, disfungsi seksual.",
        "notes": "Half-life panjang (1-4 hari). Interaksi serius dengan MAOI dan tramadol.",
    },
    "tramadol": {
        "name": "Tramadol",
        "category": "Analgesik Opioid (Lemah)",
        "description": "Obat pereda nyeri sedang hingga berat. Bekerja pada reseptor opioid dan menghambat reuptake serotonin/norepinefrin.",
        "common_brands": ["Tramal", "Ultram", "Tramadol Generik"],
        "side_effects": "Mual, pusing, konstipasi, risiko ketergantungan.",
        "notes": "Risiko sindrom serotonin bila dikombinasi dengan SSRI. Kurangi dosis pada gagal ginjal/hati.",
    },
    "spironolactone": {
        "name": "Spironolactone",
        "category": "Diuretik Hemat Kalium",
        "description": "Diuretik yang menghambat aldosteron. Digunakan untuk gagal jantung, hipertensi, dan edema.",
        "common_brands": ["Aldactone", "Spironolactone Generik"],
        "side_effects": "Hiperkalemia, ginekomastia (pria), gangguan menstruasi.",
        "notes": "Pantau kadar kalium serum. Hindari suplemen kalium bersamaan.",
    },
    "ssri": {
        "name": "SSRI (Selective Serotonin Reuptake Inhibitor)",
        "category": "Antidepresan",
        "description": "Golongan antidepresan yang mencakup fluoxetine, sertraline, escitalopram, paroxetine. Meningkatkan kadar serotonin di otak.",
        "common_brands": ["Prozac", "Zoloft", "Lexapro", "Paxil"],
        "side_effects": "Mual, insomnia, disfungsi seksual, agitasi.",
        "notes": "Jangan dikombinasi dengan MAOI. Tunggu 14 hari setelah stop MAOI.",
    },
    "maoi": {
        "name": "MAOI (Monoamine Oxidase Inhibitor)",
        "category": "Antidepresan",
        "description": "Antidepresan yang menghambat enzim MAO. Digunakan untuk depresi refrakter dan beberapa kondisi lain.",
        "common_brands": ["Nardil", "Parnate", "Marplan"],
        "side_effects": "Krisis hipertensi (dengan tiramin), sedasi, insomnia.",
        "notes": "Banyak interaksi makanan dan obat. Butuh diet rendah tiramin.",
    },
    "alcohol": {
        "name": "Alkohol (Ethanol)",
        "category": "Zat / Substansi",
        "description": "Etanol yang terkandung dalam minuman beralkohol. Berinteraksi dengan banyak obat dan dapat memperburuk efek samping.",
        "common_brands": ["-"],
        "side_effects": "Depresi SSP, hepatotoksisitas kronis, gangguan koordinasi.",
        "notes": "Hindari selama mengonsumsi hampir semua obat resep, terutama metformin, antikoagulan, dan CNS depressants.",
    },
    "paracetamol": {
        "name": "Paracetamol (Asetaminofen)",
        "category": "Analgesik / Antipiretik",
        "description": "Obat pereda nyeri dan penurun demam yang paling umum digunakan. Aman untuk sebagian besar pasien bila dosis tepat.",
        "common_brands": ["Panadol", "Tempra", "Sanmol", "Biogesic"],
        "side_effects": "Hepatotoksisitas pada overdosis.",
        "notes": "Dosis maksimal 4g/hari (dewasa). Kurangi dosis pada pasien dengan gangguan hati atau alkoholisme.",
    },
    "amoxicillin": {
        "name": "Amoxicillin",
        "category": "Antibiotik Penisilin",
        "description": "Antibiotik spektrum luas untuk infeksi bakteri saluran pernapasan, telinga, hidung, tenggorokan, dan saluran kemih.",
        "common_brands": ["Amoxil", "Trimox", "Yusimox", "Amoxicillin Generik"],
        "side_effects": "Ruam, diare, mual, reaksi alergi.",
        "notes": "Tanyakan riwayat alergi penisilin sebelum pemberian. Habiskan sesuai resep.",
    },
    "omeprazole": {
        "name": "Omeprazole",
        "category": "Proton Pump Inhibitor (PPI)",
        "description": "Mengurangi produksi asam lambung. Digunakan untuk tukak lambung, GERD, dan perlindungan lambung saat menggunakan NSAID.",
        "common_brands": ["Losec", "Prilosec", "Omeprazole Generik"],
        "side_effects": "Sakit kepala, diare, mual, hipomagnesemia jangka panjang.",
        "notes": "Dapat mengurangi efektivitas clopidogrel. Diminum 30 menit sebelum makan.",
    },
}


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
# Drug identification from OCR text endpoint
# Feature 1: Brand → Generic mapping applied here
# ---------------------------------------------------------------------------

class IdentifyRequest(BaseModel):
    text: str


@app.post("/api/identify-drug")
def identify_drug(payload: IdentifyRequest, session: Optional[str] = Cookie(default=None)):
    if not session or session not in SESSIONS:
        return JSONResponse({"message": "Unauthorized"}, status_code=401)

    # Normalize OCR text: lowercase, keep only alphanumeric + spaces
    raw = payload.text.lower()
    raw = re.sub(r'[^a-z0-9\s]', ' ', raw)
    tokens = set(raw.split())

    # Collect all known drug names (from RULES + DRUG_INFO + brand names)
    all_known = set(DRUG_INFO.keys()) | {d for rule in RULES for d in rule["drugs"]}

    matched_generics = {}  # generic_name → matched_via (brand or direct)

    for token in tokens:
        # 1. Check brand name mapping first (Feature 1)
        for brand, generic in BRAND_TO_GENERIC.items():
            if brand in token or token in brand:
                if generic not in matched_generics:
                    matched_generics[generic] = f"merek: {token}"
                break

        # 2. Direct generic name match (substring)
        for drug in all_known:
            if drug in token or token in drug:
                if drug not in matched_generics:
                    matched_generics[drug] = "nama generik"
                break

    if not matched_generics:
        return JSONResponse({"ok": False, "message": "Tidak ada obat yang dikenali dari teks ini."}, status_code=404)

    results = []
    for drug, via in matched_generics.items():
        info = DRUG_INFO.get(drug, {})
        results.append({
            "drug": drug,
            "info": info if info else None,
            "has_interactions": any(drug in rule["drugs"] for rule in RULES),
            "matched_via": via,
        })

    return {"ok": True, "matched": results}


# ---------------------------------------------------------------------------
# Feature 5: Share hasil via link
# ---------------------------------------------------------------------------

class ShareRequest(BaseModel):
    drugs: List[str]
    result: dict
    note: Optional[str] = None


@app.post("/api/share")
def create_share(payload: ShareRequest, session: Optional[str] = Cookie(default=None)):
    if not session or session not in SESSIONS:
        return JSONResponse({"message": "Unauthorized"}, status_code=401)

    token = str(uuid.uuid4())[:8]  # short 8-char token
    SHARED_RESULTS[token] = {
        "drugs": payload.drugs,
        "result": payload.result,
        "note": payload.note,
        "created_by": SESSIONS[session],
        "created_at": int(time.time()),
    }
    return {"ok": True, "token": token}


@app.get("/api/share/{token}")
def get_share(token: str):
    data = SHARED_RESULTS.get(token)
    if not data:
        return JSONResponse({"ok": False, "message": "Link tidak ditemukan atau sudah kadaluarsa."}, status_code=404)
    return {"ok": True, **data}


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

@app.get("/share/{token}")
def share_page(token: str):
    return FileResponse("index.html")

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return FileResponse("not_found.html", status_code=404)
