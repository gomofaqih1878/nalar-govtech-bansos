import os
import streamlit as st
import pandas as pd
import numpy as np
import random
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import lime
import lime.lime_tabular
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile
from datetime import datetime

# --- 0. AUTO-GENERATE DATASET ---
if not os.path.exists('dataset_sintetik_bansos.csv'):
    np.random.seed(42)
    random.seed(42)
    n_samples = 1500
    pekerjaan_list = ['Tidak Bekerja', 'Buruh Harian', 'Petani/Nelayan', 'Wiraswasta Kecil', 'Karyawan Swasta', 'PNS/TNI/POLRI']
    
    data = []
    for i in range(n_samples):
        nik = f"3673{random.randint(100000000000, 999999999999)}"
        pekerjaan = random.choice(pekerjaan_list)
        
        if pekerjaan in ['Tidak Bekerja', 'Buruh Harian']:
            pendapatan = random.randint(500000, 2000000)
        elif pekerjaan in ['Petani/Nelayan', 'Wiraswasta Kecil']:
            pendapatan = random.randint(1000000, 4000000)
        else:
            pendapatan = random.randint(3000000, 15000000)
            
        tanggungan = random.randint(1, 7)
        
        if pendapatan < 2000000:
            rumah = random.choice(['Tidak Permanen', 'Semi Permanen'])
            listrik = random.choice([450, 900])
        elif pendapatan < 5000000:
            rumah = random.choice(['Semi Permanen', 'Permanen Layak'])
            listrik = random.choice([900, 1300])
        else:
            rumah = random.choice(['Permanen Layak', 'Permanen Mewah'])
            listrik = random.choice([1300, 2200, 3500])
            
        score = 0
        if pendapatan <= 2500000: score += 3
        if rumah in ['Tidak Permanen', 'Semi Permanen']: score += 2
        if tanggungan >= 4: score += 1
        if listrik <= 900: score += 2
        
        if pekerjaan in ['PNS/TNI/POLRI']: score -= 100 
        if listrik >= 1300: score -= 50 
        
        status = 1 if score >= 5 else 0
        data.append([nik, pekerjaan, pendapatan, tanggungan, rumah, listrik, status])
        
    df_bansos = pd.DataFrame(data, columns=['NIK_Keluarga', 'Pekerjaan_Kepala_Keluarga', 'Pendapatan_Bln_Rp', 'Jml_Tanggungan', 'Kondisi_Rumah', 'Daya_Listrik_VA', 'Status_Layak_Bansos'])
    df_bansos.to_csv('dataset_sintetik_bansos.csv', index=False)


# --- 1. KONFIGURASI HALAMAN & UI MODERN ---
st.set_page_config(page_title="GovTech AI | NALAR", layout="wide", initial_sidebar_state="expanded", page_icon="🏛️")

