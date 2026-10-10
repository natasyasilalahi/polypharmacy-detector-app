// Polypharmacy Detector - Clinical PWA Service Worker
const CACHE_NAME = 'polypharmacy-v3.0';

const STATIC_ASSETS = [
  '/',
  '/login',
  '/manifest.json',
  '/sw.js',
];

const BRAND_TO_GENERIC = {
  "coumadin": "warfarin",
  "jantoven": "warfarin",
  "simarc": "warfarin",
  "aspilets": "aspirin",
  "thrombo": "aspirin",
  "thrombo aspilets": "aspirin",
  "bayer": "aspirin",
  "cardioaspirin": "aspirin",
  "bodrexin": "aspirin",
  "plavix": "clopidogrel",
  "clopisan": "clopidogrel",
  "placta": "clopidogrel",
  "advil": "ibuprofen",
  "motrin": "ibuprofen",
  "proris": "ibuprofen",
  "farsifen": "ibuprofen",
  "bufect": "ibuprofen",
  "brufen": "ibuprofen",
  "panadol": "paracetamol",
  "tempra": "paracetamol",
  "sanmol": "paracetamol",
  "biogesic": "paracetamol",
  "pamol": "paracetamol",
  "dumin": "paracetamol",
  "sumagesic": "paracetamol",
  "tramal": "tramadol",
  "ultram": "tramadol",
  "tradyl": "tramadol",
  "ponstan": "mefenamic acid",
  "mefinal": "mefenamic acid",
  "voltaren": "diclofenac",
  "cataflam": "diclofenac",
  "flamar": "diclofenac",
  "toradol": "ketorolac",
  "scantoma": "ketorolac",
  "glucophage": "metformin",
  "diabex": "metformin",
  "glumin": "metformin",
  "forbetes": "metformin",
  "cordarone": "amiodarone",
  "pacerone": "amiodarone",
  "tiaryt": "amiodarone",
  "lanoxin": "digoxin",
  "fargoxin": "digoxin",
  "zestril": "lisinopril",
  "prinivil": "lisinopril",
  "tensipril": "lisinopril",
  "capoten": "captopril",
  "farmoten": "captopril",
  "norvasc": "amlodipine",
  "tensivask": "amlodipine",
  "amcor": "amlodipine",
  "divask": "amlodipine",
  "aldactone": "spironolactone",
  "letonal": "spironolactone",
  "spirola": "spironolactone",
  "lasix": "furosemide",
  "farsix": "furosemide",
  "impugan": "furosemide",
  "zocor": "simvastatin",
  "lipcut": "simvastatin",
  "cholestor": "simvastatin",
  "valesco": "simvastatin",
  "lipitor": "atorvastatin",
  "stator": "atorvastatin",
  "truvaz": "atorvastatin",
  "crestor": "rosuvastatin",
  "rosufer": "rosuvastatin",
  "ciproxin": "ciprofloxacin",
  "baquinor": "ciprofloxacin",
  "ciflos": "ciprofloxacin",
  "amoxil": "amoxicillin",
  "trimox": "amoxicillin",
  "yusimox": "amoxicillin",
  "hiconcil": "amoxicillin",
  "mylanta": "antacid",
  "promag": "antacid",
  "polysilane": "antacid",
  "gastrucid": "antacid",
  "magida": "antacid",
  "antasida doen": "antacid",
  "losec": "omeprazole",
  "prilosec": "omeprazole",
  "ozid": "omeprazole",
  "omz": "omeprazole",
  "nexium": "esomeprazole",
  "inpepsa": "sucralfate",
  "pantozol": "pantoprazole",
  "klacid": "clarithromycin",
  "abbotic": "clarithromycin",
  "bicrolin": "clarithromycin",
  "prozac": "fluoxetine",
  "nopres": "fluoxetine",
  "kalxetin": "fluoxetine",
  "zoloft": "sertraline",
  "fridep": "sertraline",
  "lexapro": "escitalopram",
  "cipralex": "escitalopram",
  "paxil": "paroxetine",
  "seroxat": "paroxetine",
  "nardil": "phenelzine",
  "parnate": "tranylcypromine",
  "marplan": "isocarboxazid",
  "jumex": "selegiline",
  "valium": "diazepam",
  "stesolid": "diazepam",
  "frimania": "lithium",
  "aspar": "potassium",
  "kcl": "potassium",
  "ksr": "potassium",
  "euthyrox": "levothyroxine",
  "thyrax": "levothyroxine",
  "viagra": "sildenafil",
  "ericfil": "sildenafil",
  "nitrokaf": "nitroglycerin",
  "isdn": "isosorbide dinitrate",
  "cedocard": "isosorbide dinitrate",
  "zyloric": "allopurinol",
  "puricemia": "allopurinol",
  "imuran": "azathioprine",
  "rheumatrex": "methotrexate",
  "trexall": "methotrexate"
};
const SYNONYMS = {
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
  "ferrous": "iron"
};
const DRUG_CLASSES = {
  "fluoxetine": [
    "ssri"
  ],
  "sertraline": [
    "ssri"
  ],
  "escitalopram": [
    "ssri"
  ],
  "citalopram": [
    "ssri"
  ],
  "paroxetine": [
    "ssri"
  ],
  "fluvoxamine": [
    "ssri"
  ],
  "phenelzine": [
    "maoi"
  ],
  "tranylcypromine": [
    "maoi"
  ],
  "isocarboxazid": [
    "maoi"
  ],
  "selegiline": [
    "maoi"
  ],
  "moclobemide": [
    "maoi"
  ],
  "ibuprofen": [
    "nsaid"
  ],
  "aspirin": [
    "nsaid",
    "antiplatelet"
  ],
  "mefenamic acid": [
    "nsaid"
  ],
  "diclofenac": [
    "nsaid"
  ],
  "ketorolac": [
    "nsaid"
  ],
  "meloxicam": [
    "nsaid"
  ],
  "naproxen": [
    "nsaid"
  ],
  "indomethacin": [
    "nsaid"
  ],
  "lisinopril": [
    "acei"
  ],
  "captopril": [
    "acei"
  ],
  "ramipril": [
    "acei"
  ],
  "enalapril": [
    "acei"
  ],
  "simvastatin": [
    "statin"
  ],
  "atorvastatin": [
    "statin"
  ],
  "rosuvastatin": [
    "statin"
  ],
  "pravastatin": [
    "statin"
  ],
  "omeprazole": [
    "ppi"
  ],
  "esomeprazole": [
    "ppi"
  ],
  "lansoprazole": [
    "ppi"
  ],
  "pantoprazole": [
    "ppi"
  ],
  "rabeprazole": [
    "ppi"
  ],
  "ciprofloxacin": [
    "quinolone"
  ],
  "levofloxacin": [
    "quinolone"
  ],
  "moxifloxacin": [
    "quinolone"
  ],
  "nitroglycerin": [
    "nitrate"
  ],
  "isosorbide dinitrate": [
    "nitrate"
  ]
};
const OFFLINE_RULES = [
  {
    "drugs": [
      "ibuprofen",
      "warfarin"
    ],
    "status": "critical",
    "level": "Kritis",
    "color": "red",
    "score": 40,
    "mechanism": "pharmacodynamic",
    "mechanism_detail": "NSAID menghambat COX-1 \u2192 agregasi trombosit dihambat + erosi mukosa GI \u2192 risiko perdarahan masif",
    "cyp": null,
    "alternatives": [
      "Ganti ibuprofen dengan Parasetamol (asetaminofen) untuk nyeri ringan-sedang."
    ],
    "description": "Warfarin + Ibuprofen: Kombinasi antikoagulan dan NSAID menghambat agregasi trombosit serta mengikis mukosa saluran cerna, melipatgandakan risiko perdarahan internal fatal (GI & intrakranial).",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 20,
        "note": "Lansia (\u226565 th): Integritas vaskular dan mukosa menurun, risiko perdarahan GI 3\u20134\u00d7 lebih tinggi. Gunakan parasetamol."
      },
      "ckd": {
        "score_add": 25,
        "note": "Gagal Ginjal (CKD): NSAID menurunkan laju filtrasi glomerulus (GFR) dan menghambat ekskresi obat. Kontraindikasi relatif."
      },
      "liver": {
        "score_add": 20,
        "note": "Gangguan Hati: Sintesis faktor pembekuan darah terganggu; efek antikoagulasi warfarin sulit diprediksi."
      },
      "pregnant": {
        "score_add": 35,
        "note": "Kehamilan: Warfarin teratogenik berat (sindrom warfarin fetal), NSAID memicu penutupan prematur duktus arteriosus. KONTRAINDIKASI MUTLAK."
      }
    }
  },
  {
    "drugs": [
      "aspirin",
      "warfarin"
    ],
    "status": "critical",
    "level": "Kritis",
    "color": "red",
    "score": 45,
    "mechanism": "pharmacodynamic",
    "mechanism_detail": "Dual antikoagulasi + antiplatelet ireversibel \u2192 hemostasis lumpuh total \u2192 risiko perdarahan berat",
    "cyp": null,
    "alternatives": [
      "Evaluasi indikasi dual terapi; konsultasikan dokter spesialis jantung/hepar untuk target INR yang lebih ketat."
    ],
    "description": "Warfarin + Aspirin: Kombinasi antikoagulan oral dan antiplatelet kuat menyebabkan penghambatan hemostasis ganda. Risiko perdarahan gastrointestinal dan hemoragik serebral sangat tinggi.",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 20,
        "note": "Lansia: Risiko perdarahan intrakranial fatal meningkat drastis. Pantau INR secara mingguan."
      },
      "ckd": {
        "score_add": 20,
        "note": "Gagal Ginjal (CKD): Klirens metabolit menurun, uremia memperburuk fungsi trombosit intrinsik."
      },
      "liver": {
        "score_add": 25,
        "note": "Gangguan Hati: Risiko perdarahan varises esofagus meningkat drastis."
      },
      "pregnant": {
        "score_add": 35,
        "note": "Kehamilan: Perdarahan retroplasenta dan malformasi kongenital berat. KONTRAINDIKASI MUTLAK."
      }
    }
  },
  {
    "drugs": [
      "alcohol",
      "metformin"
    ],
    "status": "critical",
    "level": "Kritis",
    "color": "red",
    "score": 42,
    "mechanism": "pharmacodynamic",
    "mechanism_detail": "Alkohol menghambat glukoneogenesis hepar + akumulasi laktat dari metformin \u2192 asidosis laktat fatal",
    "cyp": null,
    "alternatives": [
      "Hentikan konsumsi minuman beralkohol secara mutlak selama menjalani pengobatan metformin."
    ],
    "description": "Metformin + Alkohol: Alkohol menghambat glukoneogenesis hepatik dan memperlambat pembersihan laktat, memicu asidosis laktat (kematian hingga 50%). Risiko hipoglikemia berat juga meningkat.",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 15,
        "note": "Lansia: Cadangan glikogen hati lebih rendah, gejala asidosis laktat sering terselubung."
      },
      "ckd": {
        "score_add": 25,
        "note": "Gagal Ginjal (CKD): Metformin terakumulasi di tubulus ginjal, risiko asidosis laktat melonjak tajam."
      },
      "liver": {
        "score_add": 30,
        "note": "Gangguan Hati: Gangguan klirens laktat hepatik. KONTRAINDIKASI ABSOLUT."
      },
      "pregnant": {
        "score_add": 30,
        "note": "Kehamilan: Alkohol memicu Fetal Alcohol Syndrome (FAS) dan asidosis maternal-fetal membahayakan janin."
      }
    }
  },
  {
    "drugs": [
      "maoi",
      "ssri"
    ],
    "status": "critical",
    "level": "Kritis",
    "color": "red",
    "score": 50,
    "mechanism": "pharmacodynamic",
    "mechanism_detail": "SSRI blok reuptake 5-HT + MAOI blok degradasi 5-HT \u2192 hiperaktivasi sinaps serotonergik \u2192 Sindrom Serotonin",
    "cyp": null,
    "alternatives": [
      "Hentikan MAOI minimal 14 hari (atau 5 minggu untuk fluoxetine) sebelum memulai terapi SSRI."
    ],
    "description": "SSRI + MAOI: Kombinasi mematikan yang memicu Sindrom Serotonin ganas \u2014 ditandai hipertermia maligna, klonus, instabilitas otonom, kejang, dan henti kardiorespirasi.",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 15,
        "note": "Lansia: Eliminasi hepatik melambat; washout period harus diperpanjang minimal 21 hari."
      },
      "ckd": {
        "score_add": 10,
        "note": "CKD: Akumulasi metabolit aktif memperlama durasi toksisitas neurologis."
      },
      "liver": {
        "score_add": 15,
        "note": "Gangguan Hati: Metabolisme kedua antidepresan terhambat signifikan."
      },
      "pregnant": {
        "score_add": 25,
        "note": "Kehamilan: Krisis hipertensi dan hipertermia mengancam viabilitas janin secara langsung."
      }
    }
  },
  {
    "drugs": [
      "amiodarone",
      "simvastatin"
    ],
    "status": "critical",
    "level": "Kritis",
    "color": "red",
    "score": 40,
    "mechanism": "pharmacokinetic",
    "mechanism_detail": "Amiodarone inhibisi kuat CYP3A4 \u2192 bioavailabilitas simvastatin naik 4-5\u00d7 \u2192 miopati / rabdomiolisis",
    "cyp": "CYP3A4",
    "alternatives": [
      "Ganti simvastatin ke Rosuvastatin atau Pravastatin yang tidak dimetabolisme CYP3A4."
    ],
    "description": "Simvastatin + Amiodarone: Amiodarone menghambat enzim CYP3A4 hepar, menyebabkan kadar simvastatin plasma meningkat drastis hingga menimbulkan kerusakan serat otot berat (rabdomiolisis) dan gagal ginjal akut.",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 20,
        "note": "Lansia: Penurunan massa otot rangka dan fungsi ekskresi membuat rabdomiolisis berakibat fatal."
      },
      "ckd": {
        "score_add": 25,
        "note": "Gagal Ginjal (CKD): Mioglobinuria akibat rabdomiolisis mempercepat nekrosis tubular ginjal akut."
      },
      "liver": {
        "score_add": 15,
        "note": "Gangguan Hati: Peningkatan enzim transaminase hepatik (SGOT/SGPT) lebih sering timbul."
      },
      "pregnant": {
        "score_add": 35,
        "note": "Kehamilan: Simvastatin KONTRAINDIKASI Kategori X (teratogenik). Amiodarone berisiko gondok/hipotiroid fetal."
      }
    }
  },
  {
    "drugs": [
      "amiodarone",
      "digoxin"
    ],
    "status": "critical",
    "level": "Kritis",
    "color": "red",
    "score": 45,
    "mechanism": "pharmacokinetic",
    "mechanism_detail": "Amiodarone menghambat pompa P-glikoprotein & klirens ginjal \u2192 kadar digoxin naik 100% \u2192 aritmia maut",
    "cyp": "P-gp",
    "alternatives": [
      "Turunkan dosis digoxin sebesar 50% dan periksa konsentrasi serum digoxin secara rutin tiap 1\u20132 minggu."
    ],
    "description": "Digoxin + Amiodarone: Amiodarone mendesak digoxin dari ikatan protein jaringan dan menghambat sekresi tubulus ginjal melalui P-gp. Kadar serum digoxin meningkat hingga 2\u00d7 lipat, berisiko intoksikasi digitalis, blok AV, dan asistol.",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 20,
        "note": "Lansia: Volume distribusi digoxin mengecil; kadar terapeutik sangat dekat dengan ambang toksisitas."
      },
      "ckd": {
        "score_add": 25,
        "note": "Gagal Ginjal (CKD): Digoxin terutama dieliminasi melalui ginjal; retensi sangat membahayakan jantung."
      },
      "liver": {
        "score_add": 15,
        "note": "Gangguan Hati: Gangguan regulasi elektrolit mempercepat timbulnya aritmia mematikan."
      },
      "pregnant": {
        "score_add": 25,
        "note": "Kehamilan: Penetrasi plasenta dapat memicu aritmia fetal; pantau ketat detak jantung janin."
      }
    }
  },
  {
    "drugs": [
      "ibuprofen",
      "methotrexate"
    ],
    "status": "critical",
    "level": "Kritis",
    "color": "red",
    "score": 48,
    "mechanism": "pharmacokinetic",
    "mechanism_detail": "NSAID menghambat sintesis prostaglandin ginjal & sekresi tubulus \u2192 klirens methotrexate anjlok \u2192 pansitopenia fatal",
    "cyp": null,
    "alternatives": [
      "Gunakan Parasetamol untuk analgesia; hindari semua jenis NSAID selama terapi methotrexate dosis sedang-tinggi."
    ],
    "description": "Methotrexate + Ibuprofen: NSAID menurunkan perfusi ginjal dan bersaing pada sekresi tubulus, meningkatkan toksisitas methotrexate secara masif. Berisiko supresi sumsum tulang berat (pansitopenia) dan nekrosis mukosa GI.",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 20,
        "note": "Lansia: Cadangan sumsum tulang berkurang, mortalitas akibat sepsis pasca-pansitopenia sangat tinggi."
      },
      "ckd": {
        "score_add": 30,
        "note": "Gagal Ginjal (CKD): Methotrexate tertimbun cepat. KONTRAINDIKASI MUTLAK."
      },
      "liver": {
        "score_add": 20,
        "note": "Gangguan Hati: Hepatotoksisitas sinergis memicu sirosis atau fibrosis hati dini."
      },
      "pregnant": {
        "score_add": 40,
        "note": "Kehamilan: Methotrexate adalah abortifasien poten dan teratogenik berat (Kategori X). KONTRAINDIKASI ABSOLUT."
      }
    }
  },
  {
    "drugs": [
      "nitroglycerin",
      "sildenafil"
    ],
    "status": "critical",
    "level": "Kritis",
    "color": "red",
    "score": 50,
    "mechanism": "pharmacodynamic",
    "mechanism_detail": "PDE-5 inhibitor + donor nitrat \u2192 akumulasi cGMP masif di otot polos vaskular \u2192 vasodilatasi ekstrem & syok kardiogenik",
    "cyp": null,
    "alternatives": [
      "KONTRAINDIKASI MUTLAK. Jangan konsumsi nitrat dalam 24 jam setelah sildenafil."
    ],
    "description": "Sildenafil + Nitroglycerin: Inhibisi PDE-5 bersamaan dengan donor nitrat melipatgandakan kadar siklik GMP, menyebabkan hipotensi berat refrakter, kolaps kardiovaskular, dan infark miokard fatal.",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 15,
        "note": "Lansia: Refleks baroreseptor tumpul, risiko pingsan dan trauma kepala sangat tinggi."
      },
      "ckd": {
        "score_add": 15,
        "note": "Gagal Ginjal: Hipotensi mendadak memicu iskemia ginjal akut."
      },
      "liver": {
        "score_add": 20,
        "note": "Gangguan Hati: Metabolisme sildenafil melambat, durasi vasodilatasi ekstrem bertambah panjang."
      },
      "pregnant": {
        "score_add": 25,
        "note": "Kehamilan: Hipotensi maternal memangkas suplai darah uteroplasenta, memicu gawat janin."
      }
    }
  },
  {
    "drugs": [
      "warfarin",
      "ciprofloxacin"
    ],
    "status": "critical",
    "level": "Kritis",
    "color": "red",
    "score": 42,
    "mechanism": "pharmacokinetic",
    "mechanism_detail": "Ciprofloxacin inhibisi CYP1A2 & membasmi flora usus penghasil vitamin K \u2192 kadar warfarin & INR melonjak drastis",
    "cyp": "CYP1A2",
    "alternatives": [
      "Pilih antibiotik alternatif seperti Amoxicillin bila sensitif; turunkan dosis warfarin dan cek INR tiap 48 jam."
    ],
    "description": "Ciprofloxacin + Warfarin: Fluorokuinolon ini menghambat metabolisme hepatik warfarin dan membasmi bakteri usus pembentuk vitamin K. Lonjakan INR sering tidak terduga dan memicu perdarahan aktif masif.",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 20,
        "note": "Lansia: Hemostasis labil, INR mudah melejit >5. Pantau ketat tanda memar/hematuria."
      },
      "ckd": {
        "score_add": 15,
        "note": "Gagal Ginjal: Klirens ciprofloxacin berkurang, inhibisi enzim berlangsung lebih lama."
      },
      "liver": {
        "score_add": 20,
        "note": "Gangguan Hati: Cadangan vitamin K hepar rendah memperparah koagulopati."
      },
      "pregnant": {
        "score_add": 35,
        "note": "Kehamilan: Keduanya KONTRAINDIKASI pada kehamilan karena risiko malformasi dan artropati fetal."
      }
    }
  },
  {
    "drugs": [
      "atorvastatin",
      "clarithromycin"
    ],
    "status": "critical",
    "level": "Kritis",
    "color": "red",
    "score": 40,
    "mechanism": "pharmacokinetic",
    "mechanism_detail": "Clarithromycin inhibitor poten CYP3A4 \u2192 AUC atorvastatin naik hingga 400% \u2192 miopati & rabdomiolisis",
    "cyp": "CYP3A4",
    "alternatives": [
      "Hentikan sementara statin selama konsumsi clarithromycin, atau ganti antibiotik ke Azithromycin."
    ],
    "description": "Atorvastatin + Clarithromycin: Antibiotik makrolida clarithromycin menghambat enzim CYP3A4 secara kuat, melipatgandakan paparan atorvastatin dalam sirkulasi hingga memicu kerusakan otot berat (rabdomiolisis).",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 20,
        "note": "Lansia: Nyeri otot sering dikira keluhan rematik, keterlambatan penanganan memicu gagal ginjal."
      },
      "ckd": {
        "score_add": 25,
        "note": "Gagal Ginjal: Klirens mioglobin terhambat, mempercepat penurunan fungsi nefron."
      },
      "pregnant": {
        "score_add": 35,
        "note": "Kehamilan: Atorvastatin KONTRAINDIKASI Kategori X; mengganggu embriogenesis normal."
      }
    }
  },
  {
    "drugs": [
      "azathioprine",
      "allopurinol"
    ],
    "status": "critical",
    "level": "Kritis",
    "color": "red",
    "score": 45,
    "mechanism": "pharmacokinetic",
    "mechanism_detail": "Allopurinol menghambat xantin oksidase \u2192 metabolisme 6-merkaptopurin mandek \u2192 supresi sumsum tulang fatal",
    "cyp": null,
    "alternatives": [
      "Kurangi dosis azathioprine menjadi 25-33% dari dosis lazim dan pantau leukosit darah lengkap mingguan."
    ],
    "description": "Allopurinol + Azathioprine: Allopurinol menghambat degradasi metabolit aktif azathioprine (6-MP). Mengakibatkan penumpukan metabolit sitotoksik dan supresi sumsum tulang fatal (leukopenia, agranulositosis).",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 20,
        "note": "Lansia: Infeksi oportunistik akibat neutropenia berkembang sangat cepat menjadi sepsis fatal."
      },
      "ckd": {
        "score_add": 25,
        "note": "Gagal Ginjal: Klirens metabolit allopurinol (oxypurinol) menurun, inhibisi makin permanen."
      },
      "pregnant": {
        "score_add": 30,
        "note": "Kehamilan: Toksisitas genetik dan sitotoksik tinggi bagi diferensiasi organ fetus."
      }
    }
  },
  {
    "drugs": [
      "potassium",
      "lisinopril"
    ],
    "status": "moderate",
    "level": "Sedang",
    "color": "yellow",
    "score": 22,
    "mechanism": "pharmacodynamic",
    "mechanism_detail": "ACE inhibitor menurunkan aldosteron \u2192 retensi kalium di tubulus distal + suplemen kalium \u2192 hiperkalemia",
    "cyp": null,
    "alternatives": [
      "Hentikan suplemen kalium kecuali terdokumentasi hipokalemia; pantau elektrolit serum secara berkala."
    ],
    "description": "Lisinopril + Kalium: ACE inhibitor mengurangi sekresi aldosteron sehingga ginjal menahan kalium. Penambahan suplemen kalium dapat memicu hiperkalemia aritmogenik yang berbahaya bagi konduksi jantung.",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 15,
        "note": "Lansia: Ekskresi kalium menurun seiring penuaan fisiologis ginjal."
      },
      "ckd": {
        "score_add": 25,
        "note": "Gagal Ginjal (CKD): Kombinasi ini menjadi KRITIS. Risiko aritmia ventrikel meningkat tajam."
      },
      "pregnant": {
        "score_add": 35,
        "note": "Kehamilan: ACE inhibitor KONTRAINDIKASI Kategori D/X (menyebabkan oligohidramnion, hipoplasia paru fetal)."
      }
    }
  },
  {
    "drugs": [
      "ibuprofen",
      "metformin"
    ],
    "status": "moderate",
    "level": "Sedang",
    "color": "yellow",
    "score": 24,
    "mechanism": "pharmacokinetic",
    "mechanism_detail": "NSAID menurunkan sintesis prostaglandin ginjal \u2192 vasokonstriksi aferen & GFR turun \u2192 metformin tertimbun",
    "cyp": null,
    "alternatives": [
      "Pilih analgesik Parasetamol; hindari pemakaian NSAID rutin pada pasien diabetes melitus tipe 2."
    ],
    "description": "Metformin + Ibuprofen: NSAID menurunkan perfusi ginjal dan laju filtrasi glomerulus, menghambat eliminasi metformin dan meningkatkan risiko asidosis laktat serta cedera ginjal akut.",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 18,
        "note": "Lansia: Kombinasi ini menjadi KRITIS karena laju GFR basal lansia sudah di bawah rata-rata."
      },
      "ckd": {
        "score_add": 28,
        "note": "Gagal Ginjal (CKD): Risiko nekrosis tubular dan asidosis laktat berat. KONTRAINDIKASI."
      },
      "pregnant": {
        "score_add": 25,
        "note": "Kehamilan: NSAID trimester 3 memicu penutupan dini duktus arteriosus janin."
      }
    }
  },
  {
    "drugs": [
      "antacid",
      "ciprofloxacin"
    ],
    "status": "moderate",
    "level": "Sedang",
    "color": "yellow",
    "score": 20,
    "mechanism": "pharmacokinetic",
    "mechanism_detail": "Kation multivalent (Al\u00b3\u207a, Mg\u00b2\u207a) membentuk khelat tidak larut dengan ciprofloxacin \u2192 bioavailabilitas anjlok 85-90%",
    "cyp": null,
    "alternatives": [
      "Beri jarak waktu minum: Ciprofloxacin 2 jam SEBELUM atau 6 jam SESUDAH antasida."
    ],
    "description": "Ciprofloxacin + Antasida: Ion aluminium dan magnesium dalam antasida mengikat ciprofloxacin di saluran pencernaan menjadi senyawa khelat yang tidak dapat diserap, menyebabkan kegagalan terapi antibiotik.",
    "timing_sensitive": true,
    "timing_gap_hours": 2,
    "patient_risk": {
      "pregnant": {
        "score_add": 20,
        "note": "Kehamilan: Quinolone berisiko merusak kartilago pertumbuhan sendi janin."
      }
    }
  },
  {
    "drugs": [
      "amlodipine",
      "simvastatin"
    ],
    "status": "moderate",
    "level": "Sedang",
    "color": "yellow",
    "score": 20,
    "mechanism": "pharmacokinetic",
    "mechanism_detail": "Amlodipine inhibisi parsial CYP3A4 \u2192 kadar simvastatin naik hingga 77% \u2192 risiko miopati meningkat",
    "cyp": "CYP3A4",
    "alternatives": [
      "Batasi dosis maksimal simvastatin 20 mg/hari bila digunakan bersama amlodipine, atau beralih ke Rosuvastatin."
    ],
    "description": "Amlodipine + Simvastatin: Amlodipine menghambat pemecahan simvastatin oleh CYP3A4 di hati, meningkatkan konsentrasi statin dalam darah dan melipatgandakan risiko nyeri otot dan miopati.",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 15,
        "note": "Lansia: Gejala miopati sering terabaikan hingga menjadi kelemahan motorik berat."
      },
      "pregnant": {
        "score_add": 30,
        "note": "Kehamilan: Simvastatin KONTRAINDIKASI MUTLAK pada kehamilan."
      }
    }
  },
  {
    "drugs": [
      "tramadol",
      "fluoxetine"
    ],
    "status": "moderate",
    "level": "Sedang",
    "color": "yellow",
    "score": 25,
    "mechanism": "pharmacokinetic",
    "mechanism_detail": "Fluoxetine blok CYP2D6 (aktivasi tramadol terganggu) + inhibisi reuptake serotonin ganda \u2192 sindrom serotonin & kejang",
    "cyp": "CYP2D6",
    "alternatives": [
      "Pertimbangkan analgesik non-opioid seperti Parasetamol; bila perlu opioid, pantau ketat tanda agitasi dan tremor."
    ],
    "description": "Fluoxetine + Tramadol: Fluoxetine menghambat aktivasi metabolik tramadol sekaligus meningkatkan transmisi serotonin sentral, meningkatkan risiko sindrom serotonin sedang dan menurunkan ambang kejang.",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 15,
        "note": "Lansia: Risiko sedasi berat, disorientasi kognitif, dan cedera akibat jatuh."
      },
      "pregnant": {
        "score_add": 25,
        "note": "Kehamilan: Tramadol menembus plasenta, berisiko neonatal opioid withdrawal syndrome (NOWS)."
      }
    }
  },
  {
    "drugs": [
      "spironolactone",
      "potassium"
    ],
    "status": "moderate",
    "level": "Sedang",
    "color": "yellow",
    "score": 22,
    "mechanism": "pharmacodynamic",
    "mechanism_detail": "Diuretik hemat kalium antagonis reseptor aldosteron + asupan kalium eksternal \u2192 akumulasi kalium berbahaya",
    "cyp": null,
    "alternatives": [
      "Hentikan suplemen kalium; pantau kadar elektrolit kalium serum secara berkala."
    ],
    "description": "Spironolactone + Kalium: Spironolactone secara langsung menghambat ekskresi ion kalium di tubulus renalis distal. Pemberian kalium tambahan sangat mudah memicu hiperkalemia simtomatik.",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 15,
        "note": "Lansia: Penurunan laju filtrasi mempercepat lonjakan konsentrasi kalium plasma."
      },
      "ckd": {
        "score_add": 25,
        "note": "Gagal Ginjal (CKD): Kombinasi menjadi KRITIS. Kontraindikasi kuat pada eGFR < 30 mL/min."
      },
      "pregnant": {
        "score_add": 30,
        "note": "Kehamilan: Spironolactone memiliki efek antiandrogenik (berisiko feminisasi janin laki-laki)."
      }
    }
  },
  {
    "drugs": [
      "omeprazole",
      "clopidogrel"
    ],
    "status": "moderate",
    "level": "Sedang",
    "color": "yellow",
    "score": 26,
    "mechanism": "pharmacokinetic",
    "mechanism_detail": "Omeprazole inhibisi kuat CYP2C19 \u2192 bioaktivasi prodrug clopidogrel terhambat \u2192 efek antiplatelet turun 40-50%",
    "cyp": "CYP2C19",
    "alternatives": [
      "Ganti omeprazole dengan Pantoprazole yang memiliki inhibisi minimal terhadap CYP2C19."
    ],
    "description": "Clopidogrel + Omeprazole: Omeprazole menghambat enzim CYP2C19 yang krusial untuk mengubah clopidogrel menjadi bentuk aktifnya, menurunkan proteksi antiplatelet dan meningkatkan risiko trombosis stent / serangan jantung.",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 15,
        "note": "Lansia: Kejadian kardiovaskular sekunder lebih sering terjadi bila antiplatelet gagal bekerja."
      },
      "pregnant": {
        "score_add": 15,
        "note": "Kehamilan: Evaluasi hemostasis sebelum persalinan."
      }
    }
  },
  {
    "drugs": [
      "furosemide",
      "digoxin"
    ],
    "status": "moderate",
    "level": "Sedang",
    "color": "yellow",
    "score": 24,
    "mechanism": "pharmacodynamic",
    "mechanism_detail": "Loop diuretik membuang K\u207a & Mg\u00b2\u207a \u2192 hipokalemia meningkatkan afinitas digoxin pada Na\u207a/K\u207a-ATPase miokard \u2192 aritmia",
    "cyp": null,
    "alternatives": [
      "Monitor kadar kalium serum dan tambahkan suplemen kalium / spironolactone jika kalium < 4.0 mEq/L."
    ],
    "description": "Digoxin + Furosemide: Diuretik kuat furosemide menyebabkan ekskresi kalium berlebih (hipokalemia). Kadar kalium darah yang rendah melipatgandakan sensitivitas jantung terhadap toksisitas digoxin.",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 20,
        "note": "Lansia: Sensitivitas miokard meningkat, aritmia fatal dapat terjadi meski kadar digoxin normal."
      },
      "ckd": {
        "score_add": 20,
        "note": "CKD: Regulasi elektrolit sangat tidak stabil."
      },
      "pregnant": {
        "score_add": 15,
        "note": "Kehamilan: Hipoperfusi plasenta dan imbalans elektrolit membebani janin."
      }
    }
  },
  {
    "drugs": [
      "alcohol",
      "paracetamol"
    ],
    "status": "moderate",
    "level": "Sedang",
    "color": "yellow",
    "score": 28,
    "mechanism": "pharmacokinetic",
    "mechanism_detail": "Alkohol induksi CYP2E1 \u2192 bioaktivasi parasetamol menjadi metabolit toksik NAPQI meningkat \u2192 gagal hati akut",
    "cyp": "CYP2E1",
    "alternatives": [
      "Hindari alkohol; batasi dosis parasetamol maksimal 2000 mg/hari pada riwayat konsumsi alkohol."
    ],
    "description": "Parasetamol + Alkohol: Konsumsi alkohol kronis menginduksi enzim CYP2E1 dan menguras cadangan glutation hati. Akibatnya, parasetamol cepat terurai menjadi metabolit reaktif NAPQI yang memicu nekrosis sel hati sentrilobular.",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "liver": {
        "score_add": 30,
        "note": "Gangguan Hati: Risiko gagal hati fulminan sangat tinggi. Kombinasi menjadi KRITIS."
      },
      "elderly": {
        "score_add": 15,
        "note": "Lansia: Glutation hepar menurun alami, risiko nekrosis hepar lebih cepat terjadi."
      },
      "pregnant": {
        "score_add": 25,
        "note": "Kehamilan: Sindrom alkohol janin (FAS) + beban hepatotoksik ganda."
      }
    }
  },
  {
    "drugs": [
      "antacid",
      "levothyroxine"
    ],
    "status": "moderate",
    "level": "Sedang",
    "color": "yellow",
    "score": 20,
    "mechanism": "pharmacokinetic",
    "mechanism_detail": "Kation kalsium/aluminium/magnesium dalam antasida mengadsorpsi T4 \u2192 penyerapan hormon tiroid anjlok",
    "cyp": null,
    "alternatives": [
      "Beri jeda minimal 4 jam antara minum levothyroxine dan antasida / suplemen mineral."
    ],
    "description": "Levothyroxine + Antasida: Antasida mengikat hormon tiroid sintetik di saluran cerna dan menurunkan penyerapannya, memicu kegagalan kontrol hipotiroidisme.",
    "timing_sensitive": true,
    "timing_gap_hours": 4,
    "patient_risk": {
      "pregnant": {
        "score_add": 25,
        "note": "Kehamilan: Hipotiroidisme maternal yang tidak terkontrol mengganggu perkembangan otak dan IQ janin."
      }
    }
  },
  {
    "drugs": [
      "ibuprofen",
      "ciprofloxacin"
    ],
    "status": "moderate",
    "level": "Sedang",
    "color": "yellow",
    "score": 25,
    "mechanism": "pharmacodynamic",
    "mechanism_detail": "Fluorokuinolon + NSAID bersaing menghambat reseptor GABA di SSP \u2192 stimulasi SSP berlebih \u2192 risiko kejang",
    "cyp": null,
    "alternatives": [
      "Ganti ibuprofen ke Parasetamol selama terapi ciprofloxacin, terutama bila ada riwayat epilepsi."
    ],
    "description": "Ciprofloxacin + Ibuprofen: Kombinasi antibiotik fluorokuinolon dengan NSAID meningkatkan efek inhibisi terhadap reseptor GABA otak, berpotensi memicu stimulasi sistem saraf pusat berlebih hingga kejang tonik-klonik.",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 15,
        "note": "Lansia: Ambang kejang lebih rendah dan permeabilitas sawar darah otak lebih tinggi."
      },
      "pregnant": {
        "score_add": 25,
        "note": "Kehamilan: Quinolone dan NSAID keduanya dihindari pada masa gestasi."
      }
    }
  },
  {
    "drugs": [
      "ibuprofen",
      "lithium"
    ],
    "status": "critical",
    "level": "Kritis",
    "color": "red",
    "score": 42,
    "mechanism": "pharmacokinetic",
    "mechanism_detail": "NSAID menghambat sintesis prostaglandin renal \u2192 filtrasi lithium anjlok \u2192 kadar plasma melonjak 40-60%",
    "cyp": null,
    "alternatives": [
      "Ganti dengan Parasetamol; hindari semua jenis NSAID bila pasien dalam terapi pemeliharaan lithium."
    ],
    "description": "Lithium + Ibuprofen: NSAID mengurangi laju filtrasi ginjal terhadap ion lithium. Kadar serum lithium meningkat cepat menuju level toksik: tremor kasar, ataxia, konfusi, dan koma.",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 20,
        "note": "Lansia: Sangat rentan terhadap toksisitas neuro-renal lithium."
      },
      "ckd": {
        "score_add": 25,
        "note": "Gagal Ginjal: Klirens ginjal sudah rendah, intoksikasi terjadi sangat cepat."
      },
      "pregnant": {
        "score_add": 35,
        "note": "Kehamilan: Lithium teratogenik (Ebstein anomaly pada katup jantung fetus)."
      }
    }
  },
  {
    "drugs": [
      "diazepam",
      "omeprazole"
    ],
    "status": "moderate",
    "level": "Sedang",
    "color": "yellow",
    "score": 18,
    "mechanism": "pharmacokinetic",
    "mechanism_detail": "Omeprazole menghambat CYP2C19 \u2192 eliminasi diazepam tertunda \u2192 perpanjangan waktu paruh & sedasi berlebih",
    "cyp": "CYP2C19",
    "alternatives": [
      "Gunakan benzodiazepine yang tidak dimetabolisme CYP seperti Lorazepam, atau ganti omeprazole ke Pantoprazole."
    ],
    "description": "Omeprazole + Diazepam: Omeprazole menghambat metabolisme hepatik diazepam melalui CYP2C19, memperpanjang durasi kerja obat dan memperdalam efek kantuk, ataksia, serta depresi pernapasan.",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 20,
        "note": "Lansia: Sedasi berkepanjangan meningkatkan risiko delirium dan jatuh patah tulang panggul."
      }
    }
  },
  {
    "drugs": [
      "spironolactone",
      "lisinopril"
    ],
    "status": "moderate",
    "level": "Sedang",
    "color": "yellow",
    "score": 25,
    "mechanism": "pharmacodynamic",
    "mechanism_detail": "Dual blokade sistem Renin-Angiotensin-Aldosteron \u2192 inhibisi sekresi kalium ganda \u2192 hiperkalemia berat",
    "cyp": null,
    "alternatives": [
      "Bila diindikasikan untuk gagal jantung (HFrEF), gunakan dosis rendah spironolactone (12.5\u201325 mg) dan pantau kalium rutin."
    ],
    "description": "Lisinopril + Spironolactone: Kombinasi penghambat ACE dan antagonis aldosteron memblokir sekresi kalium secara ganda, berisiko tinggi hiperkalemia berat terutama bila pasien mengalami dehidrasi atau penurunan fungsi ginjal.",
    "timing_sensitive": false,
    "timing_gap_hours": 0,
    "patient_risk": {
      "elderly": {
        "score_add": 18,
        "note": "Lansia: Kombinasi ini menjadi KRITIS. Monitor elektrolit tiap 1-2 minggu di awal terapi."
      },
      "ckd": {
        "score_add": 28,
        "note": "Gagal Ginjal: Risiko henti jantung akibat hiperkalemia melonjak tajam."
      },
      "pregnant": {
        "score_add": 35,
        "note": "Kehamilan: Keduanya KONTRAINDIKASI MUTLAK pada kehamilan."
      }
    }
  }
];
const DRUG_CATALOG = {
  "warfarin": {
    "name": "Warfarin",
    "category": "Antikoagulan Oral",
    "description": "Obat antikoagulan (pengencer darah) antagonis vitamin K untuk mencegah trombosis vena dalam, emboli paru, fibrilasi atrium, dan stroke.",
    "common_brands": [
      "Coumadin",
      "Jantoven",
      "Simarc"
    ],
    "side_effects": "Perdarahan gusi, memar spontan, hematuria, melena, nekrosis kulit (jarang).",
    "notes": "Membutuhkan pemantauan INR rutin (target 2.0\u20133.0). Sangat rentan interaksi dengan makanan tinggi vitamin K dan NSAID."
  },
  "ibuprofen": {
    "name": "Ibuprofen",
    "category": "NSAID (Anti-Inflamasi Non-Steroid)",
    "description": "Analgesik, antipiretik, dan anti-inflamasi penghambat enzim COX-1 dan COX-2 untuk meredakan nyeri ringan hingga sedang dan demam.",
    "common_brands": [
      "Advil",
      "Proris",
      "Motrin",
      "Farsifen",
      "Bufect"
    ],
    "side_effects": "Dispepsia, nyeri ulu hati, tukak lambung, perdarahan GI, retensi cairan, penurunan fungsi ginjal.",
    "notes": "Hindari pada riwayat tukak peptik, gagal ginjal, lansia, dan kehamilan trimester ketiga."
  },
  "aspirin": {
    "name": "Aspirin (Asam Asetilsalisilat)",
    "category": "Antiplatelet / Analgesik",
    "description": "Inhibitor ireversibel COX-1 trombosit untuk prevensi sekunder infark miokard, stroke iskemik, dan sindrom koroner akut.",
    "common_brands": [
      "Aspilets",
      "Thrombo Aspilets",
      "Bayer Aspirin",
      "Cardioaspirin"
    ],
    "side_effects": "Iritasi mukosa lambung, erosi gaster, tinitus (pada dosis tinggi), perpanjangan waktu perdarahan.",
    "notes": "Dosis kardioprotektif lazim 80\u2013100 mg per hari. Berbahaya bila dikombinasi tanpa indikasi dengan antikoagulan lain."
  },
  "metformin": {
    "name": "Metformin",
    "category": "Antidiabetik Oral (Biguanide)",
    "description": "Terapi lini pertama diabetes melitus tipe 2 yang menurunkan glukoneogenesis hepatik dan memperbaiki sensitivitas insulin perifer.",
    "common_brands": [
      "Glucophage",
      "Diabex",
      "Glumin",
      "Forbetes"
    ],
    "side_effects": "Gangguan pencernaan, mual, diare, rasa logam di mulut, defisiensi vitamin B12 jangka panjang, asidosis laktat (jarang namun fatal).",
    "notes": "Diminum bersamaan atau sesudah makan. Hentikan sebelum prosedur dengan kontras iodinasi radiologi."
  },
  "amiodarone": {
    "name": "Amiodarone",
    "category": "Antiaritmia Kelas III",
    "description": "Antiaritmia spektrum luas pemanjang potensial aksi untuk aritmia ventrikel refrakter dan fibrilasi atrium simtomatik.",
    "common_brands": [
      "Cordarone",
      "Pacerone",
      "Tiaryt"
    ],
    "side_effects": "Fibrosis paru, disfungsi tiroid (hipo/hipertiroid), peningkatan enzim hepar, mikrodeposit kornea, fotosensitivitas.",
    "notes": "Waktu paruh eliminasi sangat panjang (40\u201355 hari). Merupakan inhibitor kuat CYP3A4, CYP2C9, dan P-glikoprotein."
  },
  "simvastatin": {
    "name": "Simvastatin",
    "category": "Statin (HMG-CoA Reductase Inhibitor)",
    "description": "Obat penurun kolesterol LDL dan trigliserida serta penstabil plak aterosklerosis pada penyakit kardiovaskular.",
    "common_brands": [
      "Zocor",
      "Lipcut",
      "Cholestor",
      "Valesco"
    ],
    "side_effects": "Mialgia, kram otot, peningkatan transaminase hepar, rabdomiolisis (jarang).",
    "notes": "Diminum pada malam hari. Dimetabolisme kuat oleh CYP3A4 sehingga sensitif terhadap interaksi obat dan jus grapefruit."
  },
  "atorvastatin": {
    "name": "Atorvastatin",
    "category": "Statin (Penurun Kolesterol Intensitas Tinggi)",
    "description": "Statin potensi tinggi untuk dislipidemia dan reduksi risiko infark miokard dan stroke pada pasien berisiko tinggi.",
    "common_brands": [
      "Lipitor",
      "Stator",
      "Truvaz"
    ],
    "side_effects": "Nyeri otot, sakit kepala, gangguan cerna, peningkatan enzim hati.",
    "notes": "Dapat diminum kapan saja (pagi atau malam). Inhibitor kuat CYP3A4 seperti clarithromycin meningkatkan kadar atorvastatin secara masif."
  },
  "digoxin": {
    "name": "Digoxin",
    "category": "Glikosida Jantung (Inotropik Positif)",
    "description": "Meningkatkan kontraktilitas miokard dan memperlambat konduksi nodus AV pada gagal jantung kronik dan fibrilasi atrium.",
    "common_brands": [
      "Lanoxin",
      "Fargoxin"
    ],
    "side_effects": "Anoreksia, mual, muntah, gangguan visual persepsi warna kuning/hijau (xanthopsia), aritmia ventrikel.",
    "notes": "Indeks terapeutik sangat sempit (0.5\u20130.9 ng/mL). Klirens terutama melalui ginjal; pantau ketat bila ada hipokalemia."
  },
  "lisinopril": {
    "name": "Lisinopril",
    "category": "ACE Inhibitor (Antihipertensi)",
    "description": "Menghambat sintesis Angiotensin II untuk menurunkan tekanan darah dan mengurangi beban jantung pada gagal jantung kongestif.",
    "common_brands": [
      "Zestril",
      "Prinivil",
      "Tensipril"
    ],
    "side_effects": "Batuk kering persisten (karena bradikinin), hiperkalemia, hipotensi ortostatik, angioedema (jarang).",
    "notes": "Kontraindikasi mutlak pada kehamilan. Pantau fungsi ginjal (kreatinin) dan elektrolit kalium setelah inisiasi."
  },
  "potassium": {
    "name": "Kalium (Potassium)",
    "category": "Suplemen Elektrolit Kation",
    "description": "Elektrolit esensial untuk transmisi impuls saraf, kontraksi otot rangka, dan stabilitas elektrofisiologi membran jantung.",
    "common_brands": [
      "KSR",
      "Aspar-K",
      "Kalium Klorida (KCl)"
    ],
    "side_effects": "Iritasi lambung, mual, diare, hiperkalemia bila ekskresi renal terganggu.",
    "notes": "Jangan digerus pada sediaan lepas lambat. Hindari penggunaan bersamaan dengan ACEI, ARB, atau diuretik hemat kalium."
  },
  "ciprofloxacin": {
    "name": "Ciprofloxacin",
    "category": "Antibiotik Fluorokuinolon",
    "description": "Antibiotik bakterisidal penghambat DNA girase untuk infeksi saluran kemih rumit, infeksi intraabdomen, dan pernapasan.",
    "common_brands": [
      "Ciproxin",
      "Baquinor",
      "Ciflos"
    ],
    "side_effects": "Mual, diare, sakit kepala, tendinitis dan ruptur tendon achilles (jarang), perpanjangan interval QT.",
    "notes": "Hindari bersama antasida atau susu/kalsium. Beri jarak minimal 2 jam. Hindari pada anak-anak dan kehamilan."
  },
  "antacid": {
    "name": "Antasida",
    "category": "Penetral Asam Lambung",
    "description": "Kombinasi Aluminium Hidroksida dan Magnesium Hidroksida untuk meredakan gejala gastritis, dispepsia, dan tukak lambung.",
    "common_brands": [
      "Promag",
      "Mylanta",
      "Polysilane",
      "Antasida DOEN"
    ],
    "side_effects": "Konstipasi (Al), diare (Mg), gangguan absorpsi mineral dan obat lain.",
    "notes": "Kation logam mengikat banyak antibiotik (fluorokuinolon, tetrasiklin) dan levothyroxine. Selalu beri jeda minimal 2 jam."
  },
  "amlodipine": {
    "name": "Amlodipine",
    "category": "Calcium Channel Blocker (Dihidropiridin)",
    "description": "Vasodilator arteri perifer untuk terapi hipertensi dan profilaksis angina pektoris stabil.",
    "common_brands": [
      "Norvasc",
      "Tensivask",
      "Divask",
      "Amcor"
    ],
    "side_effects": "Edema pergelangan kaki perifer, pusing, flushing wajah, palpitasi.",
    "notes": "Bekerja secara independen dari asupan garam. Memiliki efek inhibisi ringan pada CYP3A4."
  },
  "fluoxetine": {
    "name": "Fluoxetine",
    "category": "Antidepresan SSRI",
    "description": "Inhibitor selektif reuptake serotonin untuk depresi mayor, gangguan obsesif-kompulsif (OCD), dan bulimia.",
    "common_brands": [
      "Prozac",
      "Nopres",
      "Kalxetin"
    ],
    "side_effects": "Insomnia, mual, tremor, agitasi, penurunan libido, sindrom serotonin bila dikombinasi.",
    "notes": "Memiliki metabolit aktif norfluoxetine dengan waktu paruh sangat panjang (hingga 1\u20132 minggu). Membutuhkan washout period 5 minggu sebelum MAOI."
  },
  "tramadol": {
    "name": "Tramadol",
    "category": "Analgesik Opioid Sentral",
    "description": "Agonis reseptor mu-opioid dan inhibitor reuptake serotonin/norepinefrin untuk nyeri akut sedang hingga berat.",
    "common_brands": [
      "Tramal",
      "Ultram",
      "Tradyl"
    ],
    "side_effects": "Mual, pusing, konstipasi, sedasi, risiko ketergantungan dan penurunan ambang kejang.",
    "notes": "Kombinasi dengan antidepresan serotonergik sangat berisiko memicu sindrom serotonin dan kejang."
  },
  "spironolactone": {
    "name": "Spironolactone",
    "category": "Diuretik Hemat Kalium (Antagonis Aldosteron)",
    "description": "Diuretik hemat kalium untuk gagal jantung kronis (HFrEF), hipertensi resisten, asites sirosis hati, dan hiperaldosteronisme.",
    "common_brands": [
      "Aldactone",
      "Letonal",
      "Spirola"
    ],
    "side_effects": "Hiperkalemia, ginekomastia pada pria, gangguan siklus menstruasi pada wanita, dehidrasi.",
    "notes": "Wajib memantau kadar kalium dan kreatinin serum secara berkala."
  },
  "clopidogrel": {
    "name": "Clopidogrel",
    "category": "Antiplatelet Thienopyridine (P2Y12 Inhibitor)",
    "description": "Prodrug antiplatelet pencegah trombosis vaskular pada sindrom koroner akut, pasca-stent jantung, dan stroke iskemik.",
    "common_brands": [
      "Plavix",
      "Clopisan",
      "Placta"
    ],
    "side_effects": "Perdarahan, memar, purpura, dispepsia.",
    "notes": "Membutuhkan aktivasi bio-metabolik oleh enzim CYP2C19. Dihambat oleh omeprazole."
  },
  "omeprazole": {
    "name": "Omeprazole",
    "category": "Proton Pump Inhibitor (PPI)",
    "description": "Menekan sekresi asam lambung melalui inhibisi pompa H+/K+-ATPase pada GERD, tukak duodenum, dan perlindungan lambung.",
    "common_brands": [
      "Losec",
      "Prilosec",
      "Ozid",
      "OMZ"
    ],
    "side_effects": "Sakit kepala, diare, mual, polip kelenjar fundus lambung, hipomagnesemia jangka panjang.",
    "notes": "Inhibitor moderat CYP2C19. Diminum 30\u201360 menit sebelum makan pagi."
  },
  "methotrexate": {
    "name": "Methotrexate",
    "category": "Antimetabolit Imunosupresan / Sitostatika",
    "description": "Antagonis asam folat untuk rheumatoid arthritis, psoriasis berat, dan keganasan hematologi.",
    "common_brands": [
      "Rheumatrex",
      "Trexall"
    ],
    "side_effects": "Stomatitis, pansitopenia, mual, hepatotoksisitas, pneumonitis interstitial.",
    "notes": "Dosis mingguan untuk penyakit autoimun. Berikan asam folat pada hari non-dosis. Hindari kombinasi dengan NSAID."
  },
  "sildenafil": {
    "name": "Sildenafil",
    "category": "PDE-5 Inhibitor",
    "description": "Vasodilator pemanjang kerja cGMP untuk disfungsi ereksi dan hipertensi arteri pulmonal (PAH).",
    "common_brands": [
      "Viagra",
      "Ericfil",
      "Revatio"
    ],
    "side_effects": "Sakit kepala, kemerahan wajah (flushing), hidung tersumbat, dispepsia, penglihatan kebiruan.",
    "notes": "KONTRAINDIKASI MUTLAK dengan segala bentuk nitrat organik."
  },
  "nitroglycerin": {
    "name": "Nitroglycerin / Nitrat",
    "category": "Vasodilator Nitrat Organik",
    "description": "Donor nitrat untuk terminasi cepat dan pencegahan serangan angina pektoris.",
    "common_brands": [
      "Nitrokaf",
      "Nitrocine",
      "ISDN (Cedocard)"
    ],
    "side_effects": "Hipotensi mendadak, sakit kepala berdenyut, takikardia refleks, pusing ortostatik.",
    "notes": "Jangan dikombinasi dengan PDE-5 inhibitor (sildenafil, tadalafil)."
  },
  "paracetamol": {
    "name": "Paracetamol (Asetaminofen)",
    "category": "Analgesik & Antipiretik Lini Pertama",
    "description": "Pereda nyeri dan penurun demam yang aman untuk sebagian besar populasi bila digunakan dalam batas dosis harian normal.",
    "common_brands": [
      "Panadol",
      "Tempra",
      "Sanmol",
      "Biogesic",
      "Pamol"
    ],
    "side_effects": "Hepatotoksisitas bila melebihi 4000 mg/hari atau dikonsumsi bersama alkohol.",
    "notes": "Dosis maksimal dewasa 4g/hari. Pilihan analgesik teraman untuk pasien dengan riwayat perdarahan lambung atau gagal ginjal."
  },
  "amoxicillin": {
    "name": "Amoxicillin",
    "category": "Antibiotik Penisilin Spektrum Luas",
    "description": "Antibiotik bakterisidal untuk infeksi saluran napas atas, infeksi gigi, telinga, dan infeksi saluran kemih.",
    "common_brands": [
      "Amoxil",
      "Yusimox",
      "Trimox",
      "Hiconcil"
    ],
    "side_effects": "Ruam kulit, diare, mual, reaksi anafilaksis pada pasien alergi penisilin.",
    "notes": "Pastikan riwayat alergi penisilin negatif sebelum diresepkan. Habiskan sesuai durasi terapi."
  },
  "levothyroxine": {
    "name": "Levothyroxine",
    "category": "Hormon Tiroid Sintetik (T4)",
    "description": "Terapi sulih hormon untuk pasien hipotiroidisme dan pasca-tiroidektomi.",
    "common_brands": [
      "Euthyrox",
      "Thyrax"
    ],
    "side_effects": "Palpitasi, tremor, insomnia, penurunan berat badan bila dosis berlebih.",
    "notes": "Diminum saat perut kosong di pagi hari, minimal 30\u201360 menit sebelum sarapan. Beri jarak 4 jam dari antasida atau suplemen besi/kalsium."
  },
  "alcohol": {
    "name": "Alkohol (Etanol)",
    "category": "Zat Psikoaktif / Pelarut",
    "description": "Etanol dalam minuman beralkohol yang mempengaruhi sistem saraf pusat dan metabolisme hepatik.",
    "common_brands": [
      "-"
    ],
    "side_effects": "Depresi sistem saraf pusat, hepatotoksisitas, gangguan koordinasi motorik.",
    "notes": "Banyak berinteraksi buruk dengan obat-obatan medis, terutama penekan SSP, antidiabetes, dan antikoagulan."
  },
  "ssri": {
    "name": "Golongan SSRI",
    "category": "Antidepresan Serotonergik",
    "description": "Kelas antidepresan selektif serotonin mencakup fluoxetine, sertraline, escitalopram, paroxetine, dan fluvoxamine.",
    "common_brands": [
      "Prozac",
      "Zoloft",
      "Lexapro",
      "Paxil"
    ],
    "side_effects": "Mual, disfungsi seksual, agitasi, risiko sindrom serotonin.",
    "notes": "Jangan digunakan bersamaan dengan MAOI atau tramadol dosis tinggi."
  },
  "maoi": {
    "name": "Golongan MAOI",
    "category": "Antidepresan Inhibitor Monoamin Oksidase",
    "description": "Antidepresan penghambat enzim MAO mencakup phenelzine, tranylcypromine, isocarboxazid, selegiline, dan moclobemide.",
    "common_brands": [
      "Nardil",
      "Parnate",
      "Marplan",
      "Jumex"
    ],
    "side_effects": "Krisis hipertensi (dengan makanan ber-tiramin), hipotensi ortostatik, insomnia berat.",
    "notes": "Kombinasi dengan obat serotonergik lain adalah KONTRAINDIKASI MUTLAK."
  }
};

