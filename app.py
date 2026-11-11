import os
import io
import csv
import json
import uuid
import zlib
import base64
import tempfile
from flask import (
    Flask, render_template, request, jsonify, 
    send_file, session, redirect, url_for, flash
)
import pandas as pd
from model_service import engine

app = Flask(
    __name__,
    template_folder='templates',
    static_folder='public/static',
    static_url_path='/static'
)
app.secret_key = os.environ.get('SECRET_KEY', 'nalar-govtech-ai-super-secret-key-2026')


# --- BATCH STORAGE HELPERS (Stateless compressed cookie for small CSV + /tmp fallback for large CSV) ---
def _get_batch_filepath(batch_id):
    if not batch_id or not str(batch_id).isalnum():
        return None
    return os.path.join(tempfile.gettempdir(), f"nalar_batch_{batch_id}.csv")


def _cleanup_batch_file(batch_id):
    if batch_id:
        old_path = _get_batch_filepath(batch_id)
        if old_path and os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass


def _save_session_batch(csv_str):
    _cleanup_batch_file(session.pop('batch_id', None))
    compressed = base64.urlsafe_b64encode(
        zlib.compress(csv_str.encode('utf-8'), level=9)
    ).decode('ascii')

    if len(compressed) <= 2800:
        session['batch_csv_z'] = compressed
        return

    session.pop('batch_csv_z', None)
    batch_id = uuid.uuid4().hex
    filepath = _get_batch_filepath(batch_id)
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        f.write(csv_str)
    session['batch_id'] = batch_id


def _load_session_batch_csv():
    compressed = session.get('batch_csv_z')
    if compressed:
        try:
            return zlib.decompress(base64.urlsafe_b64decode(compressed.encode('ascii'))).decode('utf-8')
        except Exception:
            pass
    batch_id = session.get('batch_id')
    filepath = _get_batch_filepath(batch_id)
    if filepath and os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8', newline='') as f:
            return f.read()
    return None


def _clear_session_batch():
    session.pop('batch_csv_z', None)
    _cleanup_batch_file(session.pop('batch_id', None))
    session.pop('has_custom_batch', None)
    session.pop('custom_batch_name', None)
    session.pop('custom_batch_count', None)

# Session helper
def is_logged_in():
    return session.get('logged_in', False)

@app.context_processor
def inject_global_data():
    return {
        'is_logged_in': is_logged_in(),
        'operator_name': session.get('operator_name', 'Masyarakat Umum (Akses Publik)'),
        'operator_nip': session.get('operator_nip', 'N/A'),
        'operator_role': session.get('operator_role', 'Publik'),
        'options': engine.get_dropdown_options()
    }

# --- ROUTES ---

@app.route('/')
def index():
    feature_importances = engine.get_feature_importances()
    return render_template('index.html', feature_importances=feature_importances)

@app.route('/verifikasi')
def verifikasi():
    options = engine.get_dropdown_options()
    return render_template('verifikasi.html', options=options)

@app.route('/massal')
def massal():
    return render_template('massal.html')

@app.route('/simulasi')
def simulasi():
    has_custom = session.get('has_custom_batch', False)
    custom_csv = _load_session_batch_csv() if has_custom else None
    custom_name = session.get('custom_batch_name', 'File CSV Warga')
    
    if has_custom and custom_csv:
        try:
            df_custom = pd.read_csv(io.StringIO(custom_csv))
            initial_quota = max(1, min(len(df_custom), int(len(df_custom) * 0.4)))
            initial_sim = engine.simulate_budget(initial_quota, custom_df=df_custom)
            return render_template(
                'simulasi.html', 
                initial_sim=initial_sim,
                is_custom=True,
                custom_name=custom_name,
                custom_count=len(df_custom)
            )
        except Exception as e:
            print(f"Error loading custom batch into simulation: {e}")
    elif has_custom and not custom_csv:
        _clear_session_batch()
            
    initial_sim = engine.simulate_budget(300)
    return render_template('simulasi.html', initial_sim=initial_sim, is_custom=False)

@app.route('/simulasi/reset')
def reset_simulasi():
    _clear_session_batch()
    flash('Data simulasi telah dikembalikan ke data sampel standar nasional.', 'info')
    return redirect(url_for('simulasi'))

@app.route('/audit')
def audit():
    feature_importances = engine.get_feature_importances()
    return render_template('audit.html', feature_importances=feature_importances)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True
            session['operator_name'] = 'Drs. Hendro Wibowo, M.Si'
            session['operator_nip'] = '19850412 201001 1 003'
            session['operator_role'] = 'Verifikator Utama Kemensos RI'
            flash('Berhasil masuk. Sesi Pegawai Dinas Sosial terverifikasi.', 'success')
            next_url = request.args.get('next') or url_for('verifikasi')
            return redirect(next_url)
        else:
            flash('Kredensial pegawai tidak valid. Gunakan admin / admin123.', 'error')
    return render_template('login.html')