# Injeksi CSS Super Modern
st.markdown("""
<style>
    /* Mengimpor font Plus Jakarta Sans dari Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* Menerapkan font ke seluruh elemen */
    html, body, [class*="css"], * {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* Warna latar belakang aplikasi yang lebih lembut */
    .stApp {
        background-color: #f1f5f9;
    }

    /* Mengganti desain tombol utama menjadi gradasi dan memberikan animasi hover */
    div.stButton > button {
        border-radius: 12px;
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
        color: white;
        border: none;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        box-shadow: 0 4px 10px rgba(59, 130, 246, 0.3);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    div.stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 15px rgba(59, 130, 246, 0.4);
        color: white;
    }

    /* Memperhalus tampilan kotak container (border=True) menjadi kartu modern */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 16px !important;
        border: 1px solid #e2e8f0 !important;
        background-color: #ffffff !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03) !important;
        padding: 1.5rem !important;
    }

    /* Desain untuk angka metrik hasil analisis */
    [data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        color: #0f172a !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 1rem !important;
        font-weight: 600 !important;
        color: #64748b !important;
    }

    /* Mempercantik kotak input teks dan dropdown */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input, .stTextArea textarea {
        border-radius: 10px !important;
        border: 1px solid #cbd5e1 !important;
        background-color: #f8fafc !important;
        transition: all 0.2s ease;
    }
    .stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus-within, .stTextArea textarea:focus {
        border-color: #3b82f6 !important;
        background-color: #ffffff !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) !important;
    }

    /* Gaya sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)


# --- 2. SISTEM LOGIN SEDERHANA ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.container(border=True): 
            st.markdown("""
                <div style='text-align: center; padding-bottom: 20px;'>
                    <div style='font-size: 3.5rem; margin-bottom: -15px;'>🏛️</div>
                    <h1 style='color: #1e40af; font-weight: 800; font-size: 2.5rem; margin-bottom: 0;'>NALAR</h1>
                    <p style='color: #64748b; font-weight: 500; font-size: 1.1rem;'>Portal Analitik Penetapan Bantuan Sosial</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.info("ℹ️ Gunakan Username: **admin** | Password: **admin123**")
            username = st.text_input("Username / NIP Operator", placeholder="Masukkan NIP Anda")
            password = st.text_input("Kata Sandi", type="password", placeholder="••••••••")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Masuk ke Dasbor Utama", type="primary", use_container_width=True):
                if username == "admin" and password == "admin123":
                    st.session_state['logged_in'] = True
                    st.rerun()
                else:
                    st.error("🚨 Kredensial tidak valid. Silakan periksa kembali.")
    st.stop()


# --- 3. FUNGSI CACHE DATA & MODEL ---
@st.cache_resource
def load_data_and_model():
    df = pd.read_csv('dataset_sintetik_bansos.csv')
    le_pekerjaan = LabelEncoder()
    df['Pekerjaan_KK_Enc'] = le_pekerjaan.fit_transform(df['Pekerjaan_Kepala_Keluarga'])
    le_rumah = LabelEncoder()
    df['Kondisi_Rumah_Enc'] = le_rumah.fit_transform(df['Kondisi_Rumah'])
    features = ['Pekerjaan_KK_Enc', 'Pendapatan_Bln_Rp', 'Jml_Tanggungan', 'Kondisi_Rumah_Enc', 'Daya_Listrik_VA']
    X = df[features]
    y = df['Status_Layak_Bansos']
    
    model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=5)
    model.fit(X.values, y)
    
    explainer = lime.lime_tabular.LimeTabularExplainer(
        training_data=X.values, feature_names=['Pekerjaan', 'Pendapatan', 'Tanggungan', 'Kondisi Rumah', 'Daya Listrik'],
        class_names=['Tidak Layak', 'Layak'], mode='classification'
    )
    return model, explainer, le_pekerjaan, le_rumah, features, df

try:
    model, explainer, le_pekerjaan, le_rumah, feature_cols, df_master = load_data_and_model()
except Exception as e:
    st.error(f"Gagal memuat data awal: {e}")
    st.stop()


# --- 4. FUNGSI NLP & PDF ---
def klasifikasi_sentimen(teks):
    teks = teks.lower()
    if any(k in teks for k in ['kecewa', 'marah', 'buruk', 'gagal', 'palsu', 'bohong', 'protes', 'miskin']):
        return "🔴 Negatif (Risiko Konflik Tinggi)"
    elif any(k in teks for k in ['mohon', 'tolong', 'harap', 'tanya']):
        return "🟢 Koperatif (Butuh Literasi)"
    return "⚪ Netral (Input Standar)"