// Install: cache static shell
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS).catch(() => {}))
  );
  self.skipWaiting();
});

// Activate: clean obsolete caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

function resolveDrug(raw) {
  let cleaned = (raw || '').trim().toLowerCase();
  if (SYNONYMS[cleaned]) cleaned = SYNONYMS[cleaned];
  if (BRAND_TO_GENERIC[cleaned]) cleaned = BRAND_TO_GENERIC[cleaned];
  const tags = new Set([cleaned]);
  if (DRUG_CLASSES[cleaned]) {
    for (const c of DRUG_CLASSES[cleaned]) tags.add(c);
  }
  return { raw: (raw || '').trim(), generic: cleaned, tags: tags };
}

function runOfflineCheck(body) {
  const rawDrugs = body.drugs || [];
  const patient = body.patient || {};
  const timings = body.timings || [];

  const resolved = rawDrugs.map(resolveDrug);
  const foundInteractions = [];
  const patientAdjustments = [];
  let totalScore = 0;
  let highestStatus = 'safe';

  for (const rule of OFFLINE_RULES) {
    const reqs = rule.drugs;
    let matchedInputs = null;

    if (reqs.length === 2) {
      const [r1, r2] = reqs;
      for (let i = 0; i < resolved.length; i++) {
        for (let j = 0; j < resolved.length; j++) {
          if (i !== j && resolved[i].tags.has(r1) && resolved[j].tags.has(r2)) {
            matchedInputs = [resolved[i], resolved[j]];
            break;
          }
        }
        if (matchedInputs) break;
      }
    }

    if (!matchedInputs) continue;

    let adjScore = rule.score;
    const adjNotes = [];
    const patRisk = rule.patient_risk || {};

    if (patient.elderly && patRisk.elderly) {
      adjScore += patRisk.elderly.score_add;
      adjNotes.push(patRisk.elderly.note);
    }
    if (patient.ckd && patRisk.ckd) {
      adjScore += patRisk.ckd.score_add;
      adjNotes.push(patRisk.ckd.note);
    }
    if (patient.liver && patRisk.liver) {
      adjScore += patRisk.liver.score_add;
      adjNotes.push(patRisk.liver.note);
    }
    if (patient.pregnant && patRisk.pregnant) {
      adjScore += patRisk.pregnant.score_add;
      adjNotes.push(patRisk.pregnant.note);
    }

    let effStatus = rule.status;
    if (adjScore >= 50) effStatus = 'critical';
    else if (adjScore >= 25 && effStatus === 'safe') effStatus = 'moderate';

    const d1 = matchedInputs[0].raw;
    const d2 = matchedInputs[1].raw;

    if (adjNotes.length > 0) {
      patientAdjustments.push({
        drugs: [d1, d2],
        original_level: rule.level,
        adjusted_score: Math.min(adjScore, 100),
        notes: adjNotes,
      });
    }

    foundInteractions.push({
      drugs: [d1, d2],
      generic_drugs: rule.drugs,
      level: effStatus === 'critical' ? 'Kritis' : rule.level,
      description: rule.description,
      alternatives: rule.alternatives || [],
      mechanism: rule.mechanism,
      mechanism_detail: rule.mechanism_detail,
      cyp: rule.cyp,
    });

    totalScore += adjScore;
    if (effStatus === 'critical') highestStatus = 'critical';
    else if (effStatus === 'moderate' && highestStatus !== 'critical') highestStatus = 'moderate';
  }

  const riskScore = Math.min(totalScore, 100);

  // Timing warnings
  const timingWarnings = [];
  if (timings && timings.length >= 2) {
    const timingRecords = timings.map(t => {
      const res = resolveDrug(t.drug);
      return { drug: t.drug, minutes: t.hour * 60 + t.minute, tags: res.tags };
    });

    for (const rule of OFFLINE_RULES) {
      if (!rule.timing_sensitive || !rule.timing_gap_hours) continue;
      const [r1, r2] = rule.drugs;
      for (let i = 0; i < timingRecords.length; i++) {
        for (let j = i + 1; j < timingRecords.length; j++) {
          const t1 = timingRecords[i], t2 = timingRecords[j];
          if ((t1.tags.has(r1) && t2.tags.has(r2)) || (t1.tags.has(r2) && t2.tags.has(r1))) {
            const diff = Math.abs(t1.minutes - t2.minutes);
            const actualGap = Math.min(diff, 1440 - diff);
            if (actualGap < rule.timing_gap_hours * 60) {
              timingWarnings.push({
                drugs: [t1.drug, t2.drug],
                gap_required_hours: rule.timing_gap_hours,
                gap_actual_minutes: actualGap,
                message: (rule.alternatives && rule.alternatives[0]) || 'Beri jeda waktu minum obat.',
              });
            }
          }
        }
      }
    }
  }

  let summary = 'Tidak ditemukan interaksi berbahaya yang diketahui pada kombinasi obat ini.';
  let level = 'Aman';
  let color = 'green';
  if (highestStatus === 'critical') {
    level = 'Kritis';
    color = 'red';
    summary = 'Ditemukan interaksi berbahaya! Risiko klinis tinggi, segera konsultasikan dengan apoteker atau dokter.';
  } else if (highestStatus === 'moderate') {
    level = 'Sedang';
    color = 'yellow';
    summary = 'Ditemukan interaksi yang memerlukan perhatian. Pemantauan klinis dan penyesuaian jadwal disarankan.';
  }

  return {
    status: highestStatus,
    level: level,
    color: color,
    interactions: foundInteractions,
    summary: summary,
    risk_score: riskScore,
    patient_adjustments: patientAdjustments.length ? patientAdjustments : null,
    timing_warnings: timingWarnings.length ? timingWarnings : null,
    offline: true,
  };
}

