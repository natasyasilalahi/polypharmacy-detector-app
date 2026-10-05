const CACHE_NAME = 'polypharmacy-v2';
const OFFLINE_DRUG_RULES = [
  { drugs: ['warfarin', 'ibuprofen'], status: 'critical', level: 'Kritis', score: 40, description: 'Warfarin + Ibuprofen: Meningkatkan risiko perdarahan serius (GI bleeding, intrakranial). Gunakan parasetamol sebagai alternatif.' },
  { drugs: ['warfarin', 'aspirin'], status: 'critical', level: 'Kritis', score: 45, description: 'Warfarin + Aspirin: Kombinasi dua antikoagulan sangat meningkatkan risiko perdarahan berat.' },
  { drugs: ['metformin', 'alcohol'], status: 'critical', level: 'Kritis', score: 42, description: 'Metformin + Alkohol: Meningkatkan risiko asidosis laktat yang berpotensi mengancam jiwa.' },
  { drugs: ['ssri', 'maoi'], status: 'critical', level: 'Kritis', score: 50, description: 'SSRI + MAOI: Dapat menyebabkan sindrom serotonin mengancam jiwa.' },
  { drugs: ['simvastatin', 'amiodarone'], status: 'critical', level: 'Kritis', score: 40, description: 'Simvastatin + Amiodarone: Meningkatkan risiko miopati dan rabdomiolisis.' },
  { drugs: ['digoxin', 'amiodarone'], status: 'critical', level: 'Kritis', score: 45, description: 'Digoxin + Amiodarone: Meningkatkan kadar digoxin 2× lipat, risiko toksisitas.' },
  { drugs: ['lisinopril', 'potassium'], status: 'moderate', level: 'Sedang', score: 20, description: 'Lisinopril + Potassium: Dapat menyebabkan hiperkalemia.' },
  { drugs: ['metformin', 'ibuprofen'], status: 'moderate', level: 'Sedang', score: 22, description: 'Metformin + Ibuprofen: NSAID dapat menurunkan fungsi ginjal dan mengurangi ekskresi metformin.' },
  { drugs: ['ciprofloxacin', 'antacid'], status: 'moderate', level: 'Sedang', score: 18, description: 'Ciprofloxacin + Antasida: Antasida menurunkan penyerapan ciprofloxacin hingga 90%.' },
  { drugs: ['amlodipine', 'simvastatin'], status: 'moderate', level: 'Sedang', score: 20, description: 'Amlodipine + Simvastatin: Meningkatkan konsentrasi plasma simvastatin.' },
  { drugs: ['fluoxetine', 'tramadol'], status: 'moderate', level: 'Sedang', score: 25, description: 'Fluoxetine + Tramadol: Risiko sindrom serotonin ringan hingga sedang.' },
  { drugs: ['spironolactone', 'potassium'], status: 'moderate', level: 'Sedang', score: 18, description: 'Spironolactone + Potassium: Dapat menyebabkan hiperkalemia.' },
];

const STATIC_ASSETS = [
  '/',
  '/login',
  '/manifest.json',
];

// Install: cache static assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS).catch(() => {}))
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: network-first for API, offline fallback for check-drugs
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Offline drug check fallback
  if (url.pathname === '/api/check-drugs' && event.request.method === 'POST') {
    event.respondWith(
      fetch(event.request.clone()).catch(async () => {
        // Network failed — run offline check
        try {
          const body = await event.request.json();
          const drugSet = new Set((body.drugs || []).map(d => d.trim().toLowerCase()));
          const found = [];
          let highest = 'safe';
          let total = 0;

          for (const rule of OFFLINE_DRUG_RULES) {
            if (rule.drugs.every(d => drugSet.has(d))) {
              found.push({ drugs: rule.drugs, level: rule.level, description: rule.description, alternatives: [] });
              total += rule.score;
              if (rule.status === 'critical') highest = 'critical';
              else if (rule.status === 'moderate' && highest !== 'critical') highest = 'moderate';
            }
          }

          const risk_score = Math.min(total, 100);
          const result = {
            status: highest,
            level: highest === 'critical' ? 'Kritis' : highest === 'moderate' ? 'Sedang' : 'Aman',
            color: highest === 'critical' ? 'red' : highest === 'moderate' ? 'yellow' : 'green',
            interactions: found,
            summary: highest === 'critical'
              ? '⚠️ [OFFLINE] Interaksi berbahaya ditemukan!'
              : highest === 'moderate'
              ? '⚠️ [OFFLINE] Interaksi sedang ditemukan.'
              : '✅ [OFFLINE] Tidak ada interaksi diketahui.',
            risk_score,
            offline: true,
          };

          return new Response(JSON.stringify(result), {
            status: 200,
            headers: { 'Content-Type': 'application/json' }
          });
        } catch {
          return new Response(JSON.stringify({ message: 'Offline' }), { status: 503 });
        }
      })
    );
    return;
  }

  // For HTML pages: network first, cache fallback
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => caches.match('/'))
    );
    return;
  }

  // For other assets: cache first
  event.respondWith(
    caches.match(event.request).then(cached => cached || fetch(event.request))
  );
});