def create_pdf(nama_petugas, nik, nama_warga, pekerjaan, pendapatan, tanggungan, rumah, listrik, hasil, sentimen):
    sentimen_bersih = sentimen.replace("🔴 ", "").replace("🟢 ", "").replace("⚪ ", "")
    tanggal_cetak = datetime.now().strftime("%d %B %Y %H:%M WIB")
    
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", size=14, style='B')
    pdf.cell(200, 8, txt="PEMERINTAH REPUBLIK INDONESIA", ln=True, align='C')
    pdf.set_font("Arial", size=12, style='B')
    pdf.cell(200, 6, txt="KEMENTERIAN SOSIAL / DINAS SOSIAL DAERAH", ln=True, align='C')
    pdf.set_font("Arial", size=9)
    pdf.cell(200, 5, txt="Sistem Informasi Kesejahteraan Sosial Berbasis AI (NALAR)", ln=True, align='C')
    pdf.line(10, 30, 200, 30)
    
    pdf.ln(2)
    pdf.set_font("Arial", size=8, style='I')
    pdf.cell(200, 4, txt="Mengingat: 1. UU No. 13 Tahun 2011 | 2. Kepmensos No. 262/HUK/2022 | 3. 14 Kriteria Kemiskinan BPS", ln=True, align='C')
    pdf.line(10, 36, 200, 36)
    
    pdf.ln(8)
    pdf.set_font("Arial", size=12, style='B')
    pdf.cell(200, 8, txt="SURAT KETERANGAN HASIL VERIFIKASI ALGORTIMIK", ln=True, align='C')
    
    pdf.ln(5)
    pdf.set_font("Arial", size=11, style='B')
    pdf.cell(200, 8, txt="A. IDENTITAS PEMOHON", ln=True, align='L')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 6, txt=f"1. Nomor Induk Kependudukan (NIK) : {nik}", ln=True, align='L')
    pdf.cell(200, 6, txt=f"2. Nama Kepala Keluarga           : {nama_warga}", ln=True, align='L')
    
    pdf.ln(5)
    pdf.set_font("Arial", size=11, style='B')
    pdf.cell(200, 8, txt="B. PARAMETER SOSIO-EKONOMI", ln=True, align='L')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 6, txt=f"1. Pekerjaan Utama                : {pekerjaan}", ln=True, align='L')
    pdf.cell(200, 6, txt=f"2. Penghasilan Bulanan            : Rp {pendapatan:,}", ln=True, align='L')
    pdf.cell(200, 6, txt=f"3. Jumlah Tanggungan Keluarga     : {tanggungan} Jiwa", ln=True, align='L')
    pdf.cell(200, 6, txt=f"4. Status Kepemilikan Rumah       : {rumah}", ln=True, align='L')
    pdf.cell(200, 6, txt=f"5. Daya Listrik Terpasang         : {listrik} VA", ln=True, align='L')
    
    pdf.ln(5)
    pdf.set_font("Arial", size=11, style='B')
    pdf.cell(200, 8, txt="C. KEPUTUSAN KECERDASAN BUATAN", ln=True, align='L')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 6, txt=f"Status Kelayakan Bantuan Sosial   : {hasil}", ln=True, align='L')
    
    pdf.ln(10)
    pdf.set_font("Arial", size=9, style='I')
    teks_penutup = (
        f"Dokumen ini dicetak pada {tanggal_cetak} oleh sistem NALAR. "
        "Keputusan diambil secara otomatis menggunakan model AI berdasarkan regulasi fakir miskin."
    )
    pdf.multi_cell(0, 5, txt=teks_penutup, align='J')
    
    temp_dir = tempfile.mkdtemp()
    filepath = os.path.join(temp_dir, f"SK_Bansos_{nik}.pdf")
    pdf.output(filepath)
    return filepath


# --- 5. ANTARMUKA UTAMA ---
st.sidebar.markdown("""
    <div style='text-align: center; margin-bottom: 20px;'>
        <h2 style='color: #1e40af; margin-bottom: 0; font-weight: 800;'>🏛️ NALAR</h2>
        <p style='color: #64748b; font-size: 0.9rem;'>GovTech Indonesia</p>
    </div>
""", unsafe_allow_html=True)

st.sidebar.success("👨‍💼 **Operator:** Admin Nasional\n\n🟢 **Status:** Sistem Berjalan")
st.sidebar.markdown("<br><br><br><br><br><br><br><br>", unsafe_allow_html=True)
if st.sidebar.button("🚪 Keluar Sistem", use_container_width=True):
    st.session_state['logged_in'] = False
    st.rerun()

st.markdown("""
    <h1 style='color: #0f172a; font-weight: 800;'>Dasbor Operasional NALAR</h1>
    <p style='color: #64748b; font-size: 1.1rem; margin-top: -10px;'>Platform Analisis Prediktif & Explainable AI Skala Nasional</p>
""", unsafe_allow_html=True)
st.write("")

tab1, tab2, tab3, tab4 = st.tabs(["🧑‍🤝‍🧑 Verifikasi Individu", "📂 Pemrosesan Massal", "📈 Simulasi Kuota APBN", "🛡️ Audit Bias Algoritma"])

