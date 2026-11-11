import os
import random
import tempfile
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import lime
import lime.lime_tabular
from fpdf import FPDF

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, 'dataset_sintetik_bansos.csv')

# --- 1. DATASET INITIALIZATION ---
def ensure_dataset():
    if not os.path.exists(DATASET_PATH):
        np.random.seed(42)
        random.seed(42)
        n_samples = 1500
        pekerjaan_list = ['Tidak Bekerja', 'Buruh Harian', 'Petani/Nelayan', 'Wiraswasta Kecil', 'Karyawan Swasta', 'PNS/TNI/POLRI']
        data = []
        for _ in range(n_samples):
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
            
        df = pd.DataFrame(data, columns=['NIK_Keluarga', 'Pekerjaan_Kepala_Keluarga', 'Pendapatan_Bln_Rp', 'Jml_Tanggungan', 'Kondisi_Rumah', 'Daya_Listrik_VA', 'Status_Layak_Bansos'])
        df.to_csv(DATASET_PATH, index=False)

ensure_dataset()

# --- 2. MODEL ENGINE CLASS ---
class BansosModelEngine:
    def __init__(self):
        self.df = pd.read_csv(DATASET_PATH)
        self.le_pekerjaan = LabelEncoder()
        self.df['Pekerjaan_KK_Enc'] = self.le_pekerjaan.fit_transform(self.df['Pekerjaan_Kepala_Keluarga'])
        
        self.le_rumah = LabelEncoder()
        self.df['Kondisi_Rumah_Enc'] = self.le_rumah.fit_transform(self.df['Kondisi_Rumah'])
        
        self.features = ['Pekerjaan_KK_Enc', 'Pendapatan_Bln_Rp', 'Jml_Tanggungan', 'Kondisi_Rumah_Enc', 'Daya_Listrik_VA']
        self.feature_names_readable = ['Pekerjaan', 'Pendapatan', 'Tanggungan', 'Kondisi Rumah', 'Daya Listrik']
        
        X = self.df[self.features]
        y = self.df['Status_Layak_Bansos']
        
        self.model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=5)
        self.model.fit(X.values, y)
        
        self.explainer = lime.lime_tabular.LimeTabularExplainer(
            training_data=X.values,
            feature_names=self.feature_names_readable,
            class_names=['Tidak Layak', 'Layak'],
            mode='classification'
        )
        
    def get_dropdown_options(self):
        return {
            'pekerjaan': list(self.le_pekerjaan.classes_),
            'kondisi_rumah': list(self.le_rumah.classes_),
            'daya_listrik': [450, 900, 1300, 2200, 3500],
            'desil_dtsen': [
                'Desil 10 (Sangat Mampu / 10% Teratas)',
                'Desil 9 (Mampu / Non-Subsidi)',
                'Desil 8 (Menengah Atas)',
                'Desil 7 (Menengah)',
                'Desil 6 (Menengah Bawah)',
                'Desil 5 (Hampir Mampu)',
                'Desil 4 (Rentan Miskin)',
                'Desil 3 (Hampir Miskin Prioritas)',
                'Desil 2 (Fakir Miskin)',
                'Desil 1 (Kemiskinan Ekstrem)',
                'Belum Terdaftar / Non-DTKS'
            ],
            'jalur_verifikasi': [
                'Pemeriksaan Reguler',
                'Sanggahan / Koreksi Exclusion Error DTSEN'
            ]
        }

    def predict_single(self, pekerjaan, pendapatan, tanggungan, rumah, listrik, sanggahan="",
                       desil_dtsen="Belum Terdaftar / Non-DTKS", jalur_sanggahan="Normal",
                       nama="Warga Pemohon", nik="3673000000000000"):
        pekerjaan_enc = self.le_pekerjaan.transform([pekerjaan])[0]
        rumah_enc = self.le_rumah.transform([rumah])[0]
        input_data = np.array([[pekerjaan_enc, float(pendapatan), int(tanggungan), rumah_enc, int(listrik)]])
        
        pred = int(self.model.predict(input_data)[0])
        pred_prob = self.model.predict_proba(input_data)[0].tolist()
        
        # Explain with LIME for chart display
        exp = self.explainer.explain_instance(
            data_row=input_data[0],
            predict_fn=self.model.predict_proba,
            num_features=5,
            num_samples=1000
        )
        lime_list = exp.as_list()
        explanation = []
        for feature_text, weight in lime_list:
            explanation.append({
                'feature': feature_text,
                'weight': round(float(weight), 4),
                'impact': 'Mendukung Layak' if weight > 0 else 'Mendorong Tolak',
                'color': '#10B981' if weight > 0 else '#EF4444'
            })
            
        sentiment_info = self.analyze_sentiment(sanggahan)
        
        # Hard rule notifications
        policy_notes = []
        if pekerjaan == 'PNS/TNI/POLRI':
            policy_notes.append({
                'type': 'danger',
                'message': 'Regulasi melarang ASN/TNI/POLRI menerima bantuan sosial.'
            })
        if int(listrik) >= 1300:
            policy_notes.append({
                'type': 'warning',
                'message': 'Daya listrik >= 1300 VA tergolong rumah tangga mampu secara energi.'
            })
        if float(pendapatan) <= 1500000 and int(tanggungan) >= 4:
            policy_notes.append({
                'type': 'success',
                'message': 'Rasio pendapatan per kapita sangat rendah (prioritas tinggi).'
            })

        # Generate humanized narrative explanation
        complex_xai = self.generate_complex_xai(
            pred=pred,
            pred_prob=pred_prob,
            pekerjaan=pekerjaan,
            pendapatan=pendapatan,
            tanggungan=tanggungan,
            rumah=rumah,
            listrik=listrik,
            lime_list=lime_list,
            desil_dtsen=desil_dtsen,
            jalur_sanggahan=jalur_sanggahan,
            nama=nama,
            nik=nik
        )

        return {
            'status': 'LAYAK' if pred == 1 else 'TIDAK LAYAK',
            'status_code': pred,
            'confidence': round(pred_prob[1] if pred == 1 else pred_prob[0], 3),
            'prob_layak': round(pred_prob[1], 3),
            'prob_tidak_layak': round(pred_prob[0], 3),
            'explanation': explanation,
            'complex_xai': complex_xai,
            'sentiment': sentiment_info,
            'policy_notes': policy_notes
        }

    def generate_complex_xai(self, pred, pred_prob, pekerjaan, pendapatan, tanggungan, rumah, listrik, lime_list,
                             desil_dtsen="Belum Terdaftar / Non-DTKS", jalur_sanggahan="Normal",
                             nama="Warga Pemohon", nik="3673000000000000"):
        pend = float(pendapatan)
        tang = max(1, int(tanggungan))
        per_capita = pend / tang
        daily_per_capita = int(per_capita / 30)
        bps_poverty_line = 550000.0
        ratio_bps = (per_capita / bps_poverty_line) * 100
        prob_layak_pct = round(pred_prob[1] * 100, 1)
        prob_tolak_pct = round(pred_prob[0] * 100, 1)
        
        # 1. Executive Summary Narrative (Manusiawi, Jelas, Ringkas, Padat, Langsung ke Intinya)
        if pred == 1:
            executive_summary_narrative = (
                f"Berdasarkan verifikasi kondisi riil keluarga, pemohon dinyatakan LAYAK MENERIMA BANTUAN SOSIAL. "
                f"Dengan penghasilan Rp {int(pend):,}/bulan untuk menafkahi {tang} orang, rata-rata setiap anggota keluarga hanya hidup dengan "
                f"Rp {int(per_capita):,}/bulan (sekitar Rp {daily_per_capita:,}/hari). Angka ini berada jauh di bawah batas garis kemiskinan standar pemerintah (Rp 550.000). "
                f"Didukung oleh kondisi rumah yang {rumah.lower()} serta penggunaan listrik {listrik} VA, keluarga ini terbukti sangat membutuhkan "
                "bantuan pangan dan pemenuhan kebutuhan dasar dari negara."
            )
        else:
            if pekerjaan == 'PNS/TNI/POLRI':
                executive_summary_narrative = (
                    "Keluarga pemohon dinyatakan TIDAK MEMENUHI SYARAT BANTUAN SOSIAL karena kepala keluarga bekerja sebagai PNS, TNI, atau POLRI. "
                    "Aturan resmi pemerintah dan Komisi Pemberantasan Korupsi (KPK) melarang keras aparatur negara yang sudah berpenghasilan tetap dari negara "
                    "menerima bantuan sosial, agar dana bantuan difokuskan seutuhnya bagi warga miskin yang tidak berpenghasilan tetap."
                )
            else:
                executive_summary_narrative = (
                    f"Berdasarkan pemeriksaan, keluarga pemohon dinyatakan BELUM MEMENUHI KRITERIA PENERIMA BANTUAN SOSIAL. "
                    f"Rata-rata penghasilan per orang dalam keluarga sebesar Rp {int(per_capita):,}/bulan telah melampaui batas kriteria kemiskinan pemerintah. "
                    f"Kondisi tempat tinggal yang {rumah.lower()} dan daya listrik {listrik} VA menunjukkan keluarga masih memiliki kemampuan mandiri, "
                    "sehingga kuota bantuan diprioritaskan bagi keluarga lain yang kondisinya jauh lebih mendesak."
                )

        # 2. Income Assessment (Bahasa Manusiawi)
        if per_capita <= 350000:
            poverty_category = "Kemiskinan Ekstrem (Sangat Membutuhkan Bantuan)"
            income_assessment = (
                f"Setiap anggota keluarga rata-rata hanya memiliki biaya hidup Rp {int(per_capita):,} per bulan (sekitar Rp {daily_per_capita:,} per hari). "
                f"Jumlah ini hanya mencakup {round(ratio_bps, 1)}% dari batas garis kemiskinan pemerintah (Rp 550.000). "
                "Keluarga ini berada dalam kondisi sangat kekurangan untuk makan sehari-hari dan menjadi prioritas utama penerima bantuan sembako dan uang tunai."
            )
        elif per_capita <= bps_poverty_line:
            poverty_category = "Fakir Miskin (Prioritas Bantuan)"
            income_assessment = (
                f"Biaya hidup per anggota keluarga rata-rata Rp {int(per_capita):,} per bulan (sekitar Rp {daily_per_capita:,} per hari), "
                f"berada di bawah batas garis kemiskinan resmi ({round(ratio_bps, 1)}% dari batas Rp 550.000). "
                "Keluarga memenuhi syarat sebagai penerima bantuan sosial untuk menjaga kecukupan pangan dan gizi anak."
            )
        elif per_capita <= 850000:
            poverty_category = "Rentan Miskin (Dekat Ambang Batas)"
            income_assessment = (
                f"Penghasilan per orang sebesar Rp {int(per_capita):,} per bulan berada sedikit di atas garis kemiskinan dasar. "
                "Meskipun saat ini masih mencukupi kebutuhan makan seadanya, keluarga ini sangat rentan jatuh miskin jika harga beras naik atau terjadi musibah sakit."
            )
        else:
            poverty_category = "Keluarga Mampu (Cukup Sejahtera)"
            income_assessment = (
                f"Rata-rata penghasilan per orang sebesar Rp {int(per_capita):,} per bulan dinilai sudah mencukupi kebutuhan hidup layak. "
                "Tingkat ekonomi keluarga sudah berada di atas batas kriteria kemiskinan, sehingga tidak menjadi target bantuan sosial bersyarat."
            )

        # 3. Housing Assessment (Bahasa Manusiawi)
        if rumah == 'Tidak Permanen':
            housing_assessment = (
                "Kondisi rumah masih tergolong tidak permanen (seperti dinding bilik bambu/kayu lapuk, lantai tanah atau semen rusak, dan atap seng berkarat/bocor). "
                "Kondisi fisik ini membuktikan secara nyata bahwa keluarga hidup dalam keterbatasan tempat tinggal yang layak dan sehat."
            )
        elif rumah == 'Semi Permanen':
            housing_assessment = (
                "Kondisi rumah semi permanen dengan konstruksi bangunan sederhana yang belum tuntas. "
                "Keluarga masih memiliki keterbatasan ekonomi untuk merawat tempat tinggal yang kokoh dan sehat."
            )
        elif rumah == 'Permanen Layak':
            housing_assessment = (
                "Keluarga menempati rumah permanen yang layak huni, bertembok kokoh dan berlantai rapi. "
                "Kepemilikan rumah layak ini menandakan kebutuhan dasar papan keluarga sudah terpenuhi dengan baik."
            )
        else:
            housing_assessment = (
                "Keluarga menempati rumah permanen yang luas dan mewah. "
                "Kepemilikan aset hunian mewah bertentangan dengan prinsip pemberian bantuan sosial yang dikhususkan bagi masyarakat tidak mampu."
            )

        # 4. Energy Assessment (Bahasa Manusiawi)
        if int(listrik) <= 450:
            electricity_assessment = (
                f"Daya listrik yang digunakan adalah {listrik} VA, yaitu pelanggan resmi tarif subsidi penuh dari PLN. "
                "Daya ini hanya cukup untuk lampu penerangan dasar dan membuktikan keluarga tidak memiliki barang elektronik mewah."
            )
        elif int(listrik) <= 900:
            electricity_assessment = (
                f"Daya listrik terpasang adalah {listrik} VA, yang masih masuk dalam batas kewajaran pemakaian listrik bersubsidi untuk keluarga sederhana."
            )
        else:
            electricity_assessment = (
                f"Daya listrik yang digunakan adalah {listrik} VA, yaitu golongan tarif non-subsidi untuk rumah tangga mampu. "
                "Keluarga dinilai mampu membayar tagihan listrik umum tanpa bantuan subsidi energi negara."
            )

        # 5. Profession Assessment (Bahasa Manusiawi)
        if pekerjaan == 'PNS/TNI/POLRI':
            profession_assessment = (
                "Kepala keluarga bekerja sebagai ASN, TNI, atau POLRI. "
                "Aturan pemerintah melarang keras aparatur berpenghasilan tetap dari kas negara menerima bantuan sosial fakir miskin."
            )
        elif pekerjaan in ['Tidak Bekerja', 'Buruh Harian']:
            profession_assessment = (
                f"Pekerjaan kepala keluarga adalah '{pekerjaan}' dengan penghasilan harian yang tidak menentu dan tanpa tunjangan kerja. "
                "Jika tidak ada panggilan kerja, keluarga berada dalam risiko besar kekurangan makanan sehari-hari."
            )
        elif pekerjaan in ['Petani/Nelayan', 'Wiraswasta Kecil']:
            profession_assessment = (
                f"Pekerjaan sebagai '{pekerjaan}' sangat bergantung pada cuaca, musim tanam, atau hasil penjualan harian, "
                "sehingga penghasilan keluarga berfluktuasi dan rentan saat musim paceklik."
            )
        else:
            profession_assessment = (
                f"Pekerjaan sebagai '{pekerjaan}' memberikan kepastian penghasilan rutin yang relatif stabil setiap bulan."
            )

        # 6. Sengketa DTSEN (Bahasa Manusiawi & Jelas)
        desil_str = str(desil_dtsen).lower()
        is_high_dtsen = any(k in desil_str for k in ['desil 10', 'desil 9', 'desil 8', 'desil 7']) or desil_str.strip() in ['10', '9', '8', '7']
        is_sanggahan = 'sanggahan' in str(jalur_sanggahan).lower() or 'exclusion' in str(jalur_sanggahan).lower()
        
        is_dtsen_anomaly = False
        dtsen_suggested_decile = "Desil 2 (Fakir Miskin)" if per_capita <= bps_poverty_line else "Desil 3 (Hampir Miskin)"
        
        if is_high_dtsen and pred == 1:
            is_dtsen_anomaly = True
            dtsen_anomaly_narrative = (
                f"Perbedaan Data Catatan Pusat vs Fakta Lapangan (Kasus Sengketa Data):\n"
                f"Di data catatan pusat (DTSEN), keluarga ini terdaftar sebagai '{desil_dtsen}' (keluarga mampu). "
                f"Namun saat diverifikasi langsung ke rumahnya, faktanya keluarga ini benar-benar tidak mampu: "
                f"penghasilan hanya Rp {int(per_capita):,}/orang per bulan, rumah masih {rumah.lower()}, dan listrik hanya {listrik} VA. "
                f"Perbedaan data ini umumnya terjadi akibat salah catat petugas survei terdahulu atau musibah kehilangan mata pencaharian.\n"
                f"Tindakan Petugas: Mengutamakan bukti nyata di lapangan agar keluarga ini tetap sah menerima bantuan, "
                f"serta mengajukan surat perbaikan data ke Kementerian Sosial (SIKS-NG) agar status di pusat diperbaiki menjadi {dtsen_suggested_decile}."
            )
        elif is_sanggahan and pred == 1:
            is_dtsen_anomaly = True
            dtsen_anomaly_narrative = (
                "Pemeriksaan Pengaduan / Sanggahan Warga Disetujui:\n"
                f"Keberatan yang disampaikan warga telah terbukti benar lewat pemeriksaan lapangan. "
                f"Dengan rata-rata biaya hidup hanya Rp {int(per_capita):,}/orang dan kondisi rumah {rumah.lower()}, "
                "warga ini berhak dimasukkan ke dalam daftar penerima bantuan sosial."
            )
        elif is_high_dtsen and pred == 0:
            dtsen_anomaly_narrative = (
                f"Keluarga tercatat pada '{desil_dtsen}' di data pusat. Hasil pemeriksaan lapangan memastikan bahwa keluarga ini memang tergolong mampu, "
                "sehingga data di komputer sudah sesuai dengan kenyataan di lapangan (tidak ada kesalahan data)."
            )
        else:
            dtsen_anomaly_narrative = (
                f"Status data terdaftar ({desil_dtsen}) sejalan dengan kondisi ekonomi yang ditemukan petugas di lapangan."
            )

        # 7. Batas Perubahan Ekonomi (What-If Bahasa Manusiawi)
        if pred == 1:
            threshold_income = int(tang * 650000)
            max_delta = max(0, threshold_income - int(pend))
            counterfactual = {
                'headline': "Batas Perubahan Kondisi Ekonomi (Kapan Bantuan Berhenti?)",
                'details': (
                    f"Keluarga ini berhak terus menerima bantuan selama total penghasilan keluarga tidak naik melebihi Rp {threshold_income:,}/bulan "
                    f"(atau ada kenaikan penghasilan lebih dari +Rp {max_delta:,}/bulan), serta tetap memakai listrik bersubsidi (<= 900 VA). "
                    "Jika di masa depan keluarga menambah daya listrik menjadi 1.300 VA ke atas atau merenovasi rumah menjadi mewah, "
                    "maka hak bantuan sosial akan dialihkan ke keluarga lain yang lebih membutuhkan."
                )
            }
        else:
            max_income_for_layak = int(tang * 550000)
            counterfactual = {
                'headline': "Syarat Agar Bisa Menerima Bantuan di Masa Depan",
                'details': (
                    f"Keluarga dapat kembali mengajukan permohonan bantuan jika terjadi penurunan drastis kondisi ekonomi, "
                    f"yaitu jika total penghasilan keluarga turun di bawah Rp {max_income_for_layak:,}/bulan untuk {tang} orang anggota keluarga, "
                    "serta memenuhi kriteria keterbatasan tempat tinggal."
                )
            }

        # 8. Berita Acara Pertimbangan Resmi (Bahasa Administrasi Bersih)
        status_label = "LAYAK MENERIMA BANTUAN SOSIAL" if pred == 1 else "TIDAK LAYAK (DITOLAK)"
        scientific_justification = (
            f"BERITA ACARA VERIFIKASI RESMI:\n"
            f"Pada tanggal {datetime.now().strftime('%d %B %Y')}, telah dilakukan verifikasi berkas NIK {nik} atas nama {nama}. "
            f"Berdasarkan peninjauan terhadap 5 kriteria dasar (penghasilan per kapita Rp {int(per_capita):,}, tanggungan {tang} jiwa, "
            f"kondisi rumah '{rumah}', daya listrik {listrik} VA, dan pekerjaan '{pekerjaan}'), keluarga ditetapkan: '{status_label}'. "
            f"Penetapan ini sah dan berlandaskan pedoman penanganan fakir miskin UU No. 13 Tahun 2011 dan Kepmensos No. 262/HUK/2022. "
            + (f"\nCATATAN SENGKETA: Ditemukan perbedaan data pusat ({desil_dtsen}) dengan kondisi riil; penetapan mengesahkan bukti nyata lapangan." if is_dtsen_anomaly else "")
        )

        return {
            'poverty_category': poverty_category,
            'per_capita_income': int(per_capita),
            'daily_per_capita': daily_per_capita,
            'bps_poverty_line': int(bps_poverty_line),
            'ratio_bps_percent': round(ratio_bps, 1),
            'confidence_margin': round(abs(pred_prob[1] - 0.5) * 200, 1),
            'prob_layak_pct': prob_layak_pct,
            'prob_tolak_pct': prob_tolak_pct,
            'is_dtsen_anomaly': is_dtsen_anomaly,
            'desil_dtsen': desil_dtsen,
            'dtsen_suggested_decile': dtsen_suggested_decile,
            'executive_summary_narrative': executive_summary_narrative,
            'income_assessment': income_assessment,
            'housing_assessment': housing_assessment,
            'electricity_assessment': electricity_assessment,
            'profession_assessment': profession_assessment,
            'dtsen_anomaly_narrative': dtsen_anomaly_narrative,
            'counterfactual': counterfactual,
            'scientific_justification': scientific_justification
        }

    def analyze_sentiment(self, text):
        if not text or not text.strip():
            return {
                'label': 'Netral (Tidak ada keluhan khusus)',
                'badge': 'Netral',
                'color': 'gray',
                'icon': 'info'
            }
        text_lower = text.lower()
        if any(k in text_lower for k in ['kecewa', 'marah', 'buruk', 'gagal', 'palsu', 'bohong', 'protes', 'miskin', 'kelaparan', 'parah', 'curang', 'sanggah', 'desil 10']):
            return {
                'label': 'Keluhan Mendesak / Mengajukan Sanggahan',
                'badge': 'Kritis & Sanggahan',
                'color': 'red',
                'icon': 'alert-circle'
            }
        elif any(k in text_lower for k in ['mohon', 'tolong', 'harap', 'tanya', 'bantu', 'terima kasih']):
            return {
                'label': 'Permohonan Bantuan / Koperatif',
                'badge': 'Koperatif',
                'color': 'emerald',
                'icon': 'smile'
            }
        return {
            'label': 'Keterangan Standar',
            'badge': 'Standar',
            'color': 'blue',
            'icon': 'file-text'
        }

    def process_batch(self, df_upload):
        required_cols = ['NIK_Keluarga', 'Pekerjaan_Kepala_Keluarga', 'Pendapatan_Bln_Rp', 'Jml_Tanggungan', 'Kondisi_Rumah', 'Daya_Listrik_VA']
        for col in required_cols:
            if col not in df_upload.columns:
                raise ValueError(f"Kolom wajib '{col}' tidak ditemukan dalam file CSV.")
        
        df_copy = df_upload.copy()
        
        # Handle unseen categories gracefully
        pekerjaan_known = set(self.le_pekerjaan.classes_)
        df_copy['Pekerjaan_Clean'] = df_copy['Pekerjaan_Kepala_Keluarga'].apply(
            lambda x: x if x in pekerjaan_known else 'Wiraswasta Kecil'
        )
        df_copy['Pekerjaan_KK_Enc'] = self.le_pekerjaan.transform(df_copy['Pekerjaan_Clean'])
        
        rumah_known = set(self.le_rumah.classes_)
        df_copy['Rumah_Clean'] = df_copy['Kondisi_Rumah'].apply(
            lambda x: x if x in rumah_known else 'Semi Permanen'
        )
        df_copy['Kondisi_Rumah_Enc'] = self.le_rumah.transform(df_copy['Rumah_Clean'])
        
        X_batch = df_copy[self.features]
        preds = self.model.predict(X_batch.values)
        probs = self.model.predict_proba(X_batch.values)[:, 1]
        
        df_copy['Status_Rekomendasi'] = ['LAYAK' if p == 1 else 'TIDAK LAYAK' for p in preds]
        df_copy['Skor_Kemiskinan'] = [round(float(pr), 3) for pr in probs]
        
        # DTSEN Audit & Anomaly Detection in Batch
        has_dtsen_col = 'Desil_DTSEN' in df_copy.columns
        has_sanggahan_col = 'Status_Sanggahan' in df_copy.columns
        
        status_audit_list = []
        anomaly_count = 0
        sanggahan_approved_count = 0
        
        for idx, row in df_copy.iterrows():
            d_val = str(row['Desil_DTSEN']).strip() if has_dtsen_col else ''
            s_val = str(row['Status_Sanggahan']).strip().lower() if has_sanggahan_col else ''
            is_layak = row['Status_Rekomendasi'] == 'LAYAK'
            is_high = any(k in d_val.lower() for k in ['desil 10', 'desil 9', 'desil 8', 'desil 7']) or d_val in ['10', '9', '8', '7']
            
            if is_layak and (is_high or 'sanggahan' in s_val or 'disetujui' in s_val):
                status_audit_list.append('🚨 Anomali Exclusion Error (DTSEN Tinggi -> Layak Faktual)')
                anomaly_count += 1
                if 'disetujui' in s_val or 'sanggahan' in s_val:
                    sanggahan_approved_count += 1
            elif 'sanggahan' in s_val or 'disetujui' in s_val:
                status_audit_list.append('✅ Sanggahan Terverifikasi (Koreksi Lapangan)')
                sanggahan_approved_count += 1
            elif is_high and not is_layak:
                status_audit_list.append('Terkonfirmasi Mampu (Sesuai DTSEN)')
            elif is_layak:
                status_audit_list.append('Terverifikasi Layak (Sesuai DTSEN)')
            else:
                status_audit_list.append('Normal')
                
        df_copy['Status_Audit_DTSEN'] = status_audit_list
        
        # Sort by poverty score descending
        df_copy = df_copy.sort_values('Skor_Kemiskinan', ascending=False).reset_index(drop=True)
        df_copy['Peringkat_Kelayakan'] = [f"#{i+1}" for i in range(len(df_copy))]
        
        total_rows = len(df_copy)
        layak_count = int(np.sum(preds == 1))
        tidak_layak_count = total_rows - layak_count
        
        preview_cols = ['Peringkat_Kelayakan', 'NIK_Keluarga', 'Pekerjaan_Kepala_Keluarga', 'Pendapatan_Bln_Rp', 'Jml_Tanggungan', 'Status_Rekomendasi', 'Skor_Kemiskinan', 'Status_Audit_DTSEN']
        result_preview = df_copy[preview_cols].head(50).to_dict(orient='records')
        
        return {
            'total_rows': total_rows,
            'layak_count': layak_count,
            'tidak_layak_count': tidak_layak_count,
            'layak_percentage': round((layak_count / total_rows) * 100, 1) if total_rows > 0 else 0,
            'anomaly_dtsen_count': anomaly_count,
            'sanggahan_approved_count': sanggahan_approved_count,
            'preview': result_preview,
            'full_df': df_copy
        }

    def simulate_budget(self, quota, custom_df=None):
        if custom_df is not None and not custom_df.empty:
            df_sim = custom_df.copy()
            if 'Skor_Kemiskinan' not in df_sim.columns:
                pekerjaan_known = set(self.le_pekerjaan.classes_)
                df_sim['Pekerjaan_Clean'] = df_sim['Pekerjaan_Kepala_Keluarga'].apply(
                    lambda x: x if x in pekerjaan_known else 'Wiraswasta Kecil'
                )
                df_sim['Pekerjaan_KK_Enc'] = self.le_pekerjaan.transform(df_sim['Pekerjaan_Clean'])
                
                rumah_known = set(self.le_rumah.classes_)
                df_sim['Rumah_Clean'] = df_sim['Kondisi_Rumah'].apply(
                    lambda x: x if x in rumah_known else 'Semi Permanen'
                )
                df_sim['Kondisi_Rumah_Enc'] = self.le_rumah.transform(df_sim['Rumah_Clean'])
                
                probs = self.model.predict_proba(df_sim[self.features].values)[:, 1]
                df_sim['Skor_Kemiskinan'] = [round(float(pr), 3) for pr in probs]
        else:
            df_sim = self.df.copy()
            probs = self.model.predict_proba(df_sim[self.features].values)[:, 1]
            df_sim['Skor_Kemiskinan'] = [round(float(pr), 3) for pr in probs]
            
        df_sim = df_sim.sort_values('Skor_Kemiskinan', ascending=False).reset_index(drop=True)
        
        quota = max(1, min(int(quota), len(df_sim)))
        
        # Buffer quota calculation: 95% regular quota, 5% buffer pool for dispute/sanggahan cases
        buffer_quota = max(1, int(quota * 0.05)) if quota >= 20 else 0
        regular_quota = quota - buffer_quota
        
        df_sim['Keputusan'] = [
            'Diterima (Kuota Reguler)' if i < regular_quota else
            ('Diterima (Buffer Sanggahan DTSEN)' if i < quota else 'Antrean Cadangan')
            for i in range(len(df_sim))
        ]
        
        admitted = df_sim.iloc[:quota]
        cutoff_score = float(df_sim.iloc[quota - 1]['Skor_Kemiskinan'])
        avg_income = int(admitted['Pendapatan_Bln_Rp'].mean()) if not admitted.empty else 0
        
        sample_admitted = admitted[['NIK_Keluarga', 'Pekerjaan_Kepala_Keluarga', 'Pendapatan_Bln_Rp', 'Jml_Tanggungan', 'Kondisi_Rumah', 'Skor_Kemiskinan', 'Keputusan']].head(15).to_dict(orient='records')
        waiting = df_sim.iloc[quota:quota + 10][['NIK_Keluarga', 'Pekerjaan_Kepala_Keluarga', 'Pendapatan_Bln_Rp', 'Jml_Tanggungan', 'Kondisi_Rumah', 'Skor_Kemiskinan', 'Keputusan']].to_dict(orient='records')
        
        # Monthly per family: Rp 600,000
        monthly_per_family = 600000
        total_monthly_budget = quota * monthly_per_family
        total_annual_budget = total_monthly_budget * 12
        
        buffer_monthly_budget = buffer_quota * monthly_per_family
        buffer_annual_budget = buffer_monthly_budget * 12
        
        return {
            'quota': quota,
            'regular_quota': regular_quota,
            'buffer_quota': buffer_quota,
            'total_applicants': len(df_sim),
            'cutoff_score': round(cutoff_score, 3),
            'avg_income_admitted': f"Rp {avg_income:,}",
            'total_monthly_budget': f"Rp {total_monthly_budget:,}",
            'total_annual_budget': f"Rp {total_annual_budget:,}",
            'buffer_monthly_budget': f"Rp {buffer_monthly_budget:,}",
            'buffer_annual_budget': f"Rp {buffer_annual_budget:,}",
            'admitted_preview': sample_admitted,
            'waiting_preview': waiting
        }

    def get_feature_importances(self):
        importances = self.model.feature_importances_
        res = []
        for name, imp in zip(self.feature_names_readable, importances):
            res.append({
                'feature': name,
                'importance': round(float(imp), 4),
                'percentage': round(float(imp) * 100, 1)
            })
        res = sorted(res, key=lambda x: x['importance'], reverse=True)
        return res

    def clean_pdf_text(self, text):
        if text is None:
            return ""
        text = str(text)
        replacements = {
            '\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'",
            '\u201c': '"', '\u201d': '"', '\u2022': '*', '\u2265': '>=',
            '\u2264': '<=', '\u2026': '...', '\xa0': ' ', '\xb1': '+/-'
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text.encode('latin-1', 'replace').decode('latin-1')

    def generate_pdf(self, nik, nama, pekerjaan, pendapatan, tanggungan, rumah, listrik, hasil, sanggahan,
                     is_official=False, operator_name=None, operator_nip=None, catatan_petugas=None,
                     desil_dtsen="Belum Terdaftar / Non-DTKS", jalur_sanggahan="Normal", complex_xai=None):
        sentiment = self.analyze_sentiment(sanggahan)
        tanggal_cetak = datetime.now().strftime("%d %B %Y %H:%M WIB")
        
        nik_clean = self.clean_pdf_text(nik or "3673000000000000")
        nama_clean = self.clean_pdf_text(nama or "Warga Pemohon")
        pekerjaan_clean = self.clean_pdf_text(pekerjaan or "Buruh Harian")
        rumah_clean = self.clean_pdf_text(rumah or "Semi Permanen")
        hasil_clean = self.clean_pdf_text(hasil or "LAYAK (Disetujui)")
        sentiment_label_clean = self.clean_pdf_text(sentiment.get('label', 'Netral'))
        catatan_petugas_clean = self.clean_pdf_text(catatan_petugas or "")
        desil_clean = self.clean_pdf_text(desil_dtsen or "Belum Terdaftar")
        jalur_clean = self.clean_pdf_text(jalur_sanggahan or "Normal")
        
        op_name_clean = self.clean_pdf_text(operator_name or "Drs. Hendro Wibowo, M.Si")
        op_nip_clean = self.clean_pdf_text(operator_nip or "19850314 201001 1 008")
        
        try:
            pend_num = int(float(pendapatan))
        except Exception:
            pend_num = 1500000
            
        try:
            tang_num = int(tanggungan)
        except Exception:
            tang_num = 3
            
        try:
            listrik_num = int(listrik)
        except Exception:
            listrik_num = 900

        pdf = FPDF()
        pdf.add_page()
        
        if is_official:
            pdf.set_font("Arial", size=13, style='B')
            pdf.cell(190, 7, txt="PEMERINTAH REPUBLIK INDONESIA", ln=True, align='C')
            pdf.set_font("Arial", size=11, style='B')
            pdf.cell(190, 6, txt="DINAS SOSIAL DAERAH / KEMENTERIAN SOSIAL RI", ln=True, align='C')
            pdf.set_font("Arial", size=9)
            pdf.cell(190, 5, txt="Sistem Pengambilan Keputusan Bantuan Sosial Terintegrasi (NALAR)", ln=True, align='C')
            pdf.line(10, 30, 200, 30)
            pdf.line(10, 31, 200, 31)
            
            pdf.ln(3)
            pdf.set_font("Arial", size=8, style='I')
            pdf.cell(190, 4, txt="Landasan Hukum: UU No. 13/2011 Penanganan Fakir Miskin | Kepmensos No. 262/HUK/2022 | DTKS BPS", ln=True, align='C')
            pdf.line(10, 37, 200, 37)
            
            pdf.ln(5)
            pdf.set_font("Arial", size=12, style='B')
            pdf.cell(190, 7, txt="BERITA ACARA & SURAT KEPUTUSAN PENETAPAN KELAYAKAN BANSOS", ln=True, align='C')
            pdf.set_font("Arial", size=8)
            prefix_nik = nik_clean[:6] if len(nik_clean) >= 6 else (nik_clean + "000000")[:6]
            pdf.cell(190, 5, txt=f"Nomor SK Resmi: DINSOS/SK-BANSOS/{datetime.now().strftime('%Y%m')}/{prefix_nik}-{random.randint(1000, 9999)}", ln=True, align='C')
        else:
            pdf.set_font("Arial", size=12, style='B')
            pdf.cell(190, 7, txt="PORTAL SIMULASI MANDIRI BANTUAN SOSIAL (NALAR)", ln=True, align='C')
            pdf.set_font("Arial", size=9, style='I')
            pdf.cell(190, 5, txt="Dokumen Hasil Simulasi Mandiri Warga - Bukan Dokumen Penetapan Hukum", ln=True, align='C')
            pdf.line(10, 25, 200, 25)
            
            pdf.ln(4)
            pdf.set_font("Arial", size=11, style='B')
            pdf.cell(190, 7, txt="BUKTI CEK KELAYAKAN MANDIRI WARGA", ln=True, align='C')
            pdf.set_font("Arial", size=8)
            pdf.cell(190, 5, txt=f"ID Simulasi: SIM-WARGA/{datetime.now().strftime('%Y%m%d')}/{nik_clean[:8]}", ln=True, align='C')

        pdf.ln(4)
        pdf.set_font("Arial", size=9, style='B')
        pdf.cell(190, 5, txt="A. IDENTITAS PEMOHON & DATA STATUS REGISTRASI NASIONAL", ln=True, align='L')
        pdf.set_font("Arial", size=8.5)
        pdf.cell(190, 4.5, txt=f"  1. Nomor Induk Kependudukan (NIK) : {nik_clean}", ln=True, align='L')
        pdf.cell(190, 4.5, txt=f"  2. Nama Lengkap Kepala Keluarga   : {nama_clean}", ln=True, align='L')
        pdf.cell(190, 4.5, txt=f"  3. Status Terdaftar di DTSEN/P3KE : {desil_clean}", ln=True, align='L')
        pdf.cell(190, 4.5, txt=f"  4. Kategori Jalur Verifikasi      : {jalur_clean}", ln=True, align='L')
        
        pdf.ln(2)
        pdf.set_font("Arial", size=9, style='B')
        pdf.cell(190, 5, txt="B. BUKTI FAKTUAL KONDISI KELUARGA DI LAPANGAN", ln=True, align='L')
        pdf.set_font("Arial", size=8.5)
        pdf.cell(190, 4.5, txt=f"  1. Pekerjaan Kepala Keluarga      : {pekerjaan_clean}", ln=True, align='L')
        pdf.cell(190, 4.5, txt=f"  2. Penghasilan Bulanan Keluarga   : Rp {pend_num:,}", ln=True, align='L')
        pdf.cell(190, 4.5, txt=f"  3. Jumlah Tanggungan Keluarga     : {tang_num} Jiwa (Rata-rata: Rp {int(pend_num/max(1, tang_num)):,}/orang/bulan)", ln=True, align='L')
        pdf.cell(190, 4.5, txt=f"  4. Kondisi Fisik Tempat Tinggal   : {rumah_clean}", ln=True, align='L')
        pdf.cell(190, 4.5, txt=f"  5. Daya Listrik Rumah Tangga      : {listrik_num} VA", ln=True, align='L')
        
        pdf.ln(2)
        pdf.set_font("Arial", size=9, style='B')
        pdf.cell(190, 5, txt="C. KEPUTUSAN PENETAPAN & ALASAN RESMI KELAYAKAN", ln=True, align='L')
        pdf.set_font("Arial", size=9, style='B')
        pdf.cell(190, 5, txt=f"  HASIL PENETAPAN KELAYAKAN         : {hasil_clean}", ln=True, align='L')
        pdf.set_font("Arial", size=8.5)
        pdf.cell(190, 4.5, txt=f"  Catatan Permohonan Warga          : {sentiment_label_clean}", ln=True, align='L')
        
        # Narasi Alasan Manusiawi
        if complex_xai:
            narasi = complex_xai.get('executive_summary_narrative', '')
        else:
            narasi = (
                f"Penetapan '{hasil_clean}' diputuskan berdasarkan pembuktian penghasilan per kapita terhadap Garis Kemiskinan pemerintah, "
                f"kondisi fisik tempat tinggal, daya listrik bersubsidi, dan ketiadaan anggota keluarga yang berstatus PNS/TNI/Polri."
            )
        pdf.set_font("Arial", size=8)
        pdf.multi_cell(0, 3.8, txt=f"  Alasan Penetapan: {self.clean_pdf_text(narasi)}", align='J')

        # D. Catatan Sengketa DTSEN jika ada
        is_anomali = ('desil 10' in desil_clean.lower() or 'desil 9' in desil_clean.lower() or 'desil 8' in desil_clean.lower() or 'sanggahan' in jalur_clean.lower()) and 'LAYAK' in hasil_clean
        if is_anomali:
            pdf.ln(2)
            pdf.set_font("Arial", size=9, style='B')
            pdf.cell(190, 5, txt="D. PEMERIKSAAN SENGKETA DATA DTSEN & USULAN PERBAIKAN", ln=True, align='L')
            pdf.set_font("Arial", size=8)
            catatan_dtsen = (
                f"Ditemukan perbedaan data: Warga terdaftar di {desil_clean} pada data pusat, namun pemeriksaan lapangan membuktikan keluarga "
                f"benar-benar tidak mampu (Desil 2-3). Diterbitkan Berita Acara Rekomendasi Resmi agar warga sah menerima bantuan "
                f"dan diusulkan perbaikan status ke Kementerian Sosial RI melalui aplikasi SIKS-NG."
            )
            pdf.multi_cell(0, 3.8, txt=self.clean_pdf_text(catatan_dtsen), align='J')

        if is_official and catatan_petugas_clean:
            pdf.ln(2)
            pdf.set_font("Arial", size=9, style='B')
            pdf.cell(190, 5, txt="E. CATATAN VERIFIKATOR LAPANGAN DINAS SOSIAL", ln=True, align='L')
            pdf.set_font("Arial", size=8)
            pdf.multi_cell(0, 3.8, txt=f"  Catatan Petugas Lapangan: {catatan_petugas_clean}", align='L')

        pdf.ln(4)
        pdf.set_font("Arial", size=7.5, style='I')
        if is_official:
            penutup = (
                f"Surat Keputusan dan Berita Acara ini diterbitkan sah pada {tanggal_cetak} melalui sistem NALAR. "
                "Keputusan berlandaskan asas keadilan sosial UU No. 13/2011 dan telah disahkan oleh verifikator resmi dinas sosial."
            )
        else:
            penutup = (
                f"Dokumen simulasi ini dicetak mandiri pada {tanggal_cetak} sebagai gambaran awal warga pemohon "
                "dan memerlukan penetapan sah dari petugas Dinas Sosial Kabupaten/Kota."
            )
        pdf.multi_cell(0, 3.5, txt=self.clean_pdf_text(penutup), align='J')
        
        pdf.ln(6)
        pdf.set_font("Arial", size=8.5)
        if is_official:
            pdf.cell(110, 4, txt="", ln=False)
            pdf.cell(80, 4, txt="Mengesahkan Secara Resmi,", ln=True, align='C')
            pdf.cell(110, 4, txt="", ln=False)
            pdf.cell(80, 4, txt="Verifikator Resmi Dinas Sosial", ln=True, align='C')
            pdf.ln(12)
            pdf.set_font("Arial", size=8.5, style='B')
            pdf.cell(110, 4, txt="", ln=False)
            pdf.cell(80, 4, txt=f"[ TERTANDA: {op_name_clean} ]", ln=True, align='C')
            pdf.set_font("Arial", size=7.5)
            pdf.cell(110, 3.5, txt="", ln=False)
            pdf.cell(80, 3.5, txt=f"NIP. {op_nip_clean}", ln=True, align='C')
            pdf.cell(110, 3.5, txt="", ln=False)
            pdf.cell(80, 3.5, txt="Status: SK RESMI BERKEKUATAN HUKUM", ln=True, align='C')
        else:
            pdf.cell(110, 4, txt="", ln=False)
            pdf.cell(80, 4, txt="Dicetak Secara Mandiri Oleh:", ln=True, align='C')
            pdf.cell(110, 4, txt="", ln=False)
            pdf.cell(80, 4, txt="Warga / Pemohon Bantuan", ln=True, align='C')
            pdf.ln(12)
            pdf.set_font("Arial", size=8.5, style='B')
            pdf.cell(110, 4, txt="", ln=False)
            pdf.cell(80, 4, txt=f"( {nama_clean} )", ln=True, align='C')
            pdf.set_font("Arial", size=7.5)
            pdf.cell(110, 3.5, txt="", ln=False)
            pdf.cell(80, 3.5, txt="Status: DRAF SIMULASI MANDIRI", ln=True, align='C')
        
        temp_dir = tempfile.mkdtemp()
        safe_nik_file = "".join(c for c in nik_clean if c.isalnum() or c in ('-', '_')) or "3673000000000000"
        prefix_doc = "SK_Resmi" if is_official else "Simulasi_Warga"
        filepath = os.path.join(temp_dir, f"{prefix_doc}_Bansos_{safe_nik_file}.pdf")
        pdf.output(filepath)
        return filepath

# Instantiate singleton
engine = BansosModelEngine()
