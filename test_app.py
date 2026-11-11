import os
import io
import json
import unittest
from app import app

class FlaskAppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_homepage(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Keadilan', response.data)
        self.assertIn(b'Program Kami', response.data)
        self.assertIn(b'NALAR', response.data)
        print(" [PASS] Homepage rendered with reference design typography.")

    def test_verifikasi_page(self):
        response = self.app.get('/verifikasi')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Verifikasi Kelayakan Individu', response.data)
        print(" [PASS] Verifikasi page loaded.")

    def test_predict_api_layak(self):
        payload = {
            'pekerjaan': 'Buruh Harian',
            'pendapatan': 1200000,
            'tanggungan': 4,
            'rumah': 'Tidak Permanen',
            'listrik': 450,
            'sanggahan': 'Mohon bantuannya untuk keluarga kami'
        }
        response = self.app.post('/api/predict', json=payload)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['status'], 'LAYAK')
        self.assertTrue(len(data['data']['explanation']) > 0)
        print(" [PASS] Predict API (Layak + LIME explanation) works as expected.")

    def test_predict_api_pns(self):
        payload = {
            'pekerjaan': 'PNS/TNI/POLRI',
            'pendapatan': 8000000,
            'tanggungan': 2,
            'rumah': 'Permanen Mewah',
            'listrik': 2200,
            'sanggahan': 'Tolong evaluasi'
        }
        response = self.app.post('/api/predict', json=payload)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['data']['status'], 'TIDAK LAYAK')
        self.assertTrue(any(n['type'] == 'danger' for n in data['data']['policy_notes']))
        print(" [PASS] Predict API (PNS automatic policy check) works as expected.")

    def test_pdf_generation(self):
        payload = {
            'nik': '3673123456789012',
            'nama': 'Budi Santoso',
            'pekerjaan': 'Buruh Harian',
            'pendapatan': 1200000,
            'tanggungan': 4,
            'rumah': 'Tidak Permanen',
            'listrik': 450,
            'hasil': 'LAYAK',
            'sanggahan': 'Mohon bantuan pangan'
        }
        response = self.app.post('/api/download-pdf', data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/pdf')
        self.assertTrue(len(response.data) > 1000)
        print(" [PASS] PDF generation produces valid PDF document.")

    def test_simulasi_api(self):
        response = self.app.post('/api/simulasi', json={'quota': 250})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['quota'], 250)
        print(" [PASS] Simulasi APBN API functions correctly.")

    def test_batch_template(self):
        response = self.app.get('/api/download-template')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'NIK_Keluarga', response.data)
        print(" [PASS] CSV template download works.")

    def test_batch_process(self):
        csv_content = (
            "NIK_Keluarga,Pekerjaan_Kepala_Keluarga,Pendapatan_Bln_Rp,Jml_Tanggungan,Kondisi_Rumah,Daya_Listrik_VA\n"
            "36730001,Buruh Harian,1000000,4,Tidak Permanen,450\n"
            "36730002,PNS/TNI/POLRI,9000000,2,Permanen Mewah,2200\n"
        )
        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'test_batch.csv')
        }
        response = self.app.post('/api/batch-process', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        res_json = json.loads(response.data)
        self.assertEqual(res_json['summary']['total_rows'], 2)
        print(" [PASS] Batch CSV processing works seamlessly.")

    def test_predict_api_dtsen_anomaly(self):
        payload = {
            'nik': '3673091100230004',
            'nama': 'Siti Rohayah',
            'pekerjaan': 'Buruh Harian',
            'pendapatan': 900000,
            'tanggungan': 5,
            'rumah': 'Tidak Permanen',
            'listrik': 450,
            'desil_dtsen': 'Desil 10 (Sangat Mampu / 10% Teratas)',
            'jalur_sanggahan': 'Sanggahan / Koreksi Exclusion Error DTSEN',
            'sanggahan': 'Di data DTSEN tertulis Desil 10 padahal rumah kami beralas tanah dan suami meninggal.'
        }
        response = self.app.post('/api/predict', json=payload)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['status'], 'LAYAK')
        cx = data['data']['complex_xai']
        self.assertTrue(cx['is_dtsen_anomaly'])
        self.assertTrue(len(cx['executive_summary_narrative']) > 200)
        self.assertTrue(len(cx['income_assessment']) > 150)
        self.assertTrue(len(cx['housing_assessment']) > 150)
        self.assertTrue(len(cx['electricity_assessment']) > 150)
        self.assertTrue(len(cx['profession_assessment']) > 150)
        self.assertTrue(len(cx['dtsen_anomaly_narrative']) > 150)
        print(" [PASS] Predict API DTSEN Exclusion Error Anomaly & Extended Narratives verified.")

    def test_batch_dtsen_anomaly_and_sanggahan(self):
        csv_content = (
            "NIK_Keluarga,Pekerjaan_Kepala_Keluarga,Pendapatan_Bln_Rp,Jml_Tanggungan,Kondisi_Rumah,Daya_Listrik_VA,Desil_DTSEN,Status_Sanggahan\n"
            "36730001,Buruh Harian,900000,5,Tidak Permanen,450,Desil 10,Sanggahan_Faktual_Disetujui\n"
            "36730002,Buruh Harian,1100000,4,Tidak Permanen,450,Desil 2,Normal\n"
            "36730003,PNS/TNI/POLRI,9000000,2,Permanen Mewah,2200,Desil 10,Normal\n"
        )
        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'test_batch_dtsen.csv')
        }
        response = self.app.post('/api/batch-process', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        res_json = json.loads(response.data)
        self.assertEqual(res_json['summary']['total_rows'], 3)
        self.assertGreaterEqual(res_json['summary']['anomaly_dtsen_count'], 1)
        self.assertGreaterEqual(res_json['summary']['sanggahan_approved_count'], 1)
        print(" [PASS] Batch DTSEN Anomaly & Sanggahan detection works.")

    def test_pdf_with_dtsen_sanggahan(self):
        payload = {
            'nik': '3673091100230004',
            'nama': 'Siti Rohayah',
            'pekerjaan': 'Buruh Harian',
            'pendapatan': 900000,
            'tanggungan': 5,
            'rumah': 'Tidak Permanen',
            'listrik': 450,
            'hasil': 'LAYAK',
            'desil_dtsen': 'Desil 10 (Sangat Mampu / 10% Teratas)',
            'jalur_sanggahan': 'Sanggahan / Koreksi Exclusion Error DTSEN',
            'sanggahan': 'Mohon verifikasi faktual lapangan'
        }
        response = self.app.post('/api/download-pdf', data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/pdf')
        self.assertTrue(len(response.data) > 1000)
        print(" [PASS] PDF generation with DTSEN Sanggahan produces valid document.")

    def test_audit_page(self):
        response = self.app.get('/audit')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Audit Transparansi', response.data)
        print(" [PASS] Audit page rendered.")

    def test_custom_batch_to_simulasi_flow(self):
        # 1. Upload CSV to batch
        csv_content = (
            "NIK_Keluarga,Pekerjaan_Kepala_Keluarga,Pendapatan_Bln_Rp,Jml_Tanggungan,Kondisi_Rumah,Daya_Listrik_VA,Desil_DTSEN,Status_Sanggahan\n"
            "36730001,Buruh Harian,700000,5,Tidak Permanen,450,Desil 1,Normal\n"
            "36730002,Buruh Harian,900000,4,Tidak Permanen,450,Desil 2,Normal\n"
            "36730003,Petani/Nelayan,1200000,4,Semi Permanen,450,Desil 2,Normal\n"
            "36730004,Wiraswasta Kecil,2000000,3,Semi Permanen,900,Desil 4,Normal\n"
            "36730005,PNS/TNI/POLRI,8000000,2,Permanen Mewah,2200,Desil 10,Normal\n"
        )
        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'warga_rt05.csv')
        }
        res_batch = self.app.post('/api/batch-process', data=data, content_type='multipart/form-data')
        self.assertEqual(res_batch.status_code, 200)

        # 2. Access Simulasi page - should recognize custom batch mode
        res_page = self.app.get('/simulasi')
        self.assertEqual(res_page.status_code, 200)
        self.assertIn(b'Mode Data Wilayah Aktif', res_page.data)
        self.assertIn(b'warga_rt05.csv', res_page.data)

        # 3. Call Simulasi API with quota=3
        res_sim = self.app.post('/api/simulasi', json={'quota': 3})
        self.assertEqual(res_sim.status_code, 200)
        sim_data = json.loads(res_sim.data)['data']
        self.assertEqual(sim_data['total_applicants'], 5)
        self.assertEqual(sim_data['quota'], 3)
        self.assertEqual(len(sim_data['admitted_preview']), 3)
        self.assertEqual(sim_data['is_custom'], True)

        # 4. Reset simulation
        res_reset = self.app.get('/simulasi/reset', follow_redirects=True)
        self.assertEqual(res_reset.status_code, 200)
        self.assertNotIn(b'Mode Data Wilayah Aktif', res_reset.data)
        print(" [PASS] Custom Batch to Simulasi seamless integration verified.")

    def test_humanized_narrative_no_jargon(self):
        payload = {
            'nik': '3673091100230004',
            'nama': 'Siti Rohayah',
            'pekerjaan': 'Buruh Harian',
            'pendapatan': 900000,
            'tanggungan': 5,
            'rumah': 'Tidak Permanen',
            'listrik': 450,
            'desil_dtsen': 'Desil 10 (Sangat Mampu / 10% Teratas)',
            'jalur_sanggahan': 'Sanggahan / Koreksi Exclusion Error DTSEN',
            'sanggahan': 'Verifikasi faktual lapangan'
        }
        response = self.app.post('/api/predict', json=payload)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        cx = data['data']['complex_xai']
        
        all_narratives = " ".join([
            cx.get('executive_summary_narrative', ''),
            cx.get('income_assessment', ''),
            cx.get('housing_assessment', ''),
            cx.get('electricity_assessment', ''),
            cx.get('profession_assessment', ''),
            cx.get('dtsen_anomaly_narrative', ''),
            cx.get('counterfactual', {}).get('headline', ''),
            cx.get('counterfactual', {}).get('details', ''),
            cx.get('scientific_justification', '')
        ]).lower()

        forbidden_terms = [
            'random forest',
            'lime',
            'decision tree',
            'algoritma',
            'probabilitas p =',
            'dekonstruksi',
            'koefisien',
            'permanent wealth index'
        ]

        for term in forbidden_terms:
            self.assertNotIn(term, all_narratives, f"Forbidden jargon '{term}' found in humanized XAI narrative!")

        print(" [PASS] XAI narrative is fully humanized without IT/AI jargon.")

    def test_health_endpoint(self):
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'ok')
        print(" [PASS] Health endpoint returns 200 OK.")

    def test_large_batch_no_cookie_overflow(self):
        header = "NIK_Keluarga,Pekerjaan_Kepala_Keluarga,Pendapatan_Bln_Rp,Jml_Tanggungan,Kondisi_Rumah,Daya_Listrik_VA,Desil_DTSEN,Status_Sanggahan\n"
        rows = [
            f"36730001{i:08d},Buruh Harian,1000000,4,Tidak Permanen,450,Desil 2,Normal"
            for i in range(150)
        ]
        csv_content = header + "\n".join(rows)
        data = {
            'file': (io.BytesIO(csv_content.encode('utf-8')), 'large_warga_150.csv')
        }
        res_batch = self.app.post('/api/batch-process', data=data, content_type='multipart/form-data')
        self.assertEqual(res_batch.status_code, 200)

        res_sim = self.app.post('/api/simulasi', json={'quota': 50})
        self.assertEqual(res_sim.status_code, 200)
        sim_data = json.loads(res_sim.data)['data']
        self.assertEqual(sim_data['total_applicants'], 150)
        self.assertEqual(sim_data['quota'], 50)
        self.assertTrue(sim_data['is_custom'])

        res_export = self.app.get('/api/export-batch')
        self.assertEqual(res_export.status_code, 200)
        exported_lines = res_export.data.decode('utf-8').strip().splitlines()
        self.assertEqual(len(exported_lines), 151)  # header + 150 rows

        res_reset = self.app.get('/simulasi/reset', follow_redirects=True)
        self.assertEqual(res_reset.status_code, 200)
        print(" [PASS] Large 150-row CSV batch works seamlessly without cookie overflow.")

if __name__ == '__main__':
    unittest.main()