function getOfflineDrugCatalog() {
  const all_drugs = Array.from(new Set([
    ...Object.keys(DRUG_CATALOG),
    ...OFFLINE_RULES.flatMap(r => r.drugs),
    ...Object.keys(BRAND_TO_GENERIC),
    ...Object.keys(SYNONYMS)
  ])).sort();

  const pairs = OFFLINE_RULES.map(r => ({
    drugs: r.drugs,
    level: r.level,
    status: r.status,
    description: r.description,
    score: r.score,
    mechanism: r.mechanism,
    mechanism_detail: r.mechanism_detail,
    alternatives: r.alternatives || []
  }));

  return {
    drugs: all_drugs,
    pairs: pairs,
    catalog: DRUG_CATALOG
  };
}

function runOfflineIdentify(rawText) {
  const clean = (rawText || '').toLowerCase().replace(/[^a-z0-9\s-]/g, ' ');
  const tokens = clean.split(/\s+/).filter(t => t.length >= 3);
  const matched = {};

  for (const [brand, generic] of Object.entries(BRAND_TO_GENERIC)) {
    if (clean.includes(brand) || tokens.includes(brand)) {
      matched[generic] = `merek dagang: ${brand.charAt(0).toUpperCase() + brand.slice(1)}`;
    }
  }

  const allKnown = new Set([...Object.keys(DRUG_CATALOG), ...OFFLINE_RULES.flatMap(r => r.drugs)]);
  for (const generic of allKnown) {
    if (clean.includes(generic) || tokens.includes(generic)) {
      matched[generic] = `nama generik: ${generic.charAt(0).toUpperCase() + generic.slice(1)}`;
    }
  }

  for (const [syn, std] of Object.entries(SYNONYMS)) {
    if (clean.includes(syn) || tokens.includes(syn)) {
      const target = BRAND_TO_GENERIC[std] || std;
      matched[target] = `sinonim: ${syn.charAt(0).toUpperCase() + syn.slice(1)}`;
    }
  }

  const results = [];
  for (const [drug, via] of Object.entries(matched)) {
    const info = DRUG_CATALOG[drug] || {
      name: drug.charAt(0).toUpperCase() + drug.slice(1),
      category: 'Farmakologi Klinis',
      description: `Informasi obat klinis untuk ${drug}`,
      common_brands: ['-'],
      side_effects: 'Konsultasikan dengan apoteker.',
      notes: 'Terdaftar dalam basis data klinis.'
    };
    results.append ? results.push({
      drug: drug,
      info: info,
      has_interactions: OFFLINE_RULES.some(r => r.drugs.includes(drug)),
      matched_via: via
    }) : results.push({
      drug: drug,
      info: info,
      has_interactions: OFFLINE_RULES.some(r => r.drugs.includes(drug)),
      matched_via: via
    });
  }

  if (!results.length) {
    return { ok: false, message: 'Tidak ada obat yang dikenali dari teks ini.' };
  }
  return { ok: true, matched: results };
}