@app.route('/quick-login-demo')
def quick_login_demo():
    session['logged_in'] = True
    session['operator_name'] = 'Drs. Hendro Wibowo, M.Si'
    session['operator_nip'] = '19850412 201001 1 003'
    session['operator_role'] = 'Verifikator Utama Kemensos RI'
    flash('Sesi Pegawai Dinas Sosial berhasil diaktifkan.', 'success')
    next_url = request.args.get('next') or url_for('verifikasi')
    return redirect(next_url)

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah keluar dari Sesi Pegawai Dinas Sosial.', 'info')
    return redirect(url_for('index'))

# --- API ENDPOINTS ---

@app.route('/api/predict', methods=['POST'])
def api_predict():
    try:
        data = request.get_json() if request.is_json else request.form
        nik = data.get('nik', '3673000000000000')
        nama = data.get('nama', 'Warga Pemohon')
        pekerjaan = data.get('pekerjaan')
        pendapatan = float(data.get('pendapatan', 0))
        tanggungan = int(data.get('tanggungan', 1))
        rumah = data.get('rumah')
        listrik = int(data.get('listrik', 900))
        sanggahan = data.get('sanggahan', '')
        desil_dtsen = data.get('desil_dtsen', 'Belum Terdaftar / Non-DTKS')
        jalur_sanggahan = data.get('jalur_sanggahan', 'Normal')
        
        result = engine.predict_single(
            pekerjaan, pendapatan, tanggungan, rumah, listrik, sanggahan,
            desil_dtsen=desil_dtsen, jalur_sanggahan=jalur_sanggahan,
            nama=nama, nik=nik
        )
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/download-pdf', methods=['GET', 'POST'])
def api_download_pdf():
    try:
        data = request.form if request.method == 'POST' else request.args
        nik = data.get('nik') or '3673000000000000'
        nama = data.get('nama') or 'Warga Pemohon'
        pekerjaan = data.get('pekerjaan') or 'Buruh Harian'
        
        # Parse pendapatan safely
        raw_pend = data.get('pendapatan')
        try:
            pendapatan = float(str(raw_pend).replace('Rp', '').replace('.', '').replace(',', '').strip()) if raw_pend else 1500000.0
        except Exception:
            pendapatan = 1500000.0
            
        raw_tanggungan = data.get('tanggungan')
        try:
            tanggungan = int(raw_tanggungan) if raw_tanggungan else 3
        except Exception:
            tanggungan = 3
            
        rumah = data.get('rumah') or 'Semi Permanen'
        
        raw_listrik = data.get('listrik')
        try:
            listrik = int(raw_listrik) if raw_listrik else 900
        except Exception:
            listrik = 900
            
        hasil = data.get('hasil') or 'LAYAK (Disetujui)'
        sanggahan = data.get('sanggahan') or ''
        desil_dtsen = data.get('desil_dtsen') or 'Belum Terdaftar / Non-DTKS'
        jalur_sanggahan = data.get('jalur_sanggahan') or 'Normal'
        
        is_official = is_logged_in()
        op_name = session.get('operator_name', 'Drs. Hendro Wibowo, M.Si')
        op_nip = session.get('operator_nip', '19850314 201001 1 008')
        catatan_petugas = data.get('catatan_petugas', '')
        
        # Compute rich narrative XAI context
        calc_res = engine.predict_single(
            pekerjaan, pendapatan, tanggungan, rumah, listrik, sanggahan,
            desil_dtsen=desil_dtsen, jalur_sanggahan=jalur_sanggahan,
            nama=nama, nik=nik
        )
        complex_xai = calc_res.get('complex_xai')
        
        pdf_path = engine.generate_pdf(
            nik, nama, pekerjaan, pendapatan, tanggungan, rumah, listrik, hasil, sanggahan,
            is_official=is_official,
            operator_name=op_name,
            operator_nip=op_nip,
            catatan_petugas=catatan_petugas,
            desil_dtsen=desil_dtsen,
            jalur_sanggahan=jalur_sanggahan,
            complex_xai=complex_xai
        )
        with open(pdf_path, 'rb') as f:
            pdf_bytes = io.BytesIO(f.read())
        try:
            os.remove(pdf_path)
            temp_parent = os.path.dirname(pdf_path)
            if os.path.exists(temp_parent) and not os.listdir(temp_parent):
                os.rmdir(temp_parent)
        except Exception:
            pass
            
        safe_nik = "".join(c for c in str(nik) if c.isalnum() or c in ('-', '_')) or '3673000000000000'
        prefix_doc = "SK_Resmi_Dinsos" if is_official else "Simulasi_Mandiri_Warga"
        return send_file(
            pdf_bytes,
            as_attachment=True,
            download_name=f"{prefix_doc}_{safe_nik}.pdf",
            mimetype="application/pdf"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/batch-process', methods=['POST'])
def api_batch_process():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'Tidak ada file CSV yang diunggah'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'Nama file kosong'}), 400
    
    try:
        df_upload = pd.read_csv(file)
        batch_res = engine.process_batch(df_upload)
        
        # Save processed data on server temp storage to avoid 4KB browser cookie limits
        _save_session_batch(batch_res['full_df'].to_csv(index=False))
        session['has_custom_batch'] = True
        session['custom_batch_name'] = getattr(file, 'filename', 'data_warga.csv')
        session['custom_batch_count'] = batch_res['total_rows']
        
        return jsonify({
            'status': 'success',
            'summary': {
                'total_rows': batch_res['total_rows'],
                'layak_count': batch_res['layak_count'],
                'tidak_layak_count': batch_res['tidak_layak_count'],
                'layak_percentage': batch_res['layak_percentage'],
                'anomaly_dtsen_count': batch_res.get('anomaly_dtsen_count', 0),
                'sanggahan_approved_count': batch_res.get('sanggahan_approved_count', 0)
            },
            'preview': batch_res['preview'],
            'has_custom_batch': True,
            'custom_batch_count': batch_res['total_rows']
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/download-template')
def api_download_template():
    # Return sample CSV with DTSEN Decile and Sanggahan Status support
    sample_data = """NIK_Keluarga,Pekerjaan_Kepala_Keluarga,Pendapatan_Bln_Rp,Jml_Tanggungan,Kondisi_Rumah,Daya_Listrik_VA,Desil_DTSEN,Status_Sanggahan
3673100100200001,Buruh Harian,1200000,4,Tidak Permanen,450,Desil 2,Normal
3673100100200002,Buruh Harian,950000,5,Tidak Permanen,450,Desil 10,Sanggahan_Faktual_Disetujui
3673100100200003,Petani/Nelayan,1800000,3,Semi Permanen,900,Desil 3,Normal
3673100100200004,Karyawan Swasta,6500000,2,Permanen Layak,1300,Desil 8,Normal
3673100100200005,Tidak Bekerja,800000,5,Tidak Permanen,450,Desil 1,Normal
3673100100200006,PNS/TNI/POLRI,8000000,2,Permanen Mewah,2200,Desil 10,Normal"""
    output = io.BytesIO()
    output.write(sample_data.encode('utf-8'))
    output.seek(0)
    return send_file(
        output,
        mimetype="text/csv",
        as_attachment=True,
        download_name="template_batch_bansos_dtsen.csv"
    )

@app.route('/api/export-batch')
def api_export_batch():
    csv_data = _load_session_batch_csv()
    if not csv_data:
        return "Tidak ada hasil pemrosesan massal yang tersimpan.", 404
    output = io.BytesIO()
    output.write(csv_data.encode('utf-8'))
    output.seek(0)
    return send_file(
        output,
        mimetype="text/csv",
        as_attachment=True,
        download_name="rekap_hasil_verifikasi_bansos.csv"
    )

@app.route('/api/simulasi', methods=['POST'])
def api_simulasi():
    try:
        data = request.get_json() if request.is_json else request.form
        quota = int(data.get('quota', 300))
        
        has_custom = session.get('has_custom_batch', False)
        custom_csv = _load_session_batch_csv() if has_custom else None
        if has_custom and custom_csv:
            df_custom = pd.read_csv(io.StringIO(custom_csv))
            result = engine.simulate_budget(quota, custom_df=df_custom)
            result['is_custom'] = True
            result['custom_batch_name'] = session.get('custom_batch_name', '')
        else:
            if has_custom and not custom_csv:
                _clear_session_batch()
            result = engine.simulate_budget(quota)
            result['is_custom'] = False
            
        return jsonify({'status': 'success', 'data': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/quick-search-nik', methods=['GET'])
def api_quick_search_nik():
    nik = request.args.get('nik', '').strip()
    df = engine.df
    if nik:
        match = df[df['NIK_Keluarga'].astype(str).str.contains(nik)]
        if not match.empty:
            row = match.iloc[0].to_dict()
            return jsonify({'found': True, 'data': row})
    # Return random row as demo
    sample = df.sample(1).iloc[0].to_dict()
    return jsonify({'found': False, 'sample': sample})

@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[*] NALAR GovTech AI running on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