# --- TAB 1: PREDIKSI INDIVIDU ---
with tab1:
    col_input, col_hasil = st.columns([1.2, 1.8], gap="large")
    
    with col_input:
        with st.container(border=True):
            st.markdown("<h4 style='color: #1e293b;'>📝 Data Identitas</h4>", unsafe_allow_html=True)
            nik_input = st.text_input("Nomor Induk Kependudukan (NIK)", max_chars=16, placeholder="Ketik 16 Digit NIK di sini")
            nama_input = st.text_input("Nama Kepala Keluarga", placeholder="Contoh: Budi Santoso")
            
            st.divider()
            st.markdown("<h4 style='color: #1e293b;'>📊 Parameter Sosio-Ekonomi</h4>", unsafe_allow_html=True)
            pekerjaan = st.selectbox("Status Pekerjaan", le_pekerjaan.classes_, key='t1_pek')
            pendapatan = st.number_input("Penghasilan Bulanan (Rp)", 500000, 20000000, 2500000, step=500000, key='t1_pen')
            tanggungan = st.slider("Jumlah Tanggungan Keluarga", 1, 10, 3, key='t1_tan')
            rumah = st.selectbox("Status Rumah", le_rumah.classes_, key='t1_rum')
            listrik = st.selectbox("Daya Listrik (VA)", [450, 900, 1300, 2200, 3500], key='t1_lis')
            
            st.divider()
            if pekerjaan == 'PNS/TNI/POLRI':
                st.error("🚨 **BLOKIR OTOMATIS:** Regulasi melarang ASN/TNI/POLRI menerima bansos.")
            if listrik >= 1300:
                st.warning("⚠️ **PERINGATAN:** Daya listrik tinggi mengindikasikan keluarga mampu.")
            
            teks_sanggahan = st.text_area("Laporan/Keluhan Warga:", placeholder="Ketik keluhan dari lapangan...", height=100)
            
            form_valid = len(nik_input) == 16 and len(nama_input) > 0
            
            st.write("")
            if st.button("🚀 Analisis Menggunakan AI", type="primary", use_container_width=True, disabled=not form_valid):
                st.session_state['run_analysis'] = True

    with col_hasil:
        if st.session_state.get('run_analysis', False) and form_valid:
            input_data = np.array([[le_pekerjaan.transform([pekerjaan])[0], pendapatan, tanggungan, le_rumah.transform([rumah])[0], listrik]])
            pred = model.predict(input_data)[0]
            pred_prob = model.predict_proba(input_data)[0]
            sentimen = klasifikasi_sentimen(teks_sanggahan)
            hasil_teks = "LAYAK (Approve)" if pred == 1 else "TIDAK LAYAK (Reject)"
            
            with st.container(border=True):
                st.markdown("<h4 style='color: #1e293b;'>🎯 Keputusan Algoritma</h4>", unsafe_allow_html=True)
                m1, m2 = st.columns(2)
                color_hasil = "normal" if pred == 1 else "inverse"
                m1.metric("Status Bantuan", hasil_teks, f"{pred_prob[1]:.1%} Akurasi", delta_color=color_hasil)
                m2.metric("Sentimen Narasi", sentimen.split(" ")[0], sentimen.split(" ", 1)[1] if len(sentimen.split(" "))>1 else "", delta_color="off")
                
                st.divider()
                pdf_path = create_pdf("Admin", nik_input, nama_input, pekerjaan, pendapatan, tanggungan, rumah, listrik, hasil_teks, sentimen)
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button("📄 Unduh Surat Keputusan Resmi (PDF)", data=pdf_file, file_name=f"SK_Bansos_{nik_input}.pdf", mime="application/pdf", type="primary", use_container_width=True)
            
            st.write("")
            with st.container(border=True):
                st.markdown("<h4 style='color: #1e293b;'>🧠 Transparansi AI (Metode LIME)</h4>", unsafe_allow_html=True)
                st.caption("Faktor pendorong keputusan algoritma (Warna Hijau = Mendukung Layak, Merah = Menolak)")
                with st.spinner('Membedah logika AI...'):
                    exp = explainer.explain_instance(data_row=input_data[0], predict_fn=model.predict_proba, num_features=5)
                    fig = exp.as_pyplot_figure()
                    fig.patch.set_facecolor('white') 
                    st.pyplot(fig)
        else:
            with st.container(border=True):
                st.markdown("""
                <div style='text-align: center; padding: 80px 20px; color: #94a3b8;'>
                    <h1 style='font-size: 4rem; margin-bottom: 10px;'>📊</h1>
                    <h3 style='color: #64748b;'>Menunggu Input Data</h3>
                    <p>Lengkapi formulir di samping dan tekan tombol Analisis untuk melihat dekonstruksi keputusan AI.</p>
                </div>
                """, unsafe_allow_html=True)