// Fetch listener: network-first for API, offline fallback with full engine parity
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // POST /api/check-drugs offline fallback
  if (url.pathname === '/api/check-drugs' && event.request.method === 'POST') {
    event.respondWith(
      fetch(event.request.clone()).catch(async () => {
        try {
          const body = await event.request.json();
          const result = runOfflineCheck(body);
          return new Response(JSON.stringify(result), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
          });
        } catch (e) {
          return new Response(JSON.stringify({ message: 'Offline error: ' + e.message }), { status: 503 });
        }
      })
    );
    return;
  }

  // POST /api/identify-drug offline fallback
  if (url.pathname === '/api/identify-drug' && event.request.method === 'POST') {
    event.respondWith(
      fetch(event.request.clone()).catch(async () => {
        try {
          const body = await event.request.json();
          const result = runOfflineIdentify(body.text || '');
          const status = result.ok ? 200 : 404;
          return new Response(JSON.stringify(result), {
            status: status,
            headers: { 'Content-Type': 'application/json' }
          });
        } catch (e) {
          return new Response(JSON.stringify({ ok: false, message: 'Offline error: ' + e.message }), { status: 503 });
        }
      })
    );
    return;
  }

  // GET /api/drugs offline fallback
  if (url.pathname === '/api/drugs' && event.request.method === 'GET') {
    event.respondWith(
      fetch(event.request.clone()).then(res => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE_NAME).then(c => c.put(event.request, copy)).catch(() => {});
        }
        return res;
      }).catch(async () => {
        const cached = await caches.match(event.request);
        if (cached) return cached;
        const offlineData = getOfflineDrugCatalog();
        return new Response(JSON.stringify(offlineData), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      })
    );
    return;
  }

  // GET /api/me offline fallback
  if (url.pathname === '/api/me' && event.request.method === 'GET') {
    event.respondWith(
      fetch(event.request).catch(() => {
        return new Response(JSON.stringify({ ok: true, username: 'Tamu (Offline)', is_guest: true }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      })
    );
    return;
  }

  // IMPORTANT: Never call caches.match on non-GET requests!
  if (event.request.method !== 'GET') {
    event.respondWith(fetch(event.request));
    return;
  }

  // HTML page navigation
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).then(response => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then(c => c.put(event.request, copy)).catch(() => {});
        return response;
      }).catch(() => caches.match('/'))
    );
    return;
  }

  // Regular GET assets
  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request))
  );
});
