import os
import uuid
import re
import json
import time
from fastapi import FastAPI, Cookie, Response, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Polypharmacy Collision Detector - Clinical AI Engine")

# ---------------------------------------------------------------------------
# In-memory stores (prototype / demo)
# ---------------------------------------------------------------------------

# Pre-seeded demo accounts for instant evaluation
USERS: dict[str, str] = {
    "apoteker": "apoteker123",
    "dokter": "dokter123",
    "admin": "admin123",
    "demo": "demo123",
}

# { session_token: username }
SESSIONS: dict[str, str] = {}

# { share_token: { result_data } }  — Share hasil via link
SHARE_FILE = "shared_results.json"
def load_shared() -> dict[str, dict]:
    if os.path.exists(SHARE_FILE):
        try:
            with open(SHARE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_shared(data: dict) -> None:
    try:
        with open(SHARE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass

SHARED_RESULTS: dict[str, dict] = load_shared()

# ---------------------------------------------------------------------------
# Auth Models & Endpoints
# ---------------------------------------------------------------------------

class AuthRequest(BaseModel):
    username: str
    password: str

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
        return {"ok": True, "username": SESSIONS[session], "is_guest": False}
    return {"ok": True, "username": "Tamu (Guest)", "is_guest": True}

# ---------------------------------------------------------------------------
# Clinical Data Models
# ---------------------------------------------------------------------------

class PatientProfile(BaseModel):
    elderly: bool = False      # usia >= 65 tahun
    ckd: bool = False          # chronic kidney disease / gangguan ginjal
    liver: bool = False        # gangguan fungsi hati
    pregnant: bool = False     # kehamilan

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
    resolved_drugs: Optional[List[dict]] = None

# ---------------------------------------------------------------------------
# Synonyms, Classes, and Brand Mappings
# ---------------------------------------------------------------------------

SYNONYMS: dict[str, str] = {
    "kalium": "potassium",
    "antasida": "antacid",
    "alkohol": "alcohol",
    "etanol": "alcohol",
    "parasetamol": "paracetamol",
    "asetaminofen": "paracetamol",
    "acetaminophen": "paracetamol",
    "asam asetilsalisilat": "aspirin",
    "asetosal": "aspirin",
    "asam mefenamat": "mefenamic acid",
    "natrium diklofenak": "diclofenac",
    "kalium diklofenak": "diclofenac",
    "besi": "iron",
    "zat besi": "iron",
    "ferrous": "iron",
}

BRAND_TO_GENERIC: dict[str, str] = {
    # Antikoagulan & Antiplatelet
    "coumadin": "warfarin", "jantoven": "warfarin", "simarc": "warfarin",
    "aspilets": "aspirin", "thrombo": "aspirin", "thrombo aspilets": "aspirin", "bayer": "aspirin", "cardioaspirin": "aspirin", "bodrexin": "aspirin",
    "plavix": "clopidogrel", "clopisan": "clopidogrel", "placta": "clopidogrel",
    # Analgesik & NSAID
    "advil": "ibuprofen", "motrin": "ibuprofen", "proris": "ibuprofen", "farsifen": "ibuprofen", "bufect": "ibuprofen", "brufen": "ibuprofen",
    "panadol": "paracetamol", "tempra": "paracetamol", "sanmol": "paracetamol", "biogesic": "paracetamol", "pamol": "paracetamol", "dumin": "paracetamol", "sumagesic": "paracetamol",
    "tramal": "tramadol", "ultram": "tramadol", "tradyl": "tramadol",
    "ponstan": "mefenamic acid", "mefinal": "mefenamic acid",
    "voltaren": "diclofenac", "cataflam": "diclofenac", "flamar": "diclofenac",
    "toradol": "ketorolac", "scantoma": "ketorolac",
    # Antidiabetes
    "glucophage": "metformin", "diabex": "metformin", "glumin": "metformin", "forbetes": "metformin",
    # Kardiovaskular & Antihipertensi
    "cordarone": "amiodarone", "pacerone": "amiodarone", "tiaryt": "amiodarone",
    "lanoxin": "digoxin", "fargoxin": "digoxin",
    "zestril": "lisinopril", "prinivil": "lisinopril", "tensipril": "lisinopril",
    "capoten": "captopril", "farmoten": "captopril",
    "norvasc": "amlodipine", "tensivask": "amlodipine", "amcor": "amlodipine", "divask": "amlodipine",
    "aldactone": "spironolactone", "letonal": "spironolactone", "spirola": "spironolactone",
    "lasix": "furosemide", "farsix": "furosemide", "impugan": "furosemide",
    # Statin (Penurun Kolesterol)
    "zocor": "simvastatin", "lipcut": "simvastatin", "cholestor": "simvastatin", "valesco": "simvastatin",
    "lipitor": "atorvastatin", "stator": "atorvastatin", "truvaz": "atorvastatin",
    "crestor": "rosuvastatin", "rosufer": "rosuvastatin",
    # Antibiotik & Lambung
    "ciproxin": "ciprofloxacin", "baquinor": "ciprofloxacin", "ciflos": "ciprofloxacin",
    "amoxil": "amoxicillin", "trimox": "amoxicillin", "yusimox": "amoxicillin", "hiconcil": "amoxicillin",
    "mylanta": "antacid", "promag": "antacid", "polysilane": "antacid", "gastrucid": "antacid", "magida": "antacid", "antasida doen": "antacid",
    "losec": "omeprazole", "prilosec": "omeprazole", "ozid": "omeprazole", "omz": "omeprazole",
    "nexium": "esomeprazole", "inpepsa": "sucralfate", "pantozol": "pantoprazole",
    "klacid": "clarithromycin", "abbotic": "clarithromycin", "bicrolin": "clarithromycin",
    # Psikiatri & SSP
    "prozac": "fluoxetine", "nopres": "fluoxetine", "kalxetin": "fluoxetine",
    "zoloft": "sertraline", "fridep": "sertraline",
    "lexapro": "escitalopram", "cipralex": "escitalopram",
    "paxil": "paroxetine", "seroxat": "paroxetine",
    "nardil": "phenelzine", "parnate": "tranylcypromine", "marplan": "isocarboxazid", "jumex": "selegiline",
    "valium": "diazepam", "stesolid": "diazepam",
    "frimania": "lithium",
    # Suplemen & Lainnya
    "aspar": "potassium", "kcl": "potassium", "ksr": "potassium",
    "euthyrox": "levothyroxine", "thyrax": "levothyroxine",
    "viagra": "sildenafil", "ericfil": "sildenafil",
    "nitrokaf": "nitroglycerin", "isdn": "isosorbide dinitrate", "cedocard": "isosorbide dinitrate",
    "zyloric": "allopurinol", "puricemia": "allopurinol",
    "imuran": "azathioprine",
    "rheumatrex": "methotrexate", "trexall": "methotrexate",
}

# Drug classes to facilitate broad clinical interaction mapping
DRUG_CLASSES: dict[str, set[str]] = {
    # SSRI
    "fluoxetine": {"ssri"}, "sertraline": {"ssri"}, "escitalopram": {"ssri"}, "citalopram": {"ssri"}, "paroxetine": {"ssri"}, "fluvoxamine": {"ssri"},
    # MAOI
    "phenelzine": {"maoi"}, "tranylcypromine": {"maoi"}, "isocarboxazid": {"maoi"}, "selegiline": {"maoi"}, "moclobemide": {"maoi"},
    # NSAID
    "ibuprofen": {"nsaid"}, "aspirin": {"nsaid", "antiplatelet"}, "mefenamic acid": {"nsaid"}, "diclofenac": {"nsaid"},
    "ketorolac": {"nsaid"}, "meloxicam": {"nsaid"}, "naproxen": {"nsaid"}, "indomethacin": {"nsaid"},
    # ACE-inhibitor & ARB
    "lisinopril": {"acei"}, "captopril": {"acei"}, "ramipril": {"acei"}, "enalapril": {"acei"},
    # Statin
    "simvastatin": {"statin"}, "atorvastatin": {"statin"}, "rosuvastatin": {"statin"}, "pravastatin": {"statin"},
    # PPI
    "omeprazole": {"ppi"}, "esomeprazole": {"ppi"}, "lansoprazole": {"ppi"}, "pantoprazole": {"ppi"}, "rabeprazole": {"ppi"},
    # Quinolone
    "ciprofloxacin": {"quinolone"}, "levofloxacin": {"quinolone"}, "moxifloxacin": {"quinolone"},
    # Nitrate
    "nitroglycerin": {"nitrate"}, "isosorbide dinitrate": {"nitrate"},
}

# ---------------------------------------------------------------------------
# Interaction Rules Database (25+ Comprehensive Clinical Rules)
# ---------------------------------------------------------------------------

RULES = [
    # ── 1. WARFARIN + IBUPROFEN (CRITICAL) ──────────────────────────────────
    {
        "drugs": {"warfarin", "ibuprofen"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 40,
        "mechanism": "pharmacodynamic",
        "mechanism_detail": "NSAID menghambat COX-1 → agregasi trombosit dihambat + erosi mukosa GI → risiko perdarahan masif",
        "cyp": None,
        "alternatives": ["Ganti ibuprofen dengan Parasetamol (asetaminofen) untuk nyeri ringan-sedang."],
        "description": "Warfarin + Ibuprofen: Kombinasi antikoagulan dan NSAID menghambat agregasi trombosit serta mengikis mukosa saluran cerna, melipatgandakan risiko perdarahan internal fatal (GI & intrakranial).",
        "patient_risk": {
            "elderly": {"score_add": 20, "note": "Lansia (≥65 th): Integritas vaskular dan mukosa menurun, risiko perdarahan GI 3–4× lebih tinggi. Gunakan parasetamol."},
            "ckd": {"score_add": 25, "note": "Gagal Ginjal (CKD): NSAID menurunkan laju filtrasi glomerulus (GFR) dan menghambat ekskresi obat. Kontraindikasi relatif."},
            "liver": {"score_add": 20, "note": "Gangguan Hati: Sintesis faktor pembekuan darah terganggu; efek antikoagulasi warfarin sulit diprediksi."},
            "pregnant": {"score_add": 35, "note": "Kehamilan: Warfarin teratogenik berat (sindrom warfarin fetal), NSAID memicu penutupan prematur duktus arteriosus. KONTRAINDIKASI MUTLAK."},
        },
    },
    # ── 2. WARFARIN + ASPIRIN (CRITICAL) ────────────────────────────────────
    {
        "drugs": {"warfarin", "aspirin"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 45,
        "mechanism": "pharmacodynamic",
        "mechanism_detail": "Dual antikoagulasi + antiplatelet ireversibel → hemostasis lumpuh total → risiko perdarahan berat",
        "cyp": None,
        "alternatives": ["Evaluasi indikasi dual terapi; konsultasikan dokter spesialis jantung/hepar untuk target INR yang lebih ketat."],
        "description": "Warfarin + Aspirin: Kombinasi antikoagulan oral dan antiplatelet kuat menyebabkan penghambatan hemostasis ganda. Risiko perdarahan gastrointestinal dan hemoragik serebral sangat tinggi.",
        "patient_risk": {
            "elderly": {"score_add": 20, "note": "Lansia: Risiko perdarahan intrakranial fatal meningkat drastis. Pantau INR secara mingguan."},
            "ckd": {"score_add": 20, "note": "Gagal Ginjal (CKD): Klirens metabolit menurun, uremia memperburuk fungsi trombosit intrinsik."},
            "liver": {"score_add": 25, "note": "Gangguan Hati: Risiko perdarahan varises esofagus meningkat drastis."},
            "pregnant": {"score_add": 35, "note": "Kehamilan: Perdarahan retroplasenta dan malformasi kongenital berat. KONTRAINDIKASI MUTLAK."},
        },
    },
    # ── 3. METFORMIN + ALCOHOL (CRITICAL) ───────────────────────────────────
    {
        "drugs": {"metformin", "alcohol"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 42,
        "mechanism": "pharmacodynamic",
        "mechanism_detail": "Alkohol menghambat glukoneogenesis hepar + akumulasi laktat dari metformin → asidosis laktat fatal",
        "cyp": None,
        "alternatives": ["Hentikan konsumsi minuman beralkohol secara mutlak selama menjalani pengobatan metformin."],
        "description": "Metformin + Alkohol: Alkohol menghambat glukoneogenesis hepatik dan memperlambat pembersihan laktat, memicu asidosis laktat (kematian hingga 50%). Risiko hipoglikemia berat juga meningkat.",
        "patient_risk": {
            "elderly": {"score_add": 15, "note": "Lansia: Cadangan glikogen hati lebih rendah, gejala asidosis laktat sering terselubung."},
            "ckd": {"score_add": 25, "note": "Gagal Ginjal (CKD): Metformin terakumulasi di tubulus ginjal, risiko asidosis laktat melonjak tajam."},
            "liver": {"score_add": 30, "note": "Gangguan Hati: Gangguan klirens laktat hepatik. KONTRAINDIKASI ABSOLUT."},
            "pregnant": {"score_add": 30, "note": "Kehamilan: Alkohol memicu Fetal Alcohol Syndrome (FAS) dan asidosis maternal-fetal membahayakan janin."},
        },
    },
    # ── 4. SSRI + MAOI (CRITICAL) ───────────────────────────────────────────
    {
        "drugs": {"ssri", "maoi"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 50,
        "mechanism": "pharmacodynamic",
        "mechanism_detail": "SSRI blok reuptake 5-HT + MAOI blok degradasi 5-HT → hiperaktivasi sinaps serotonergik → Sindrom Serotonin",
        "cyp": None,
        "alternatives": ["Hentikan MAOI minimal 14 hari (atau 5 minggu untuk fluoxetine) sebelum memulai terapi SSRI."],
        "description": "SSRI + MAOI: Kombinasi mematikan yang memicu Sindrom Serotonin ganas — ditandai hipertermia maligna, klonus, instabilitas otonom, kejang, dan henti kardiorespirasi.",
        "patient_risk": {
            "elderly": {"score_add": 15, "note": "Lansia: Eliminasi hepatik melambat; washout period harus diperpanjang minimal 21 hari."},
            "ckd": {"score_add": 10, "note": "CKD: Akumulasi metabolit aktif memperlama durasi toksisitas neurologis."},
            "liver": {"score_add": 15, "note": "Gangguan Hati: Metabolisme kedua antidepresan terhambat signifikan."},
            "pregnant": {"score_add": 25, "note": "Kehamilan: Krisis hipertensi dan hipertermia mengancam viabilitas janin secara langsung."},
        },
    },
    # ── 5. SIMVASTATIN + AMIODARONE (CRITICAL) ──────────────────────────────
    {
        "drugs": {"simvastatin", "amiodarone"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 40,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "Amiodarone inhibisi kuat CYP3A4 → bioavailabilitas simvastatin naik 4-5× → miopati / rabdomiolisis",
        "cyp": "CYP3A4",
        "alternatives": ["Ganti simvastatin ke Rosuvastatin atau Pravastatin yang tidak dimetabolisme CYP3A4."],
        "description": "Simvastatin + Amiodarone: Amiodarone menghambat enzim CYP3A4 hepar, menyebabkan kadar simvastatin plasma meningkat drastis hingga menimbulkan kerusakan serat otot berat (rabdomiolisis) dan gagal ginjal akut.",
        "patient_risk": {
            "elderly": {"score_add": 20, "note": "Lansia: Penurunan massa otot rangka dan fungsi ekskresi membuat rabdomiolisis berakibat fatal."},
            "ckd": {"score_add": 25, "note": "Gagal Ginjal (CKD): Mioglobinuria akibat rabdomiolisis mempercepat nekrosis tubular ginjal akut."},
            "liver": {"score_add": 15, "note": "Gangguan Hati: Peningkatan enzim transaminase hepatik (SGOT/SGPT) lebih sering timbul."},
            "pregnant": {"score_add": 35, "note": "Kehamilan: Simvastatin KONTRAINDIKASI Kategori X (teratogenik). Amiodarone berisiko gondok/hipotiroid fetal."},
        },
    },
    # ── 6. DIGOXIN + AMIODARONE (CRITICAL) ──────────────────────────────────
    {
        "drugs": {"digoxin", "amiodarone"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 45,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "Amiodarone menghambat pompa P-glikoprotein & klirens ginjal → kadar digoxin naik 100% → aritmia maut",
        "cyp": "P-gp",
        "alternatives": ["Turunkan dosis digoxin sebesar 50% dan periksa konsentrasi serum digoxin secara rutin tiap 1–2 minggu."],
        "description": "Digoxin + Amiodarone: Amiodarone mendesak digoxin dari ikatan protein jaringan dan menghambat sekresi tubulus ginjal melalui P-gp. Kadar serum digoxin meningkat hingga 2× lipat, berisiko intoksikasi digitalis, blok AV, dan asistol.",
        "patient_risk": {
            "elderly": {"score_add": 20, "note": "Lansia: Volume distribusi digoxin mengecil; kadar terapeutik sangat dekat dengan ambang toksisitas."},
            "ckd": {"score_add": 25, "note": "Gagal Ginjal (CKD): Digoxin terutama dieliminasi melalui ginjal; retensi sangat membahayakan jantung."},
            "liver": {"score_add": 15, "note": "Gangguan Hati: Gangguan regulasi elektrolit mempercepat timbulnya aritmia mematikan."},
            "pregnant": {"score_add": 25, "note": "Kehamilan: Penetrasi plasenta dapat memicu aritmia fetal; pantau ketat detak jantung janin."},
        },
    },
    # ── 7. METHOTREXATE + IBUPROFEN (CRITICAL) ──────────────────────────────
    {
        "drugs": {"methotrexate", "ibuprofen"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 48,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "NSAID menghambat sintesis prostaglandin ginjal & sekresi tubulus → klirens methotrexate anjlok → pansitopenia fatal",
        "cyp": None,
        "alternatives": ["Gunakan Parasetamol untuk analgesia; hindari semua jenis NSAID selama terapi methotrexate dosis sedang-tinggi."],
        "description": "Methotrexate + Ibuprofen: NSAID menurunkan perfusi ginjal dan bersaing pada sekresi tubulus, meningkatkan toksisitas methotrexate secara masif. Berisiko supresi sumsum tulang berat (pansitopenia) dan nekrosis mukosa GI.",
        "patient_risk": {
            "elderly": {"score_add": 20, "note": "Lansia: Cadangan sumsum tulang berkurang, mortalitas akibat sepsis pasca-pansitopenia sangat tinggi."},
            "ckd": {"score_add": 30, "note": "Gagal Ginjal (CKD): Methotrexate tertimbun cepat. KONTRAINDIKASI MUTLAK."},
            "liver": {"score_add": 20, "note": "Gangguan Hati: Hepatotoksisitas sinergis memicu sirosis atau fibrosis hati dini."},
            "pregnant": {"score_add": 40, "note": "Kehamilan: Methotrexate adalah abortifasien poten dan teratogenik berat (Kategori X). KONTRAINDIKASI ABSOLUT."},
        },
    },
    # ── 8. SILDENAFIL + NITROGLYCERIN (CRITICAL) ────────────────────────────
    {
        "drugs": {"sildenafil", "nitroglycerin"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 50,
        "mechanism": "pharmacodynamic",
        "mechanism_detail": "PDE-5 inhibitor + donor nitrat → akumulasi cGMP masif di otot polos vaskular → vasodilatasi ekstrem & syok kardiogenik",
        "cyp": None,
        "alternatives": ["KONTRAINDIKASI MUTLAK. Jangan konsumsi nitrat dalam 24 jam setelah sildenafil."],
        "description": "Sildenafil + Nitroglycerin: Inhibisi PDE-5 bersamaan dengan donor nitrat melipatgandakan kadar siklik GMP, menyebabkan hipotensi berat refrakter, kolaps kardiovaskular, dan infark miokard fatal.",
        "patient_risk": {
            "elderly": {"score_add": 15, "note": "Lansia: Refleks baroreseptor tumpul, risiko pingsan dan trauma kepala sangat tinggi."},
            "ckd": {"score_add": 15, "note": "Gagal Ginjal: Hipotensi mendadak memicu iskemia ginjal akut."},
            "liver": {"score_add": 20, "note": "Gangguan Hati: Metabolisme sildenafil melambat, durasi vasodilatasi ekstrem bertambah panjang."},
            "pregnant": {"score_add": 25, "note": "Kehamilan: Hipotensi maternal memangkas suplai darah uteroplasenta, memicu gawat janin."},
        },
    },
    # ── 9. CIPROFLOXACIN + WARFARIN (CRITICAL) ──────────────────────────────
    {
        "drugs": {"ciprofloxacin", "warfarin"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 42,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "Ciprofloxacin inhibisi CYP1A2 & membasmi flora usus penghasil vitamin K → kadar warfarin & INR melonjak drastis",
        "cyp": "CYP1A2",
        "alternatives": ["Pilih antibiotik alternatif seperti Amoxicillin bila sensitif; turunkan dosis warfarin dan cek INR tiap 48 jam."],
        "description": "Ciprofloxacin + Warfarin: Fluorokuinolon ini menghambat metabolisme hepatik warfarin dan membasmi bakteri usus pembentuk vitamin K. Lonjakan INR sering tidak terduga dan memicu perdarahan aktif masif.",
        "patient_risk": {
            "elderly": {"score_add": 20, "note": "Lansia: Hemostasis labil, INR mudah melejit >5. Pantau ketat tanda memar/hematuria."},
            "ckd": {"score_add": 15, "note": "Gagal Ginjal: Klirens ciprofloxacin berkurang, inhibisi enzim berlangsung lebih lama."},
            "liver": {"score_add": 20, "note": "Gangguan Hati: Cadangan vitamin K hepar rendah memperparah koagulopati."},
            "pregnant": {"score_add": 35, "note": "Kehamilan: Keduanya KONTRAINDIKASI pada kehamilan karena risiko malformasi dan artropati fetal."},
        },
    },
    # ── 10. ATORVASTATIN + CLARITHROMYCIN (CRITICAL) ────────────────────────
    {
        "drugs": {"atorvastatin", "clarithromycin"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 40,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "Clarithromycin inhibitor poten CYP3A4 → AUC atorvastatin naik hingga 400% → miopati & rabdomiolisis",
        "cyp": "CYP3A4",
        "alternatives": ["Hentikan sementara statin selama konsumsi clarithromycin, atau ganti antibiotik ke Azithromycin."],
        "description": "Atorvastatin + Clarithromycin: Antibiotik makrolida clarithromycin menghambat enzim CYP3A4 secara kuat, melipatgandakan paparan atorvastatin dalam sirkulasi hingga memicu kerusakan otot berat (rabdomiolisis).",
        "patient_risk": {
            "elderly": {"score_add": 20, "note": "Lansia: Nyeri otot sering dikira keluhan rematik, keterlambatan penanganan memicu gagal ginjal."},
            "ckd": {"score_add": 25, "note": "Gagal Ginjal: Klirens mioglobin terhambat, mempercepat penurunan fungsi nefron."},
            "pregnant": {"score_add": 35, "note": "Kehamilan: Atorvastatin KONTRAINDIKASI Kategori X; mengganggu embriogenesis normal."},
        },
    },
    # ── 11. ALLOPURINOL + AZATHIOPRINE (CRITICAL) ───────────────────────────
    {
        "drugs": {"allopurinol", "azathioprine"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 45,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "Allopurinol menghambat xantin oksidase → metabolisme 6-merkaptopurin mandek → supresi sumsum tulang fatal",
        "cyp": None,
        "alternatives": ["Kurangi dosis azathioprine menjadi 25-33% dari dosis lazim dan pantau leukosit darah lengkap mingguan."],
        "description": "Allopurinol + Azathioprine: Allopurinol menghambat degradasi metabolit aktif azathioprine (6-MP). Mengakibatkan penumpukan metabolit sitotoksik dan supresi sumsum tulang fatal (leukopenia, agranulositosis).",
        "patient_risk": {
            "elderly": {"score_add": 20, "note": "Lansia: Infeksi oportunistik akibat neutropenia berkembang sangat cepat menjadi sepsis fatal."},
            "ckd": {"score_add": 25, "note": "Gagal Ginjal: Klirens metabolit allopurinol (oxypurinol) menurun, inhibisi makin permanen."},
            "pregnant": {"score_add": 30, "note": "Kehamilan: Toksisitas genetik dan sitotoksik tinggi bagi diferensiasi organ fetus."},
        },
    },
    # ── 12. LISINOPRIL + POTASSIUM (MODERATE) ───────────────────────────────
    {
        "drugs": {"lisinopril", "potassium"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 22,
        "mechanism": "pharmacodynamic",
        "mechanism_detail": "ACE inhibitor menurunkan aldosteron → retensi kalium di tubulus distal + suplemen kalium → hiperkalemia",
        "cyp": None,
        "alternatives": ["Hentikan suplemen kalium kecuali terdokumentasi hipokalemia; pantau elektrolit serum secara berkala."],
        "description": "Lisinopril + Kalium: ACE inhibitor mengurangi sekresi aldosteron sehingga ginjal menahan kalium. Penambahan suplemen kalium dapat memicu hiperkalemia aritmogenik yang berbahaya bagi konduksi jantung.",
        "patient_risk": {
            "elderly": {"score_add": 15, "note": "Lansia: Ekskresi kalium menurun seiring penuaan fisiologis ginjal."},
            "ckd": {"score_add": 25, "note": "Gagal Ginjal (CKD): Kombinasi ini menjadi KRITIS. Risiko aritmia ventrikel meningkat tajam."},
            "pregnant": {"score_add": 35, "note": "Kehamilan: ACE inhibitor KONTRAINDIKASI Kategori D/X (menyebabkan oligohidramnion, hipoplasia paru fetal)."},
        },
    },
    # ── 13. METFORMIN + IBUPROFEN (MODERATE) ────────────────────────────────
    {
        "drugs": {"metformin", "ibuprofen"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 24,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "NSAID menurunkan sintesis prostaglandin ginjal → vasokonstriksi aferen & GFR turun → metformin tertimbun",
        "cyp": None,
        "alternatives": ["Pilih analgesik Parasetamol; hindari pemakaian NSAID rutin pada pasien diabetes melitus tipe 2."],
        "description": "Metformin + Ibuprofen: NSAID menurunkan perfusi ginjal dan laju filtrasi glomerulus, menghambat eliminasi metformin dan meningkatkan risiko asidosis laktat serta cedera ginjal akut.",
        "patient_risk": {
            "elderly": {"score_add": 18, "note": "Lansia: Kombinasi ini menjadi KRITIS karena laju GFR basal lansia sudah di bawah rata-rata."},
            "ckd": {"score_add": 28, "note": "Gagal Ginjal (CKD): Risiko nekrosis tubular dan asidosis laktat berat. KONTRAINDIKASI."},
            "pregnant": {"score_add": 25, "note": "Kehamilan: NSAID trimester 3 memicu penutupan dini duktus arteriosus janin."},
        },
    },
    # ── 14. CIPROFLOXACIN + ANTACID (MODERATE - TIMING SENSITIVE) ───────────
    {
        "drugs": {"ciprofloxacin", "antacid"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 20,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "Kation multivalent (Al³⁺, Mg²⁺) membentuk khelat tidak larut dengan ciprofloxacin → bioavailabilitas anjlok 85-90%",
        "cyp": None,
        "alternatives": ["Beri jarak waktu minum: Ciprofloxacin 2 jam SEBELUM atau 6 jam SESUDAH antasida."],
        "description": "Ciprofloxacin + Antasida: Ion aluminium dan magnesium dalam antasida mengikat ciprofloxacin di saluran pencernaan menjadi senyawa khelat yang tidak dapat diserap, menyebabkan kegagalan terapi antibiotik.",
        "patient_risk": {
            "pregnant": {"score_add": 20, "note": "Kehamilan: Quinolone berisiko merusak kartilago pertumbuhan sendi janin."},
        },
        "timing_sensitive": True,
        "timing_gap_hours": 2,
    },
    # ── 15. AMLODIPINE + SIMVASTATIN (MODERATE) ─────────────────────────────
    {
        "drugs": {"amlodipine", "simvastatin"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 20,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "Amlodipine inhibisi parsial CYP3A4 → kadar simvastatin naik hingga 77% → risiko miopati meningkat",
        "cyp": "CYP3A4",
        "alternatives": ["Batasi dosis maksimal simvastatin 20 mg/hari bila digunakan bersama amlodipine, atau beralih ke Rosuvastatin."],
        "description": "Amlodipine + Simvastatin: Amlodipine menghambat pemecahan simvastatin oleh CYP3A4 di hati, meningkatkan konsentrasi statin dalam darah dan melipatgandakan risiko nyeri otot dan miopati.",
        "patient_risk": {
            "elderly": {"score_add": 15, "note": "Lansia: Gejala miopati sering terabaikan hingga menjadi kelemahan motorik berat."},
            "pregnant": {"score_add": 30, "note": "Kehamilan: Simvastatin KONTRAINDIKASI MUTLAK pada kehamilan."},
        },
    },
    # ── 16. FLUOXETINE + TRAMADOL (MODERATE) ────────────────────────────────
    {
        "drugs": {"fluoxetine", "tramadol"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 25,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "Fluoxetine blok CYP2D6 (aktivasi tramadol terganggu) + inhibisi reuptake serotonin ganda → sindrom serotonin & kejang",
        "cyp": "CYP2D6",
        "alternatives": ["Pertimbangkan analgesik non-opioid seperti Parasetamol; bila perlu opioid, pantau ketat tanda agitasi dan tremor."],
        "description": "Fluoxetine + Tramadol: Fluoxetine menghambat aktivasi metabolik tramadol sekaligus meningkatkan transmisi serotonin sentral, meningkatkan risiko sindrom serotonin sedang dan menurunkan ambang kejang.",
        "patient_risk": {
            "elderly": {"score_add": 15, "note": "Lansia: Risiko sedasi berat, disorientasi kognitif, dan cedera akibat jatuh."},
            "pregnant": {"score_add": 25, "note": "Kehamilan: Tramadol menembus plasenta, berisiko neonatal opioid withdrawal syndrome (NOWS)."},
        },
    },
    # ── 17. SPIRONOLACTONE + POTASSIUM (MODERATE) ───────────────────────────
    {
        "drugs": {"spironolactone", "potassium"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 22,
        "mechanism": "pharmacodynamic",
        "mechanism_detail": "Diuretik hemat kalium antagonis reseptor aldosteron + asupan kalium eksternal → akumulasi kalium berbahaya",
        "cyp": None,
        "alternatives": ["Hentikan suplemen kalium; pantau kadar elektrolit kalium serum secara berkala."],
        "description": "Spironolactone + Kalium: Spironolactone secara langsung menghambat ekskresi ion kalium di tubulus renalis distal. Pemberian kalium tambahan sangat mudah memicu hiperkalemia simtomatik.",
        "patient_risk": {
            "elderly": {"score_add": 15, "note": "Lansia: Penurunan laju filtrasi mempercepat lonjakan konsentrasi kalium plasma."},
            "ckd": {"score_add": 25, "note": "Gagal Ginjal (CKD): Kombinasi menjadi KRITIS. Kontraindikasi kuat pada eGFR < 30 mL/min."},
            "pregnant": {"score_add": 30, "note": "Kehamilan: Spironolactone memiliki efek antiandrogenik (berisiko feminisasi janin laki-laki)."},
        },
    },
    # ── 18. CLOPIDOGREL + OMEPRAZOLE (MODERATE) ─────────────────────────────
    {
        "drugs": {"clopidogrel", "omeprazole"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 26,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "Omeprazole inhibisi kuat CYP2C19 → bioaktivasi prodrug clopidogrel terhambat → efek antiplatelet turun 40-50%",
        "cyp": "CYP2C19",
        "alternatives": ["Ganti omeprazole dengan Pantoprazole yang memiliki inhibisi minimal terhadap CYP2C19."],
        "description": "Clopidogrel + Omeprazole: Omeprazole menghambat enzim CYP2C19 yang krusial untuk mengubah clopidogrel menjadi bentuk aktifnya, menurunkan proteksi antiplatelet dan meningkatkan risiko trombosis stent / serangan jantung.",
        "patient_risk": {
            "elderly": {"score_add": 15, "note": "Lansia: Kejadian kardiovaskular sekunder lebih sering terjadi bila antiplatelet gagal bekerja."},
            "pregnant": {"score_add": 15, "note": "Kehamilan: Evaluasi hemostasis sebelum persalinan."},
        },
    },
    # ── 19. DIGOXIN + FUROSEMIDE (MODERATE) ─────────────────────────────────
    {
        "drugs": {"digoxin", "furosemide"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 24,
        "mechanism": "pharmacodynamic",
        "mechanism_detail": "Loop diuretik membuang K⁺ & Mg²⁺ → hipokalemia meningkatkan afinitas digoxin pada Na⁺/K⁺-ATPase miokard → aritmia",
        "cyp": None,
        "alternatives": ["Monitor kadar kalium serum dan tambahkan suplemen kalium / spironolactone jika kalium < 4.0 mEq/L."],
        "description": "Digoxin + Furosemide: Diuretik kuat furosemide menyebabkan ekskresi kalium berlebih (hipokalemia). Kadar kalium darah yang rendah melipatgandakan sensitivitas jantung terhadap toksisitas digoxin.",
        "patient_risk": {
            "elderly": {"score_add": 20, "note": "Lansia: Sensitivitas miokard meningkat, aritmia fatal dapat terjadi meski kadar digoxin normal."},
            "ckd": {"score_add": 20, "note": "CKD: Regulasi elektrolit sangat tidak stabil."},
            "pregnant": {"score_add": 15, "note": "Kehamilan: Hipoperfusi plasenta dan imbalans elektrolit membebani janin."},
        },
    },
    # ── 20. PARACETAMOL + ALCOHOL (MODERATE/CRITICAL) ───────────────────────
    {
        "drugs": {"paracetamol", "alcohol"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 28,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "Alkohol induksi CYP2E1 → bioaktivasi parasetamol menjadi metabolit toksik NAPQI meningkat → gagal hati akut",
        "cyp": "CYP2E1",
        "alternatives": ["Hindari alkohol; batasi dosis parasetamol maksimal 2000 mg/hari pada riwayat konsumsi alkohol."],
        "description": "Parasetamol + Alkohol: Konsumsi alkohol kronis menginduksi enzim CYP2E1 dan menguras cadangan glutation hati. Akibatnya, parasetamol cepat terurai menjadi metabolit reaktif NAPQI yang memicu nekrosis sel hati sentrilobular.",
        "patient_risk": {
            "liver": {"score_add": 30, "note": "Gangguan Hati: Risiko gagal hati fulminan sangat tinggi. Kombinasi menjadi KRITIS."},
            "elderly": {"score_add": 15, "note": "Lansia: Glutation hepar menurun alami, risiko nekrosis hepar lebih cepat terjadi."},
            "pregnant": {"score_add": 25, "note": "Kehamilan: Sindrom alkohol janin (FAS) + beban hepatotoksik ganda."},
        },
    },
    # ── 21. LEVOTHYROXINE + ANTACID (MODERATE - TIMING SENSITIVE) ───────────
    {
        "drugs": {"levothyroxine", "antacid"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 20,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "Kation kalsium/aluminium/magnesium dalam antasida mengadsorpsi T4 → penyerapan hormon tiroid anjlok",
        "cyp": None,
        "alternatives": ["Beri jeda minimal 4 jam antara minum levothyroxine dan antasida / suplemen mineral."],
        "description": "Levothyroxine + Antasida: Antasida mengikat hormon tiroid sintetik di saluran cerna dan menurunkan penyerapannya, memicu kegagalan kontrol hipotiroidisme.",
        "patient_risk": {
            "pregnant": {"score_add": 25, "note": "Kehamilan: Hipotiroidisme maternal yang tidak terkontrol mengganggu perkembangan otak dan IQ janin."},
        },
        "timing_sensitive": True,
        "timing_gap_hours": 4,
    },
    # ── 22. CIPROFLOXACIN + IBUPROFEN (MODERATE) ────────────────────────────
    {
        "drugs": {"ciprofloxacin", "ibuprofen"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 25,
        "mechanism": "pharmacodynamic",
        "mechanism_detail": "Fluorokuinolon + NSAID bersaing menghambat reseptor GABA di SSP → stimulasi SSP berlebih → risiko kejang",
        "cyp": None,
        "alternatives": ["Ganti ibuprofen ke Parasetamol selama terapi ciprofloxacin, terutama bila ada riwayat epilepsi."],
        "description": "Ciprofloxacin + Ibuprofen: Kombinasi antibiotik fluorokuinolon dengan NSAID meningkatkan efek inhibisi terhadap reseptor GABA otak, berpotensi memicu stimulasi sistem saraf pusat berlebih hingga kejang tonik-klonik.",
        "patient_risk": {
            "elderly": {"score_add": 15, "note": "Lansia: Ambang kejang lebih rendah dan permeabilitas sawar darah otak lebih tinggi."},
            "pregnant": {"score_add": 25, "note": "Kehamilan: Quinolone dan NSAID keduanya dihindari pada masa gestasi."},
        },
    },
    # ── 23. LITHIUM + IBUPROFEN (CRITICAL) ──────────────────────────────────
    {
        "drugs": {"lithium", "ibuprofen"},
        "status": "critical",
        "level": "Kritis",
        "color": "red",
        "score": 42,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "NSAID menghambat sintesis prostaglandin renal → filtrasi lithium anjlok → kadar plasma melonjak 40-60%",
        "cyp": None,
        "alternatives": ["Ganti dengan Parasetamol; hindari semua jenis NSAID bila pasien dalam terapi pemeliharaan lithium."],
        "description": "Lithium + Ibuprofen: NSAID mengurangi laju filtrasi ginjal terhadap ion lithium. Kadar serum lithium meningkat cepat menuju level toksik: tremor kasar, ataxia, konfusi, dan koma.",
        "patient_risk": {
            "elderly": {"score_add": 20, "note": "Lansia: Sangat rentan terhadap toksisitas neuro-renal lithium."},
            "ckd": {"score_add": 25, "note": "Gagal Ginjal: Klirens ginjal sudah rendah, intoksikasi terjadi sangat cepat."},
            "pregnant": {"score_add": 35, "note": "Kehamilan: Lithium teratogenik (Ebstein anomaly pada katup jantung fetus)."},
        },
    },
    # ── 24. OMEPRAZOLE + DIAZEPAM (MODERATE) ────────────────────────────────
    {
        "drugs": {"omeprazole", "diazepam"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 18,
        "mechanism": "pharmacokinetic",
        "mechanism_detail": "Omeprazole menghambat CYP2C19 → eliminasi diazepam tertunda → perpanjangan waktu paruh & sedasi berlebih",
        "cyp": "CYP2C19",
        "alternatives": ["Gunakan benzodiazepine yang tidak dimetabolisme CYP seperti Lorazepam, atau ganti omeprazole ke Pantoprazole."],
        "description": "Omeprazole + Diazepam: Omeprazole menghambat metabolisme hepatik diazepam melalui CYP2C19, memperpanjang durasi kerja obat dan memperdalam efek kantuk, ataksia, serta depresi pernapasan.",
        "patient_risk": {
            "elderly": {"score_add": 20, "note": "Lansia: Sedasi berkepanjangan meningkatkan risiko delirium dan jatuh patah tulang panggul."},
        },
    },
    # ── 25. LISINOPRIL + SPIRONOLACTONE (MODERATE/CRITICAL) ─────────────────
    {
        "drugs": {"lisinopril", "spironolactone"},
        "status": "moderate",
        "level": "Sedang",
        "color": "yellow",
        "score": 25,
        "mechanism": "pharmacodynamic",
        "mechanism_detail": "Dual blokade sistem Renin-Angiotensin-Aldosteron → inhibisi sekresi kalium ganda → hiperkalemia berat",
        "cyp": None,
        "alternatives": ["Bila diindikasikan untuk gagal jantung (HFrEF), gunakan dosis rendah spironolactone (12.5–25 mg) dan pantau kalium rutin."],
        "description": "Lisinopril + Spironolactone: Kombinasi penghambat ACE dan antagonis aldosteron memblokir sekresi kalium secara ganda, berisiko tinggi hiperkalemia berat terutama bila pasien mengalami dehidrasi atau penurunan fungsi ginjal.",
        "patient_risk": {
            "elderly": {"score_add": 18, "note": "Lansia: Kombinasi ini menjadi KRITIS. Monitor elektrolit tiap 1-2 minggu di awal terapi."},
            "ckd": {"score_add": 28, "note": "Gagal Ginjal: Risiko henti jantung akibat hiperkalemia melonjak tajam."},
            "pregnant": {"score_add": 35, "note": "Kehamilan: Keduanya KONTRAINDIKASI MUTLAK pada kehamilan."},
        },
    },
]

# ---------------------------------------------------------------------------
# Dictionary Drug Details for Kamus & Scanner (DRUG_INFO)
# ---------------------------------------------------------------------------

DRUG_INFO: dict[str, dict] = {
    "warfarin": {
        "name": "Warfarin",
        "category": "Antikoagulan Oral",
        "description": "Obat antikoagulan (pengencer darah) antagonis vitamin K untuk mencegah trombosis vena dalam, emboli paru, fibrilasi atrium, dan stroke.",
        "common_brands": ["Coumadin", "Jantoven", "Simarc"],
        "side_effects": "Perdarahan gusi, memar spontan, hematuria, melena, nekrosis kulit (jarang).",
        "notes": "Membutuhkan pemantauan INR rutin (target 2.0–3.0). Sangat rentan interaksi dengan makanan tinggi vitamin K dan NSAID.",
    },
    "ibuprofen": {
        "name": "Ibuprofen",
        "category": "NSAID (Anti-Inflamasi Non-Steroid)",
        "description": "Analgesik, antipiretik, dan anti-inflamasi penghambat enzim COX-1 dan COX-2 untuk meredakan nyeri ringan hingga sedang dan demam.",
        "common_brands": ["Advil", "Proris", "Motrin", "Farsifen", "Bufect"],
        "side_effects": "Dispepsia, nyeri ulu hati, tukak lambung, perdarahan GI, retensi cairan, penurunan fungsi ginjal.",
        "notes": "Hindari pada riwayat tukak peptik, gagal ginjal, lansia, dan kehamilan trimester ketiga.",
    },
    "aspirin": {
        "name": "Aspirin (Asam Asetilsalisilat)",
        "category": "Antiplatelet / Analgesik",
        "description": "Inhibitor ireversibel COX-1 trombosit untuk prevensi sekunder infark miokard, stroke iskemik, dan sindrom koroner akut.",
        "common_brands": ["Aspilets", "Thrombo Aspilets", "Bayer Aspirin", "Cardioaspirin"],
        "side_effects": "Iritasi mukosa lambung, erosi gaster, tinitus (pada dosis tinggi), perpanjangan waktu perdarahan.",
        "notes": "Dosis kardioprotektif lazim 80–100 mg per hari. Berbahaya bila dikombinasi tanpa indikasi dengan antikoagulan lain.",
    },
    "metformin": {
        "name": "Metformin",
        "category": "Antidiabetik Oral (Biguanide)",
        "description": "Terapi lini pertama diabetes melitus tipe 2 yang menurunkan glukoneogenesis hepatik dan memperbaiki sensitivitas insulin perifer.",
        "common_brands": ["Glucophage", "Diabex", "Glumin", "Forbetes"],
        "side_effects": "Gangguan pencernaan, mual, diare, rasa logam di mulut, defisiensi vitamin B12 jangka panjang, asidosis laktat (jarang namun fatal).",
        "notes": "Diminum bersamaan atau sesudah makan. Hentikan sebelum prosedur dengan kontras iodinasi radiologi.",
    },
    "amiodarone": {
        "name": "Amiodarone",
        "category": "Antiaritmia Kelas III",
        "description": "Antiaritmia spektrum luas pemanjang potensial aksi untuk aritmia ventrikel refrakter dan fibrilasi atrium simtomatik.",
        "common_brands": ["Cordarone", "Pacerone", "Tiaryt"],
        "side_effects": "Fibrosis paru, disfungsi tiroid (hipo/hipertiroid), peningkatan enzim hepar, mikrodeposit kornea, fotosensitivitas.",
        "notes": "Waktu paruh eliminasi sangat panjang (40–55 hari). Merupakan inhibitor kuat CYP3A4, CYP2C9, dan P-glikoprotein.",
    },
    "simvastatin": {
        "name": "Simvastatin",
        "category": "Statin (HMG-CoA Reductase Inhibitor)",
        "description": "Obat penurun kolesterol LDL dan trigliserida serta penstabil plak aterosklerosis pada penyakit kardiovaskular.",
        "common_brands": ["Zocor", "Lipcut", "Cholestor", "Valesco"],
        "side_effects": "Mialgia, kram otot, peningkatan transaminase hepar, rabdomiolisis (jarang).",
        "notes": "Diminum pada malam hari. Dimetabolisme kuat oleh CYP3A4 sehingga sensitif terhadap interaksi obat dan jus grapefruit.",
    },
    "atorvastatin": {
        "name": "Atorvastatin",
        "category": "Statin (Penurun Kolesterol Intensitas Tinggi)",
        "description": "Statin potensi tinggi untuk dislipidemia dan reduksi risiko infark miokard dan stroke pada pasien berisiko tinggi.",
        "common_brands": ["Lipitor", "Stator", "Truvaz"],
        "side_effects": "Nyeri otot, sakit kepala, gangguan cerna, peningkatan enzim hati.",
        "notes": "Dapat diminum kapan saja (pagi atau malam). Inhibitor kuat CYP3A4 seperti clarithromycin meningkatkan kadar atorvastatin secara masif.",
    },
    "digoxin": {
        "name": "Digoxin",
        "category": "Glikosida Jantung (Inotropik Positif)",
        "description": "Meningkatkan kontraktilitas miokard dan memperlambat konduksi nodus AV pada gagal jantung kronik dan fibrilasi atrium.",
        "common_brands": ["Lanoxin", "Fargoxin"],
        "side_effects": "Anoreksia, mual, muntah, gangguan visual persepsi warna kuning/hijau (xanthopsia), aritmia ventrikel.",
        "notes": "Indeks terapeutik sangat sempit (0.5–0.9 ng/mL). Klirens terutama melalui ginjal; pantau ketat bila ada hipokalemia.",
    },
    "lisinopril": {
        "name": "Lisinopril",
        "category": "ACE Inhibitor (Antihipertensi)",
        "description": "Menghambat sintesis Angiotensin II untuk menurunkan tekanan darah dan mengurangi beban jantung pada gagal jantung kongestif.",
        "common_brands": ["Zestril", "Prinivil", "Tensipril"],
        "side_effects": "Batuk kering persisten (karena bradikinin), hiperkalemia, hipotensi ortostatik, angioedema (jarang).",
        "notes": "Kontraindikasi mutlak pada kehamilan. Pantau fungsi ginjal (kreatinin) dan elektrolit kalium setelah inisiasi.",
    },
    "potassium": {
        "name": "Kalium (Potassium)",
        "category": "Suplemen Elektrolit Kation",
        "description": "Elektrolit esensial untuk transmisi impuls saraf, kontraksi otot rangka, dan stabilitas elektrofisiologi membran jantung.",
        "common_brands": ["KSR", "Aspar-K", "Kalium Klorida (KCl)"],
        "side_effects": "Iritasi lambung, mual, diare, hiperkalemia bila ekskresi renal terganggu.",
        "notes": "Jangan digerus pada sediaan lepas lambat. Hindari penggunaan bersamaan dengan ACEI, ARB, atau diuretik hemat kalium.",
    },
    "ciprofloxacin": {
        "name": "Ciprofloxacin",
        "category": "Antibiotik Fluorokuinolon",
        "description": "Antibiotik bakterisidal penghambat DNA girase untuk infeksi saluran kemih rumit, infeksi intraabdomen, dan pernapasan.",
        "common_brands": ["Ciproxin", "Baquinor", "Ciflos"],
        "side_effects": "Mual, diare, sakit kepala, tendinitis dan ruptur tendon achilles (jarang), perpanjangan interval QT.",
        "notes": "Hindari bersama antasida atau susu/kalsium. Beri jarak minimal 2 jam. Hindari pada anak-anak dan kehamilan.",
    },
    "antacid": {
        "name": "Antasida",
        "category": "Penetral Asam Lambung",
        "description": "Kombinasi Aluminium Hidroksida dan Magnesium Hidroksida untuk meredakan gejala gastritis, dispepsia, dan tukak lambung.",
        "common_brands": ["Promag", "Mylanta", "Polysilane", "Antasida DOEN"],
        "side_effects": "Konstipasi (Al), diare (Mg), gangguan absorpsi mineral dan obat lain.",
        "notes": "Kation logam mengikat banyak antibiotik (fluorokuinolon, tetrasiklin) dan levothyroxine. Selalu beri jeda minimal 2 jam.",
    },
    "amlodipine": {
        "name": "Amlodipine",
        "category": "Calcium Channel Blocker (Dihidropiridin)",
        "description": "Vasodilator arteri perifer untuk terapi hipertensi dan profilaksis angina pektoris stabil.",
        "common_brands": ["Norvasc", "Tensivask", "Divask", "Amcor"],
        "side_effects": "Edema pergelangan kaki perifer, pusing, flushing wajah, palpitasi.",
        "notes": "Bekerja secara independen dari asupan garam. Memiliki efek inhibisi ringan pada CYP3A4.",
    },
    "fluoxetine": {
        "name": "Fluoxetine",
        "category": "Antidepresan SSRI",
        "description": "Inhibitor selektif reuptake serotonin untuk depresi mayor, gangguan obsesif-kompulsif (OCD), dan bulimia.",
        "common_brands": ["Prozac", "Nopres", "Kalxetin"],
        "side_effects": "Insomnia, mual, tremor, agitasi, penurunan libido, sindrom serotonin bila dikombinasi.",
        "notes": "Memiliki metabolit aktif norfluoxetine dengan waktu paruh sangat panjang (hingga 1–2 minggu). Membutuhkan washout period 5 minggu sebelum MAOI.",
    },
    "tramadol": {
        "name": "Tramadol",
        "category": "Analgesik Opioid Sentral",
        "description": "Agonis reseptor mu-opioid dan inhibitor reuptake serotonin/norepinefrin untuk nyeri akut sedang hingga berat.",
        "common_brands": ["Tramal", "Ultram", "Tradyl"],
        "side_effects": "Mual, pusing, konstipasi, sedasi, risiko ketergantungan dan penurunan ambang kejang.",
        "notes": "Kombinasi dengan antidepresan serotonergik sangat berisiko memicu sindrom serotonin dan kejang.",
    },
    "spironolactone": {
        "name": "Spironolactone",
        "category": "Diuretik Hemat Kalium (Antagonis Aldosteron)",
        "description": "Diuretik hemat kalium untuk gagal jantung kronis (HFrEF), hipertensi resisten, asites sirosis hati, dan hiperaldosteronisme.",
        "common_brands": ["Aldactone", "Letonal", "Spirola"],
        "side_effects": "Hiperkalemia, ginekomastia pada pria, gangguan siklus menstruasi pada wanita, dehidrasi.",
        "notes": "Wajib memantau kadar kalium dan kreatinin serum secara berkala.",
    },
    "clopidogrel": {
        "name": "Clopidogrel",
        "category": "Antiplatelet Thienopyridine (P2Y12 Inhibitor)",
        "description": "Prodrug antiplatelet pencegah trombosis vaskular pada sindrom koroner akut, pasca-stent jantung, dan stroke iskemik.",
        "common_brands": ["Plavix", "Clopisan", "Placta"],
        "side_effects": "Perdarahan, memar, purpura, dispepsia.",
        "notes": "Membutuhkan aktivasi bio-metabolik oleh enzim CYP2C19. Dihambat oleh omeprazole.",
    },
    "omeprazole": {
        "name": "Omeprazole",
        "category": "Proton Pump Inhibitor (PPI)",
        "description": "Menekan sekresi asam lambung melalui inhibisi pompa H+/K+-ATPase pada GERD, tukak duodenum, dan perlindungan lambung.",
        "common_brands": ["Losec", "Prilosec", "Ozid", "OMZ"],
        "side_effects": "Sakit kepala, diare, mual, polip kelenjar fundus lambung, hipomagnesemia jangka panjang.",
        "notes": "Inhibitor moderat CYP2C19. Diminum 30–60 menit sebelum makan pagi.",
    },
    "methotrexate": {
        "name": "Methotrexate",
        "category": "Antimetabolit Imunosupresan / Sitostatika",
        "description": "Antagonis asam folat untuk rheumatoid arthritis, psoriasis berat, dan keganasan hematologi.",
        "common_brands": ["Rheumatrex", "Trexall"],
        "side_effects": "Stomatitis, pansitopenia, mual, hepatotoksisitas, pneumonitis interstitial.",
        "notes": "Dosis mingguan untuk penyakit autoimun. Berikan asam folat pada hari non-dosis. Hindari kombinasi dengan NSAID.",
    },
    "sildenafil": {
        "name": "Sildenafil",
        "category": "PDE-5 Inhibitor",
        "description": "Vasodilator pemanjang kerja cGMP untuk disfungsi ereksi dan hipertensi arteri pulmonal (PAH).",
        "common_brands": ["Viagra", "Ericfil", "Revatio"],
        "side_effects": "Sakit kepala, kemerahan wajah (flushing), hidung tersumbat, dispepsia, penglihatan kebiruan.",
        "notes": "KONTRAINDIKASI MUTLAK dengan segala bentuk nitrat organik.",
    },
    "nitroglycerin": {
        "name": "Nitroglycerin / Nitrat",
        "category": "Vasodilator Nitrat Organik",
        "description": "Donor nitrat untuk terminasi cepat dan pencegahan serangan angina pektoris.",
        "common_brands": ["Nitrokaf", "Nitrocine", "ISDN (Cedocard)"],
        "side_effects": "Hipotensi mendadak, sakit kepala berdenyut, takikardia refleks, pusing ortostatik.",
        "notes": "Jangan dikombinasi dengan PDE-5 inhibitor (sildenafil, tadalafil).",
    },
    "paracetamol": {
        "name": "Paracetamol (Asetaminofen)",
        "category": "Analgesik & Antipiretik Lini Pertama",
        "description": "Pereda nyeri dan penurun demam yang aman untuk sebagian besar populasi bila digunakan dalam batas dosis harian normal.",
        "common_brands": ["Panadol", "Tempra", "Sanmol", "Biogesic", "Pamol"],
        "side_effects": "Hepatotoksisitas bila melebihi 4000 mg/hari atau dikonsumsi bersama alkohol.",
        "notes": "Dosis maksimal dewasa 4g/hari. Pilihan analgesik teraman untuk pasien dengan riwayat perdarahan lambung atau gagal ginjal.",
    },
    "amoxicillin": {
        "name": "Amoxicillin",
        "category": "Antibiotik Penisilin Spektrum Luas",
        "description": "Antibiotik bakterisidal untuk infeksi saluran napas atas, infeksi gigi, telinga, dan infeksi saluran kemih.",
        "common_brands": ["Amoxil", "Yusimox", "Trimox", "Hiconcil"],
        "side_effects": "Ruam kulit, diare, mual, reaksi anafilaksis pada pasien alergi penisilin.",
        "notes": "Pastikan riwayat alergi penisilin negatif sebelum diresepkan. Habiskan sesuai durasi terapi.",
    },
    "levothyroxine": {
        "name": "Levothyroxine",
        "category": "Hormon Tiroid Sintetik (T4)",
        "description": "Terapi sulih hormon untuk pasien hipotiroidisme dan pasca-tiroidektomi.",
        "common_brands": ["Euthyrox", "Thyrax"],
        "side_effects": "Palpitasi, tremor, insomnia, penurunan berat badan bila dosis berlebih.",
        "notes": "Diminum saat perut kosong di pagi hari, minimal 30–60 menit sebelum sarapan. Beri jarak 4 jam dari antasida atau suplemen besi/kalsium.",
    },
    "alcohol": {
        "name": "Alkohol (Etanol)",
        "category": "Zat Psikoaktif / Pelarut",
        "description": "Etanol dalam minuman beralkohol yang mempengaruhi sistem saraf pusat dan metabolisme hepatik.",
        "common_brands": ["-"],
        "side_effects": "Depresi sistem saraf pusat, hepatotoksisitas, gangguan koordinasi motorik.",
        "notes": "Banyak berinteraksi buruk dengan obat-obatan medis, terutama penekan SSP, antidiabetes, dan antikoagulan.",
    },
    "ssri": {
        "name": "Golongan SSRI",
        "category": "Antidepresan Serotonergik",
        "description": "Kelas antidepresan selektif serotonin mencakup fluoxetine, sertraline, escitalopram, paroxetine, dan fluvoxamine.",
        "common_brands": ["Prozac", "Zoloft", "Lexapro", "Paxil"],
        "side_effects": "Mual, disfungsi seksual, agitasi, risiko sindrom serotonin.",
        "notes": "Jangan digunakan bersamaan dengan MAOI atau tramadol dosis tinggi.",
    },
    "maoi": {
        "name": "Golongan MAOI",
        "category": "Antidepresan Inhibitor Monoamin Oksidase",
        "description": "Antidepresan penghambat enzim MAO mencakup phenelzine, tranylcypromine, isocarboxazid, selegiline, dan moclobemide.",
        "common_brands": ["Nardil", "Parnate", "Marplan", "Jumex"],
        "side_effects": "Krisis hipertensi (dengan makanan ber-tiramin), hipotensi ortostatik, insomnia berat.",
        "notes": "Kombinasi dengan obat serotonergik lain adalah KONTRAINDIKASI MUTLAK.",
    },
}

# ---------------------------------------------------------------------------
# Intelligent Drug Tag Resolver
# ---------------------------------------------------------------------------

def clean_drug_name(raw: str) -> str:
    """Normalize drug text: lower, strip dose, keep clean string."""
    d = raw.strip().lower()
    # Strip dose patterns: e.g. 500mg, 5 mg, 10mcg, 1x1, no. x, tab, tablet, kapsul
    d = re.sub(r'\b\d+(\.\d+)?\s*(mg|mcg|ml|g|iu|tab|tablet|kapsul|cap)?\b', '', d).strip()
    d = re.sub(r'\b(no\.?\s*\w+|s\s*\d+\s*dd\s*\d+)\b', '', d).strip()
    d = re.sub(r'[^a-z0-9\s-]', '', d).strip()
    return d

def get_drug_tags(raw: str) -> tuple[str, set[str]]:
    """
    Returns (normalized_clean_name, set_of_tags).
    Tags include: generic name, brand aliases, synonyms, and drug classes.
    """
    cleaned = clean_drug_name(raw)
    tags = {cleaned}

    # Check direct synonyms
    if cleaned in SYNONYMS:
        tags.add(SYNONYMS[cleaned])

    # Check brands
    if cleaned in BRAND_TO_GENERIC:
        generic = BRAND_TO_GENERIC[cleaned]
        tags.add(generic)
        if generic in DRUG_CLASSES:
            tags.update(DRUG_CLASSES[generic])
    else:
        # Check if brand is a substring or word in cleaned
        for brand, generic in BRAND_TO_GENERIC.items():
            if brand == cleaned or brand in cleaned.split():
                tags.add(generic)
                tags.add(brand)
                if generic in DRUG_CLASSES:
                    tags.update(DRUG_CLASSES[generic])

    # Check generic classes
    for tag in list(tags):
        if tag in DRUG_CLASSES:
            tags.update(DRUG_CLASSES[tag])
        if tag in SYNONYMS:
            std = SYNONYMS[tag]
            tags.add(std)
            if std in DRUG_CLASSES:
                tags.update(DRUG_CLASSES[std])

    return cleaned, tags

# ---------------------------------------------------------------------------
# Check Drugs Endpoint
# ---------------------------------------------------------------------------

@app.post("/api/check-drugs", response_model=InteractionResult)
@app.post("/api/check", response_model=InteractionResult)
def check_drugs(payload: DrugCheckRequest, session: Optional[str] = Cookie(default=None)):
    patient = payload.patient or PatientProfile()
    timings = payload.timings or []

    # Parse and resolve each input drug
    input_records = []
    for d_raw in payload.drugs:
        d_clean, d_tags = get_drug_tags(d_raw)
        if d_clean:
            input_records.append({
                "raw": d_raw.strip(),
                "clean": d_clean,
                "tags": d_tags,
            })

    if len(input_records) < 2:
        return InteractionResult(
            status="safe",
            level="Aman",
            color="green",
            interactions=[],
            summary="Masukkan minimal 2 nama obat untuk memeriksa potensi interaksi.",
            risk_score=0,
            timing_warnings=None,
            patient_adjustments=None,
        )

    found_interactions = []
    highest_status = "safe"
    total_score = 0
    patient_adjustments = []

    # Check each clinical rule against pairs of distinct medications
    for rule in RULES:
        req_drugs = list(rule["drugs"])
        if len(req_drugs) != 2:
            continue
        req1, req2 = req_drugs[0], req_drugs[1]

        # Find if two distinct input drugs satisfy req1 and req2
        matched_inputs = None
        for i in range(len(input_records)):
            for j in range(i + 1, len(input_records)):
                rec_a, rec_b = input_records[i], input_records[j]
                if (req1 in rec_a["tags"] and req2 in rec_b["tags"]) or (req2 in rec_a["tags"] and req1 in rec_b["tags"]):
                    matched_inputs = (rec_a, rec_b)
                    break
            if matched_inputs:
                break

        if not matched_inputs:
            continue

        base_score = rule.get("score", 0)
        adj_score = base_score
        adj_notes = []

        # Patient Profile Risk Adjustments (Elderly, CKD, Liver, Pregnant)
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

        effective_status = rule["status"]
        if adj_score >= 50:
            effective_status = "critical"
        elif adj_score >= 25 and effective_status == "safe":
            effective_status = "moderate"

        # Display names: reflect user inputs if they used brand names
        d1_display = matched_inputs[0]["raw"]
        d2_display = matched_inputs[1]["raw"]

        if adj_notes:
            patient_adjustments.append({
                "drugs": [d1_display, d2_display],
                "original_level": rule["level"],
                "adjusted_score": min(adj_score, 100),
                "notes": adj_notes,
            })

        found_interactions.append({
            "drugs": [d1_display, d2_display],
            "generic_drugs": list(rule["drugs"]),
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

    # ── Timing Checker ───────────────────────────────────────────────────────
    timing_warnings = []
    if timings and len(timings) >= 2:
        # Build timing map with resolved drug tags
        timing_records = []
        for t in timings:
            _, t_tags = get_drug_tags(t.drug)
            timing_records.append({
                "drug": t.drug,
                "minutes": t.hour * 60 + t.minute,
                "tags": t_tags,
            })

        for rule in RULES:
            if not rule.get("timing_sensitive"):
                continue
            gap_h = rule.get("timing_gap_hours", 0)
            if gap_h <= 0:
                continue

            req1, req2 = list(rule["drugs"])
            for i in range(len(timing_records)):
                for j in range(i + 1, len(timing_records)):
                    t1, t2 = timing_records[i], timing_records[j]
                    if (req1 in t1["tags"] and req2 in t2["tags"]) or (req2 in t1["tags"] and req1 in t2["tags"]):
                        # Circular time diff across 24h midnight
                        diff = abs(t1["minutes"] - t2["minutes"])
                        gap_actual = min(diff, 1440 - diff)
                        if gap_actual < gap_h * 60:
                            timing_warnings.append({
                                "drugs": [t1["drug"], t2["drug"]],
                                "gap_required_hours": gap_h,
                                "gap_actual_minutes": gap_actual,
                                "message": rule.get("alternatives", ["Beri jarak waktu minum obat."])[0],
                            })

    if highest_status == "critical":
        color = "red"
        level = "Kritis"
        summary = "Ditemukan interaksi berbahaya! Risiko klinis tinggi, segera konsultasikan dengan apoteker atau dokter."
    elif highest_status == "moderate":
        color = "yellow"
        level = "Sedang"
        summary = "Ditemukan interaksi yang memerlukan perhatian. Pemantauan klinis dan penyesuaian jadwal disarankan."
    else:
        color = "green"
        level = "Aman"
        summary = "Tidak ditemukan interaksi berbahaya yang diketahui pada kombinasi obat ini."

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
# Drug Catalogue Endpoint (Autocomplete & Kamus)
# ---------------------------------------------------------------------------

@app.get("/api/drugs")
def get_drugs(session: Optional[str] = Cookie(default=None)):
    # Collect comprehensive list for autocomplete
    all_drugs = sorted(set(
        list(DRUG_INFO.keys()) +
        [d for rule in RULES for d in rule["drugs"]] +
        list(BRAND_TO_GENERIC.keys()) +
        list(SYNONYMS.keys())
    ))

    pairs = [
        {
            "drugs": list(rule["drugs"]),
            "level": rule["level"],
            "status": rule["status"],
            "description": rule["description"],
            "score": rule.get("score", 0),
            "mechanism": rule.get("mechanism"),
            "mechanism_detail": rule.get("mechanism_detail"),
            "alternatives": rule.get("alternatives", []),
        }
        for rule in RULES
    ]

    return {
        "drugs": all_drugs,
        "pairs": pairs,
        "catalog": DRUG_INFO,
    }

# ---------------------------------------------------------------------------
# Drug Identification from OCR Text Endpoint
# ---------------------------------------------------------------------------

class IdentifyRequest(BaseModel):
    text: str

@app.post("/api/identify-drug")
def identify_drug(payload: IdentifyRequest, session: Optional[str] = Cookie(default=None)):
    raw_text = payload.text.lower()
    # Normalize OCR text
    clean_text = re.sub(r'[^a-z0-9\s-]', ' ', raw_text)
    tokens = [t.strip() for t in clean_text.split() if len(t.strip()) >= 3]

    matched_generics: dict[str, str] = {}

    # 1. Multi-word and exact brand matching
    for brand, generic in BRAND_TO_GENERIC.items():
        if f" {brand} " in f" {clean_text} " or brand in tokens:
            if generic not in matched_generics:
                matched_generics[generic] = f"merek dagang: {brand.title()}"

    # 2. Known generic drugs in catalog
    all_known_generics = set(DRUG_INFO.keys()) | {d for rule in RULES for d in rule["drugs"]}
    for generic in all_known_generics:
        if f" {generic} " in f" {clean_text} " or generic in tokens:
            if generic not in matched_generics:
                matched_generics[generic] = f"nama generik: {generic.title()}"

    # 3. Synonym matching
    for syn, std in SYNONYMS.items():
        if f" {syn} " in f" {clean_text} " or syn in tokens:
            target = BRAND_TO_GENERIC.get(std, std)
            if target not in matched_generics:
                matched_generics[target] = f"sinonim: {syn.title()} ({std.title()})"

    # 4. Token fuzzy/substring match for longer tokens (len >= 5) to tolerate slight OCR typos
    if not matched_generics:
        for t in tokens:
            if len(t) >= 5:
                for brand, generic in BRAND_TO_GENERIC.items():
                    if len(brand) >= 5 and (brand in t or t in brand):
                        if generic not in matched_generics:
                            matched_generics[generic] = f"merek dagang: {brand.title()}"
                for generic in all_known_generics:
                    if len(generic) >= 5 and (generic in t or t in generic):
                        if generic not in matched_generics:
                            matched_generics[generic] = f"nama generik: {generic.title()}"

    if not matched_generics:
        return JSONResponse({"ok": False, "message": "Tidak ada obat yang dikenali dari teks ini."}, status_code=404)

    results = []
    for drug, via in matched_generics.items():
        info = DRUG_INFO.get(drug, {
            "name": drug.title(),
            "category": "Farmakologi Klinis",
            "description": f"Obat terdaftar dalam sistem klinis: {drug.title()}",
            "common_brands": ["-"],
            "side_effects": "Konsultasikan dengan apoteker untuk panduan dosis spesifik.",
            "notes": "Tercatat dalam basis data interaksi.",
        })
        results.append({
            "drug": drug,
            "info": info,
            "has_interactions": any(drug in rule["drugs"] for rule in RULES),
            "matched_via": via,
        })

    return {"ok": True, "matched": results}

# ---------------------------------------------------------------------------
# Share Result Endpoints (Feature 5)
# ---------------------------------------------------------------------------

class ShareRequest(BaseModel):
    drugs: List[str]
    result: dict
    note: Optional[str] = None

@app.post("/api/share")
def create_share(payload: ShareRequest, session: Optional[str] = Cookie(default=None)):
    token = str(uuid.uuid4())[:8]
    creator = SESSIONS.get(session, "Tamu (Guest)")
    SHARED_RESULTS[token] = {
        "drugs": payload.drugs,
        "result": payload.result,
        "note": payload.note,
        "created_by": creator,
        "created_at": int(time.time()),
    }
    save_shared(SHARED_RESULTS)
    return {"ok": True, "token": token}

@app.get("/api/share/{token}")
def get_share(token: str):
    data = SHARED_RESULTS.get(token)
    if not data:
        return JSONResponse({"ok": False, "message": "Link tidak ditemukan atau sudah kadaluarsa."}, status_code=404)
    return {"ok": True, **data}

# ---------------------------------------------------------------------------
# Static Files & Frontend Routing
# ---------------------------------------------------------------------------

app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/sw.js")
def service_worker():
    return FileResponse("sw.js", media_type="application/javascript")

@app.get("/manifest.json")
def manifest():
    return FileResponse("manifest.json", media_type="application/json")

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
async def not_found_handler(request: Request, exc):
    return FileResponse("not_found.html", status_code=404)

