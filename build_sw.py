import json
import main

# Prepare rules for JS JSON serialization
serialized_rules = []
for r in main.RULES:
    serialized_rules.append({
        "drugs": list(r["drugs"]),
        "status": r["status"],
        "level": r["level"],
        "color": r["color"],
        "score": r["score"],
        "mechanism": r.get("mechanism"),
        "mechanism_detail": r.get("mechanism_detail"),
        "cyp": r.get("cyp"),
        "alternatives": r.get("alternatives", []),
        "description": r["description"],
        "timing_sensitive": r.get("timing_sensitive", False),
        "timing_gap_hours": r.get("timing_gap_hours", 0),
        "patient_risk": r.get("patient_risk", {}),
    })

serialized_classes = {k: list(v) for k, v in main.DRUG_CLASSES.items()}

sw_content = f"""// Polypharmacy Detector - Clinical PWA Service Worker
const CACHE_NAME = 'polypharmacy-v3.0';

const STATIC_ASSETS = [
  '/',
  '/login',
  '/manifest.json',
  '/sw.js',
];

const BRAND_TO_GENERIC = {json.dumps(main.BRAND_TO_GENERIC, indent=2)};
const SYNONYMS = {json.dumps(main.SYNONYMS, indent=2)};
const DRUG_CLASSES = {json.dumps(serialized_classes, indent=2)};
const OFFLINE_RULES = {json.dumps(serialized_rules, indent=2)};
const DRUG_CATALOG = {json.dumps(main.DRUG_INFO, indent=2)};

// Install: cache static shell
self.addEventListener('install', event => {{
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS).catch(() => {{}}))
  );
  self.skipWaiting();
}});

// Activate: clean obsolete caches
self.addEventListener('activate', event => {{
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
}});

function resolveDrug(raw) {{
  let cleaned = (raw || '').trim().toLowerCase();
  if (SYNONYMS[cleaned]) cleaned = SYNONYMS[cleaned];
  if (BRAND_TO_GENERIC[cleaned]) cleaned = BRAND_TO_GENERIC[cleaned];
  const tags = new Set([cleaned]);
  if (DRUG_CLASSES[cleaned]) {{
    for (const c of DRUG_CLASSES[cleaned]) tags.add(c);
  }}
  return {{ raw: (raw || '').trim(), generic: cleaned, tags: tags }};
}}

function runOfflineCheck(body) {{
  const rawDrugs = body.drugs || [];
  const patient = body.patient || {{}};
  const timings = body.timings || [];

  const resolved = rawDrugs.map(resolveDrug);
  const foundInteractions = [];
  const patientAdjustments = [];
  let totalScore = 0;
  let highestStatus = 'safe';

  for (const rule of OFFLINE_RULES) {{
    const reqs = rule.drugs;
    let matchedInputs = null;

    if (reqs.length === 2) {{
      const [r1, r2] = reqs;
      for (let i = 0; i < resolved.length; i++) {{
        for (let j = 0; j < resolved.length; j++) {{
          if (i !== j && resolved[i].tags.has(r1) && resolved[j].tags.has(r2)) {{
            matchedInputs = [resolved[i], resolved[j]];
            break;
          }}
        }}
        if (matchedInputs) break;
      }}
    }}

    if (!matchedInputs) continue;

    let adjScore = rule.score;
    const adjNotes = [];
    const patRisk = rule.patient_risk || {{}};

    if (patient.elderly && patRisk.elderly) {{
      adjScore += patRisk.elderly.score_add;
      adjNotes.push(patRisk.elderly.note);
    }}
    if (patient.ckd && patRisk.ckd) {{
      adjScore += patRisk.ckd.score_add;
      adjNotes.push(patRisk.ckd.note);
    }}
    if (patient.liver && patRisk.liver) {{
      adjScore += patRisk.liver.score_add;
      adjNotes.push(patRisk.liver.note);
    }}
    if (patient.pregnant && patRisk.pregnant) {{
      adjScore += patRisk.pregnant.score_add;
      adjNotes.push(patRisk.pregnant.note);
    }}

    let effStatus = rule.status;
    if (adjScore >= 50) effStatus = 'critical';
    else if (adjScore >= 25 && effStatus === 'safe') effStatus = 'moderate';

    const d1 = matchedInputs[0].raw;
    const d2 = matchedInputs[1].raw;

    if (adjNotes.length > 0) {{
      patientAdjustments.push({{
        drugs: [d1, d2],
        original_level: rule.level,
        adjusted_score: Math.min(adjScore, 100),
        notes: adjNotes,
      }});
    }}

    foundInteractions.push({{
      drugs: [d1, d2],
      generic_drugs: rule.drugs,
      level: effStatus === 'critical' ? 'Kritis' : rule.level,
      description: rule.description,
      alternatives: rule.alternatives || [],
      mechanism: rule.mechanism,
      mechanism_detail: rule.mechanism_detail,
      cyp: rule.cyp,
    }});

    totalScore += adjScore;
    if (effStatus === 'critical') highestStatus = 'critical';
    else if (effStatus === 'moderate' && highestStatus !== 'critical') highestStatus = 'moderate';
  }}

  const riskScore = Math.min(totalScore, 100);

  // Timing warnings
  const timingWarnings = [];
  if (timings && timings.length >= 2) {{
    const timingRecords = timings.map(t => {{
      const res = resolveDrug(t.drug);
      return {{ drug: t.drug, minutes: t.hour * 60 + t.minute, tags: res.tags }};
    }});

    for (const rule of OFFLINE_RULES) {{
      if (!rule.timing_sensitive || !rule.timing_gap_hours) continue;
      const [r1, r2] = rule.drugs;
      for (let i = 0; i < timingRecords.length; i++) {{
        for (let j = i + 1; j < timingRecords.length; j++) {{
          const t1 = timingRecords[i], t2 = timingRecords[j];
          if ((t1.tags.has(r1) && t2.tags.has(r2)) || (t1.tags.has(r2) && t2.tags.has(r1))) {{
            const diff = Math.abs(t1.minutes - t2.minutes);
            const actualGap = Math.min(diff, 1440 - diff);
            if (actualGap < rule.timing_gap_hours * 60) {{
              timingWarnings.push({{
                drugs: [t1.drug, t2.drug],
                gap_required_hours: rule.timing_gap_hours,
                gap_actual_minutes: actualGap,
                message: (rule.alternatives && rule.alternatives[0]) || 'Beri jeda waktu minum obat.',
              }});
            }}
          }}
        }}
      }}
    }}
  }}

  let summary = 'Tidak ditemukan interaksi berbahaya yang diketahui pada kombinasi obat ini.';
  let level = 'Aman';
  let color = 'green';
  if (highestStatus === 'critical') {{
    level = 'Kritis';
    color = 'red';
    summary = 'Ditemukan interaksi berbahaya! Risiko klinis tinggi, segera konsultasikan dengan apoteker atau dokter.';
  }} else if (highestStatus === 'moderate') {{
    level = 'Sedang';
    color = 'yellow';
    summary = 'Ditemukan interaksi yang memerlukan perhatian. Pemantauan klinis dan penyesuaian jadwal disarankan.';
  }}

  return {{
    status: highestStatus,
    level: level,
    color: color,
    interactions: foundInteractions,
    summary: summary,
    risk_score: riskScore,
    patient_adjustments: patientAdjustments.length ? patientAdjustments : null,
    timing_warnings: timingWarnings.length ? timingWarnings : null,
    offline: true,
  }};
}}

function getOfflineDrugCatalog() {{
  const all_drugs = Array.from(new Set([
    ...Object.keys(DRUG_CATALOG),
    ...OFFLINE_RULES.flatMap(r => r.drugs),
    ...Object.keys(BRAND_TO_GENERIC),
    ...Object.keys(SYNONYMS)
  ])).sort();

  const pairs = OFFLINE_RULES.map(r => ({{
    drugs: r.drugs,
    level: r.level,
    status: r.status,
    description: r.description,
    score: r.score,
    mechanism: r.mechanism,
    mechanism_detail: r.mechanism_detail,
    alternatives: r.alternatives || []
  }}));

  return {{
    drugs: all_drugs,
    pairs: pairs,
    catalog: DRUG_CATALOG
  }};
}}

function runOfflineIdentify(rawText) {{
  const clean = (rawText || '').toLowerCase().replace(/[^a-z0-9\\s-]/g, ' ');
  const tokens = clean.split(/\\s+/).filter(t => t.length >= 3);
  const matched = {{}};

  for (const [brand, generic] of Object.entries(BRAND_TO_GENERIC)) {{
    if (clean.includes(brand) || tokens.includes(brand)) {{
      matched[generic] = `merek dagang: ${{brand.charAt(0).toUpperCase() + brand.slice(1)}}`;
    }}
  }}

  const allKnown = new Set([...Object.keys(DRUG_CATALOG), ...OFFLINE_RULES.flatMap(r => r.drugs)]);
  for (const generic of allKnown) {{
    if (clean.includes(generic) || tokens.includes(generic)) {{
      matched[generic] = `nama generik: ${{generic.charAt(0).toUpperCase() + generic.slice(1)}}`;
    }}
  }}

  for (const [syn, std] of Object.entries(SYNONYMS)) {{
    if (clean.includes(syn) || tokens.includes(syn)) {{
      const target = BRAND_TO_GENERIC[std] || std;
      matched[target] = `sinonim: ${{syn.charAt(0).toUpperCase() + syn.slice(1)}}`;
    }}
  }}

  const results = [];
  for (const [drug, via] of Object.entries(matched)) {{
    const info = DRUG_CATALOG[drug] || {{
      name: drug.charAt(0).toUpperCase() + drug.slice(1),
      category: 'Farmakologi Klinis',
      description: `Informasi obat klinis untuk ${{drug}}`,
      common_brands: ['-'],
      side_effects: 'Konsultasikan dengan apoteker.',
      notes: 'Terdaftar dalam basis data klinis.'
    }};
    results.append ? results.push({{
      drug: drug,
      info: info,
      has_interactions: OFFLINE_RULES.some(r => r.drugs.includes(drug)),
      matched_via: via
    }}) : results.push({{
      drug: drug,
      info: info,
      has_interactions: OFFLINE_RULES.some(r => r.drugs.includes(drug)),
      matched_via: via
    }});
  }}

  if (!results.length) {{
    return {{ ok: false, message: 'Tidak ada obat yang dikenali dari teks ini.' }};
  }}
  return {{ ok: true, matched: results }};
}}

// Fetch listener: network-first for API, offline fallback with full engine parity
self.addEventListener('fetch', event => {{
  const url = new URL(event.request.url);

  // POST /api/check-drugs offline fallback
  if (url.pathname === '/api/check-drugs' && event.request.method === 'POST') {{
    event.respondWith(
      fetch(event.request.clone()).catch(async () => {{
        try {{
          const body = await event.request.json();
          const result = runOfflineCheck(body);
          return new Response(JSON.stringify(result), {{
            status: 200,
            headers: {{ 'Content-Type': 'application/json' }}
          }});
        }} catch (e) {{
          return new Response(JSON.stringify({{ message: 'Offline error: ' + e.message }}), {{ status: 503 }});
        }}
      }})
    );
    return;
  }}

  // POST /api/identify-drug offline fallback
  if (url.pathname === '/api/identify-drug' && event.request.method === 'POST') {{
    event.respondWith(
      fetch(event.request.clone()).catch(async () => {{
        try {{
          const body = await event.request.json();
          const result = runOfflineIdentify(body.text || '');
          const status = result.ok ? 200 : 404;
          return new Response(JSON.stringify(result), {{
            status: status,
            headers: {{ 'Content-Type': 'application/json' }}
          }});
        }} catch (e) {{
          return new Response(JSON.stringify({{ ok: false, message: 'Offline error: ' + e.message }}), {{ status: 503 }});
        }}
      }})
    );
    return;
  }}

  // GET /api/drugs offline fallback
  if (url.pathname === '/api/drugs' && event.request.method === 'GET') {{
    event.respondWith(
      fetch(event.request.clone()).then(res => {{
        if (res.ok) {{
          const copy = res.clone();
          caches.open(CACHE_NAME).then(c => c.put(event.request, copy)).catch(() => {{}});
        }}
        return res;
      }}).catch(async () => {{
        const cached = await caches.match(event.request);
        if (cached) return cached;
        const offlineData = getOfflineDrugCatalog();
        return new Response(JSON.stringify(offlineData), {{
          status: 200,
          headers: {{ 'Content-Type': 'application/json' }}
        }});
      }})
    );
    return;
  }}

  // GET /api/me offline fallback
  if (url.pathname === '/api/me' && event.request.method === 'GET') {{
    event.respondWith(
      fetch(event.request).catch(() => {{
        return new Response(JSON.stringify({{ ok: true, username: 'Tamu (Offline)', is_guest: true }}), {{
          status: 200,
          headers: {{ 'Content-Type': 'application/json' }}
        }});
      }})
    );
    return;
  }}

  // IMPORTANT: Never call caches.match on non-GET requests!
  if (event.request.method !== 'GET') {{
    event.respondWith(fetch(event.request));
    return;
  }}

  // HTML page navigation
  if (event.request.mode === 'navigate') {{
    event.respondWith(
      fetch(event.request).then(response => {{
        const copy = response.clone();
        caches.open(CACHE_NAME).then(c => c.put(event.request, copy)).catch(() => {{}});
        return response;
      }}).catch(() => caches.match('/'))
    );
    return;
  }}

  // Regular GET assets
  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request))
  );
}});
"""

with open("sw.js", "w", encoding="utf-8") as f:
    f.write(sw_content)

print("sw.js updated successfully with full rule parity!")
