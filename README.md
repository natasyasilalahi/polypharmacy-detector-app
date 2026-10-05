# 💊 Polypharmacy Collision Detector

> Deteksi interaksi obat berbahaya secara instan untuk apoteker dan dokter.

🔗 **Live App:** [https://web-production-47daa.up.railway.app](https://web-production-47daa.up.railway.app)

---

## ✨ Fitur

- 🚨 **Deteksi Interaksi** — 12+ pasangan interaksi obat dengan 3 level risiko (Kritis, Sedang, Aman)
- 🏥 **Profil Pasien Khusus** — penyesuaian risiko otomatis untuk Lansia, CKD, Gangguan Hati, Hamil
- ⏱️ **Drug Timing Checker** — peringatan jarak waktu minum obat yang sensitif
- 📷 **Scan Kemasan** — OCR via kamera/upload foto, support nama merek → generik (46 mapping)
- 🔗 **Share Hasil** — bagikan hasil analisis via link pendek
- 📝 **Catatan Apoteker** — tambah catatan klinis di setiap riwayat
- 📈 **Trend Chart** — grafik skor risiko dari waktu ke waktu
- ⚗️ **Mekanisme Visual** — diagram alur farmakokinetik/farmakodinamik tiap interaksi
- 📱 **PWA + Offline Mode** — bisa diinstall & dipakai tanpa internet
- 📊 **Risk Score Meter** — skor risiko 0–100 dengan gauge visual
- 🕸️ **Graf Interaksi** — visualisasi jaringan hubungan antar obat
- 🖨️ **Export PDF** — cetak laporan langsung dari browser

## 🛠️ Tech Stack

- **Backend:** Python · FastAPI · Uvicorn
- **Frontend:** Vanilla JS · Tailwind CSS · Tesseract.js (OCR)
- **Deploy:** Railway

## 🚀 Jalankan Lokal

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Buka `http://localhost:8000`

## ⚠️ Disclaimer

Aplikasi ini adalah prototipe hackathon dan tidak dimaksudkan sebagai pengganti penilaian klinis profesional. Selalu konsultasikan dengan apoteker atau dokter berlisensi.

---

🏆 Hackathon 2025 · Clinical AI Prototype
