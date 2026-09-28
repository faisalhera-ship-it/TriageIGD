import io
import urllib.parse
from datetime import datetime
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="Triage IGD - Puskesmas Tirta Jaya",
    page_icon="🏥",
    layout="wide"
)

# Header Aplikasi
st.title("🏥 Sistem Triage & Screening IGD")
st.subheader("Puskesmas Tirta Jaya")
st.markdown("---")

# Inisialisasi Session State
if "daftar_triage" not in st.session_state:
    st.session_state.daftar_triage = []

if "pasien_terakhir" not in st.session_state:
    st.session_state.pasien_terakhir = None

# Sidebar - Form Input Pasien
st.sidebar.header("📋 Form Screening Pasien")

with st.sidebar.form("form_triage", clear_on_submit=False):
    nama = st.text_input("Nama Pasien")
    umur = st.number_input("Umur (Tahun)", min_value=0, max_value=120, value=25)
    gender = st.selectbox("Jenis Kelamin", ["Laki-laki", "Perempuan"])
    
    st.markdown("---")
    jenis_kasus = st.radio("Kategori Kasus", ["Non-Trauma", "Trauma"], horizontal=True)
    
    st.markdown("---")
    st.write("**Pemeriksaan Tanda Vital & Gejala Klinis**")
    
    kesadaran = st.selectbox("Tingkat Kesadaran", [
        "Compos Mentis (Sadar Penuh)", 
        "Apatis / Somnolen (Mengantuk / Respon Suara)", 
        "Sopor / Koma (Tidak Sadar / Respon Nyeri/Tidak Ada)"
    ])
    
    jalan_napas = st.selectbox("Jalan Napas (Airway)", [
        "Paten / Normal",
        "Sumbatan Parsial (Gurgling/Stridor)",
        "Sumbatan Total / Henti Napas"
    ])
    
    sistol = st.number_input("Sistol (mmHg)", value=120)
    diastol = st.number_input("Diastol (mmHg)", value=80)
    spo2 = st.number_input("Saturasi Oksigen / SpO2 (%)", value=98)
    nyeri = st.slider("Skala Nyeri (0 - 10)", 0, 10, 0)
    
    st.markdown("---")
    st.write("**Kondisi Khusus & Red Flags**")
    
    sesak_napas = st.checkbox("Pasien Mengalami Sesak Napas")
    
    organ_target = st.checkbox("Ada Kerusakan Organ Target (Nyeri Dada Hebat / Stroke Akut / Pandangan Kabur Mendadak)")
    
    syok_or_tik = st.checkbox("Ada Tanda Syok (Akral Dingin, Nadi Lemah/Cepat) ATAU Tanda Peningkatan TIK (Muntah Menyembur, Pupil Anisokor)")
    
    if jenis_kasus == "Trauma":
        kondisi_spesifik = st.selectbox("Tingkat Keparahan Trauma", [
            "Trauma Sedang / Ringan (Patah Tulang Tertutup, Dislokasi, Perdarahan Terkontrol)",
            "Trauma Berat (Perdarahan Masif, Trauma Kepala Berat, Patah Tulang Terbuka, Amputasi, Luka Bakar Luas)"
        ])
    else:
        kondisi_spesifik = st.selectbox("Kondisi Klinis Non-Trauma", [
            "Keluhan Ringan / Stabil",
            "Keluhan Sedang (Demam Tinggi, Nyeri Sedang, Vomiting)",
            "Kondisi Kritis (Henti Jantung, Kejang Berulang, Unstable)"
        ])
    
    keluhan_utama = st.text_area("Keluhan Utama / Catatan Klinis")
    
    submit_btn = st.form_submit_button("Simpan & Tentukan Kategori")