# --- TAB 2, 3, 4 ---
with tab2:
    st.markdown("<h3 style='color: #0f172a;'>📂 Pemrosesan Rekap Wilayah</h3>", unsafe_allow_html=True)
    col_dl, col_ul = st.columns(2)
    with col_dl:
        with st.container(border=True):
            st.markdown("#### 1. Format Template")
            with open('dataset_sintetik_bansos.csv', 'rb') as f:
                st.download_button('⬇️ Unduh CSV Kosong', f, file_name='template_batch.csv', mime='text/csv', use_container_width=True)
    with col_ul:
        with st.container(border=True):
            st.markdown("#### 2. Unggah Data CSV")
            uploaded_file = st.file_uploader("Pilih file CSV warga", type=["csv"], label_visibility="collapsed")
            
    if uploaded_file is not None:
        df_batch = pd.read_csv(uploaded_file)
        if st.button("⚙️ Proses Ribuan Data Sekarang", type="primary", use_container_width=True):
            with st.spinner("AI sedang memproses..."):
                df_batch['Pekerjaan_KK_Enc'] = le_pekerjaan.transform(df_batch['Pekerjaan_Kepala_Keluarga'])
                df_batch['Kondisi_Rumah_Enc'] = le_rumah.transform(df_batch['Kondisi_Rumah'])
                X_batch = df_batch[feature_cols]
                preds = model.predict(X_batch.values)
                df_batch['Status'] = ['Layak' if p == 1 else 'Tidak Layak' for p in preds]
                st.success(f"✅ Selesai memproses {len(df_batch)} data!")
                st.dataframe(df_batch[['NIK_Keluarga', 'Pendapatan_Bln_Rp', 'Status']], use_container_width=True)

with tab3:
    st.markdown("<h3 style='color: #0f172a;'>📈 Simulasi Pagu Anggaran APBN</h3>", unsafe_allow_html=True)
    with st.container(border=True):
        kuota = st.slider("Atur Kuota Penerima Bantuan Sosial:", 1, len(df_master), min(300, len(df_master)))
        if st.button("🔄 Eksekusi Simulasi", type="primary"):
            df_sim = df_master.copy()
            df_sim['Skor_Kemiskinan'] = model.predict_proba(df_sim[feature_cols].values)[:, 1]
            df_sim = df_sim.sort_values('Skor_Kemiskinan', ascending=False).reset_index(drop=True)
            df_sim['Keputusan'] = ['Terima' if i < kuota else 'Antre' for i in range(len(df_sim))]
            st.success(f"📊 {kuota} keluarga lolos verifikasi anggaran.")
            st.dataframe(df_sim[['NIK_Keluarga', 'Skor_Kemiskinan', 'Keputusan']].head(kuota + 3), use_container_width=True)

with tab4:
    st.markdown("<h3 style='color: #0f172a;'>🛡️ Peta Dominasi Atribut AI</h3>", unsafe_allow_html=True)
    with st.container(border=True):
        importances = model.feature_importances_
        labels = ['Pekerjaan', 'Pendapatan', 'Tanggungan', 'Kondisi Rumah', 'Daya Listrik']
        indices = np.argsort(importances)
        fig_global, ax_global = plt.subplots(figsize=(10, 4))
        ax_global.barh([labels[i] for i in indices], importances[indices], color='#3b82f6')
        ax_global.spines[['top', 'right']].set_visible(False)
        fig_global.patch.set_facecolor('white')
        st.pyplot(fig_global)