# Logika Determinasi Triage Berdasarkan Aturan Khusus
def tentukan_triage(jenis_kasus, kesadaran, jalan_napas, sistol, diastol, spo2, sesak_napas, organ_target, syok_or_tik, kondisi_spesifik):
    
    # 1. KRITERIA MERAH (Resusitasi / Immediate)
    if (
        sesak_napas or 
        syok_or_tik or 
        (sistol > 170 and diastol > 90 and organ_target) or 
        "Koma" in kesadaran or 
        "Sumbatan Total" in jalan_napas or 
        spo2 < 88 or 
        sistol < 80 or 
        (jenis_kasus == "Trauma" and "Trauma Berat" in kondisi_spesifik)
    ):
        return "MERAH (Gawat Darurat / Immediate)", "🔴", "Priority 1 - Segera Masuk Ruang Resusitasi", "#FFD2D2"
    
    # 2. KRITERIA KUNING (Emergensi / Urgent)
    elif (
        jenis_kasus == "Trauma" or 
        (sistol > 170 and diastol > 90 and not organ_target) or 
        (sistol > 140 or sistol < 90 or spo2 < 95) or 
        "Somnolen" in kesadaran or 
        "Parsial" in jalan_napas or 
        "Keluhan Sedang" in kondisi_spesifik
    ):
        return "KUNING (Emergensi / Urgent)", "🟡", "Priority 2 - Penanganan < 15 Menit", "#FFF3CD"
    
    # 3. KRITERIA HIJAU (Non-Emergensi / Normal)
    else:
        return "HIJAU (Non-Emergensi / Normal)", "🟢", "Priority 3 - Poliklinik / Rawat Jalan", "#D4EDDA"

# Fungsi untuk Membentuk URL Google Form Pre-fill
def build_google_form_url(pt):
    base_url = "https://docs.google.com/forms/d/e/1FAIpQLSdQnkh0fPuAESftoiFKNY6ZiMsCz7HEgddMktFn3cU2ObnHow/viewform"
    
    params = {
        "usp": "pp_url",
        "entry.1527605882": pt["Nama"],
        "entry.227822657": str(pt["Umur"]),
        "entry.687964026": pt["JK"],
        "entry.1182390189": pt["Kasus"],
        "entry.1889333283": pt["TD"],
        "entry.1397973064": pt["SpO2"],
        "entry.1677807563": pt["Kesadaran"],
        "entry.934574142": pt["Kategori Triage"],
        "entry.1332083877": pt["Instruksi"],
        "entry.476498570": pt["Keluhan"]
    }
    
    return f"{base_url}?{urllib.parse.urlencode(params)}"

if submit_btn:
    if not nama:
        st.sidebar.error("Nama pasien harus diisi!")
    else:
        kategori, emoji, instruksi, bg_color = tentukan_triage(
            jenis_kasus, kesadaran, jalan_napas, sistol, diastol, spo2, 
            sesak_napas, organ_target, syok_or_tik, kondisi_spesifik
        )
        waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        pasien_data = {
            "Waktu": waktu,
            "Nama": nama,
            "Umur": umur,
            "JK": gender,
            "Kasus": jenis_kasus,
            "Detail Kondisi": kondisi_spesifik,
            "Kesadaran": kesadaran,
            "Airway": jalan_napas,
            "SpO2": f"{spo2}%",
            "TD": f"{sistol}/{diastol} mmHg",
            "Nyeri": nyeri,
            "Kategori Triage": f"{emoji} {kategori}",
            "Instruksi": instruksi,
            "Keluhan": keluhan_utama,
            "BgColor": bg_color
        }
        
        st.session_state.daftar_triage.insert(0, pasien_data)
        st.session_state.pasien_terakhir = pasien_data
        st.sidebar.success(f"Pasien {nama} ({jenis_kasus}) berhasil diproses!")

# Tampilan Utama
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📊 Rekapitulasi Pasien")
    if st.session_state.daftar_triage:
        df = pd.DataFrame(st.session_state.daftar_triage)
        merah = df['Kategori Triage'].str.contains('MERAH').sum()
        kuning = df['Kategori Triage'].str.contains('KUNING').sum()
        hijau = df['Kategori Triage'].str.contains('HIJAU').sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("🔴 Merah", merah)
        c2.metric("🟡 Kuning", kuning)
        c3.metric("🟢 Hijau", hijau)
        
        st.markdown("---")
        st.subheader("📝 Kirim Data ke Google Form")
        if st.session_state.pasien_terakhir:
            pt = st.session_state.pasien_terakhir
            gform_url = build_google_form_url(pt)
            
            st.link_button(
                label="📤 Submit Pasien Terakhir ke Google Form",
                url=gform_url,
                type="primary",
                use_container_width=True
            )
            st.caption("Data pasien terakhir akan otomatis terisi ke dalam Google Form Puskesmas Tirta Jaya.")
    else:
        st.info("Belum ada data pasien.")

    st.markdown("---")
    st.subheader("🖨️ Cetak Lembar Triage")
    if st.session_state.pasien_terakhir:
        pt = st.session_state.pasien_terakhir
        st.write(f"**Pasien:** {pt['Nama']} ({pt['Kasus']} - {pt['Kategori Triage']})")
        
        html_print = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 15px; background-color: {pt['BgColor']}; }}
                .card {{ border: 2px solid #333; padding: 15px; border-radius: 8px; background: #fff; }}
                h2 {{ margin-top: 0; text-align: center; color: #1F4E78; border-bottom: 2px solid #1F4E78; padding-bottom: 5px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                td {{ padding: 6px; border-bottom: 1px solid #ddd; font-size: 14px; }}
                .badge {{ font-size: 16px; font-weight: bold; padding: 6px; text-align: center; display: block; border-radius: 4px; background-color: {pt['BgColor']}; }}
                .btn-print {{ background-color: #007BFF; color: white; padding: 10px 18px; border: none; border-radius: 5px; font-size: 14px; cursor: pointer; width: 100%; margin-top: 10px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>LEMBAR TRIAGE IGD - PUSKESMAS TIRTA JAYA</h2>
                <div class="badge">{pt['Kategori Triage']}</div>
                <table>
                    <tr><td><b>Waktu Registrasi</b></td><td>{pt['Waktu']}</td></tr>
                    <tr><td><b>Nama Pasien</b></td><td>{pt['Nama']}</td></tr>
                    <tr><td><b>Umur / Gender</b></td><td>{pt['Umur']} Tahun / {pt['JK']}</td></tr>
                    <tr><td><b>Jenis Kasus</b></td><td><b>{pt['Kasus']}</b> ({pt['Detail Kondisi']})</td></tr>
                    <tr><td><b>Tingkat Kesadaran</b></td><td>{pt['Kesadaran']}</td></tr>
                    <tr><td><b>Jalan Napas (Airway)</b></td><td>{pt['Airway']}</td></tr>
                    <tr><td><b>Tanda Vital</b></td><td>SpO2: {pt['SpO2']} | TD: {pt['TD']} | Nyeri: {pt['Nyeri']}/10</td></tr>
                    <tr><td><b>Instruksi Tindakan</b></td><td><b>{pt['Instruksi']}</b></td></tr>
                    <tr><td><b>Keluhan Utama</b></td><td>{pt['Keluhan']}</td></tr>
                </table>
            </div>
            <button class="btn-print" onclick="window.print()">🖨️ Cetak / Simpan PDF Lembar Ini</button>
        </body>
        </html>
        """
        components.html(html_print, height=450, scrolling=True)
    else:
        st.caption("Submit pasien terlebih dahulu untuk mencetak lembar triage.")

with col2:
    st.subheader("📋 Daftar Antrean & Status Triage IGD")
    if st.session_state.daftar_triage:
        df_display = pd.DataFrame(st.session_state.daftar_triage)
        cols_to_show = ['Waktu', 'Nama', 'Umur', 'Kasus', 'Kategori Triage', 'Instruksi', 'Keluhan']
        st.dataframe(df_display[cols_to_show], use_container_width=True, height=500)
    else:
        st.write("Silakan isi form di sebelah kiri untuk melakukan screening pasien baru.")
