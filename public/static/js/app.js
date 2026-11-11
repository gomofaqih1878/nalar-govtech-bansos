// static/js/app.js - NALAR GovTech AI Client Interactivity

let limeChartInstance = null;

// Initialize Lucide Icons if available
document.addEventListener('DOMContentLoaded', () => {
    if (window.lucide) {
        window.lucide.createIcons();
    }
    
    // Auto-setup demo buttons if present
    setupDemoPresets();
    setupBatchUploader();
    setupSimulasiSlider();
});

// --- DEMO PRESETS FOR QUICK TESTING ---
const DEMO_CASES = {
    layak: {
        nik: '3673892100450012',
        nama: 'Ahmad Supardi',
        desil_dtsen: 'Desil 2 (Fakir Miskin)',
        jalur_sanggahan: 'Pemeriksaan Reguler',
        pekerjaan: 'Buruh Harian',
        pendapatan: 1200000,
        tanggungan: 4,
        rumah: 'Tidak Permanen',
        listrik: 450,
        sanggahan: 'Mohon bantuannya untuk biaya makan anak-anak dan kebutuhan sekolah dasar.'
    },
    pns: {
        nik: '3673104500980004',
        nama: 'Drs. Hendro Wibowo',
        desil_dtsen: 'Desil 10 (Sangat Mampu / 10% Teratas)',
        jalur_sanggahan: 'Pemeriksaan Reguler',
        pekerjaan: 'PNS/TNI/POLRI',
        pendapatan: 7500000,
        tanggungan: 2,
        rumah: 'Permanen Mewah',
        listrik: 2200,
        sanggahan: 'Apakah ada kuota subsidi tambahan untuk keluarga kami?'
    },
    marjinal: {
        nik: '3673551200870023',
        nama: 'Siti Aminah',
        desil_dtsen: 'Desil 3 (Hampir Miskin Prioritas)',
        jalur_sanggahan: 'Pemeriksaan Reguler',
        pekerjaan: 'Petani/Nelayan',
        pendapatan: 1900000,
        tanggungan: 5,
        rumah: 'Semi Permanen',
        listrik: 900,
        sanggahan: 'Kami sangat kecewa kenapa bulan lalu bansos beras kami terhenti padahal kondisi sedang gagal panen.'
    },
    sengketa_dtsen: {
        nik: '3673091100230004',
        nama: 'Ibu Siti Rohayah (Sanggahan DTSEN)',
        desil_dtsen: 'Desil 10 (Sangat Mampu / 10% Teratas)',
        jalur_sanggahan: 'Sanggahan / Koreksi Exclusion Error DTSEN',
        pekerjaan: 'Buruh Harian',
        pendapatan: 900000,
        tanggungan: 5,
        rumah: 'Tidak Permanen',
        listrik: 450,
        sanggahan: 'Di data DTSEN kelurahan saya tercatat Desil 10 (mampu) padahal suami sudah meninggal dan kami tinggal di rumah bilik bambu beralas tanah rusak. Mohon verifikasi faktual lapangan dan koreksi desil.'
    }
};

function setupDemoPresets() {
    window.fillDemoForm = function(type, autoSubmit = true) {
        const data = DEMO_CASES[type] || DEMO_CASES.layak;
        const form = document.getElementById('formVerifikasi');
        if (!form) return;
        
        form.elements['nik'].value = data.nik;
        form.elements['nama'].value = data.nama;
        form.elements['pekerjaan'].value = data.pekerjaan;
        form.elements['pendapatan'].value = data.pendapatan;
        form.elements['tanggungan'].value = data.tanggungan;
        form.elements['rumah'].value = data.rumah;
        form.elements['listrik'].value = data.listrik;
        form.elements['sanggahan'].value = data.sanggahan;
        
        if (form.elements['desil_dtsen'] && data.desil_dtsen) {
            form.elements['desil_dtsen'].value = data.desil_dtsen;
        }
        if (form.elements['jalur_sanggahan'] && data.jalur_sanggahan) {
            form.elements['jalur_sanggahan'].value = data.jalur_sanggahan;
        }
        
        // Update tanggungan label if present
        const tanggunganVal = document.getElementById('tanggunganDisplay');
        if (tanggunganVal) {
            tanggunganVal.innerText = data.tanggungan + ' Orang';
        }
        
        // Trigger live checks
        checkFormPolicies();
        
        // Highlight form smoothly
        form.classList.add('ring-2', 'ring-amber-500', 'transition-all');
        setTimeout(() => form.classList.remove('ring-2', 'ring-amber-500'), 800);
        
        // Automatically submit for instantaneous feedback
        if (autoSubmit) {
            submitVerification();
        }
    };
}

// Live policy warnings
function checkFormPolicies() {
    const form = document.getElementById('formVerifikasi');
    if (!form) return;
    
    const pekerjaan = form.elements['pekerjaan'].value;
    const listrik = parseInt(form.elements['listrik'].value);
    const warningBox = document.getElementById('livePolicyWarnings');
    
    if (!warningBox) return;
    
    let html = '';
    if (pekerjaan === 'PNS/TNI/POLRI') {
        html += `
            <div class="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-xs flex items-center gap-2 mb-2">
                <i data-lucide="alert-triangle" class="w-4 h-4 flex-shrink-0 text-red-600"></i>
                <span><strong>Blokir Mutlak:</strong> Sesuai Surat Edaran KPK & Regulasi Kemensos, ASN/TNI/POLRI dilarang menerima bansos APBN/APBD.</span>
            </div>
        `;
    }
    if (listrik >= 1300) {
        html += `
            <div class="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-xs flex items-center gap-2 mb-2">
                <i data-lucide="zap-off" class="w-4 h-4 flex-shrink-0 text-amber-600"></i>
                <span><strong>Peringatan Daya Listrik:</strong> Daya terpasang &ge; 1.300 VA tergolong tarif non-subsidi rumah tangga mampu.</span>
            </div>
        `;
    }
    
    warningBox.innerHTML = html;
    if (window.lucide) window.lucide.createIcons();
}

// Single prediction submission
async function submitVerification(event) {
    if (event) event.preventDefault();
    const form = document.getElementById('formVerifikasi');
    if (!form) return;
    
    const btn = document.getElementById('btnSubmitVerifikasi');
    const originalBtnText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `
        <svg class="animate-spin h-5 w-5 text-white inline-block mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
        </svg>
        Memeriksa Data & Bukti Kelayakan...
    `;
    
    const payload = {
        nik: form.elements['nik'].value,
        nama: form.elements['nama'].value,
        pekerjaan: form.elements['pekerjaan'].value,
        pendapatan: parseFloat(form.elements['pendapatan'].value),
        tanggungan: parseInt(form.elements['tanggungan'].value),
        rumah: form.elements['rumah'].value,
        listrik: parseInt(form.elements['listrik'].value),
        sanggahan: form.elements['sanggahan'].value,
        desil_dtsen: form.elements['desil_dtsen'] ? form.elements['desil_dtsen'].value : 'Belum Terdaftar / Non-DTKS',
        jalur_sanggahan: form.elements['jalur_sanggahan'] ? form.elements['jalur_sanggahan'].value : 'Pemeriksaan Reguler'
    };
    
    try {
        const response = await fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const res = await response.json();
        if (res.status === 'success') {
            displayVerificationResults(payload, res.data);
        } else {
            alert('Gagal melakukan verifikasi: ' + (res.message || 'Terjadi kesalahan'));
        }
    } catch (err) {
        console.error(err);
        alert('Terjadi kesalahan koneksi server saat menganalisis data.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalBtnText;
        if (window.lucide) window.lucide.createIcons();
    }
}

function syncPdfFormData() {
    const mainForm = document.getElementById('formVerifikasi');
    const pdfForm = document.getElementById('formDownloadPdf');
    if (!mainForm || !pdfForm) return;
    
    pdfForm.elements['nik'].value = mainForm.elements['nik']?.value || '3673000000000000';
    pdfForm.elements['nama'].value = mainForm.elements['nama']?.value || 'Warga Pemohon';
    pdfForm.elements['pekerjaan'].value = mainForm.elements['pekerjaan']?.value || 'Buruh Harian';
    pdfForm.elements['pendapatan'].value = mainForm.elements['pendapatan']?.value || '1500000';
    pdfForm.elements['tanggungan'].value = mainForm.elements['tanggungan']?.value || '3';
    pdfForm.elements['rumah'].value = mainForm.elements['rumah']?.value || 'Semi Permanen';
    pdfForm.elements['listrik'].value = mainForm.elements['listrik']?.value || '900';
    pdfForm.elements['sanggahan'].value = mainForm.elements['sanggahan']?.value || '';
    if (pdfForm.elements['catatan_petugas']) {
        pdfForm.elements['catatan_petugas'].value = mainForm.elements['catatan_petugas']?.value || '';
    }
    if (pdfForm.elements['desil_dtsen']) {
        pdfForm.elements['desil_dtsen'].value = mainForm.elements['desil_dtsen']?.value || 'Belum Terdaftar';
    }
    if (pdfForm.elements['jalur_sanggahan']) {
        pdfForm.elements['jalur_sanggahan'].value = mainForm.elements['jalur_sanggahan']?.value || 'Normal';
    }
    
    // Check if result badge exists to get latest verdict
    const statusBadge = document.getElementById('resStatusBadge');
    if (statusBadge && statusBadge.innerText) {
        pdfForm.elements['hasil'].value = statusBadge.innerText.includes('LAYAK') ? 'LAYAK (Disetujui)' : 'TIDAK LAYAK (Ditolak)';
    } else if (!pdfForm.elements['hasil'].value) {
        pdfForm.elements['hasil'].value = 'LAYAK (Disetujui)';
    }
}
window.syncPdfFormData = syncPdfFormData;

function displayVerificationResults(input, data) {
    const resultContainer = document.getElementById('verificationResultContainer');
    const waitingPlaceholder = document.getElementById('waitingPlaceholder');
    
    if (waitingPlaceholder) waitingPlaceholder.classList.add('hidden');
    if (resultContainer) resultContainer.classList.remove('hidden');
    
    const isLayak = data.status === 'LAYAK';
    
    // Status Badge
    const statusBadge = document.getElementById('resStatusBadge');
    if (statusBadge) {
        statusBadge.className = isLayak 
            ? 'px-4 py-1.5 rounded-full text-sm font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center gap-1.5'
            : 'px-4 py-1.5 rounded-full text-sm font-bold bg-rose-100 text-rose-800 border border-rose-300 flex items-center gap-1.5';
        statusBadge.innerHTML = isLayak
            ? '<i data-lucide="check-circle" class="w-4 h-4"></i> LAYAK MENERIMA BANSOS'
            : '<i data-lucide="x-circle" class="w-4 h-4"></i> TIDAK LAYAK (REJECT)';
    }
    
    // Confidence & probabilities
    const probLayakText = document.getElementById('resProbLayak');
    if (probLayakText) probLayakText.innerText = (data.prob_layak * 100).toFixed(1) + '%';
    
    const probBar = document.getElementById('resProbBar');
    if (probBar) {
        probBar.style.width = (data.prob_layak * 100) + '%';
        probBar.className = isLayak
            ? 'h-2.5 rounded-full bg-emerald-500 transition-all duration-700'
            : 'h-2.5 rounded-full bg-rose-500 transition-all duration-700';
    }
    
    // Sentiment Badge
    const sentimentBadge = document.getElementById('resSentimentBadge');
    if (sentimentBadge && data.sentiment) {
        sentimentBadge.innerText = data.sentiment.label;
        sentimentBadge.className = `inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${
            data.sentiment.color === 'red' ? 'bg-rose-100 text-rose-800' :
            data.sentiment.color === 'emerald' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-800'
        }`;
    }

    // Anomali DTSEN Banner
    const anomalyBanner = document.getElementById('resDtsenAnomalyBanner');
    const anomalyText = document.getElementById('resDtsenAnomalyText');
    if (anomalyBanner && anomalyText) {
        if (data.complex_xai && data.complex_xai.is_dtsen_anomaly) {
            anomalyBanner.classList.remove('hidden');
            anomalyText.innerText = data.complex_xai.dtsen_anomaly_narrative || 'Terdeteksi diskrepansi data antara registrasi DTSEN dan kondisi empiris lapangan.';
        } else {
            anomalyBanner.classList.add('hidden');
        }
    }

    // Populate Complex Explainable AI (LIME) Extended Narratives
    if (data.complex_xai) {
        const cx = data.complex_xai;
        
        // Executive Summary
        const elExec = document.getElementById('resExecutiveSummary');
        if (elExec) elExec.innerText = cx.executive_summary_narrative || '';

        // 4 Pillar Narratives
        const elIncomeNarr = document.getElementById('resIncomeNarrative');
        if (elIncomeNarr) elIncomeNarr.innerText = cx.income_assessment || '';

        const elHousingNarr = document.getElementById('resHousingNarrative');
        if (elHousingNarr) elHousingNarr.innerText = cx.housing_assessment || '';

        const elElecNarr = document.getElementById('resElectricityNarrative');
        if (elElecNarr) elElecNarr.innerText = cx.electricity_assessment || '';

        const elProfNarr = document.getElementById('resProfessionNarrative');
        if (elProfNarr) elProfNarr.innerText = cx.profession_assessment || '';

        // Poverty Category
        const elPoverty = document.getElementById('resPovertyCategory');
        if (elPoverty) elPoverty.innerText = cx.poverty_category;

        // DTSEN Section
        const elDtsenNarr = document.getElementById('resDtsenAuditNarrative');
        if (elDtsenNarr) elDtsenNarr.innerText = cx.dtsen_anomaly_narrative || '';

        // Counterfactual
        const elCountHead = document.getElementById('resCounterfactualHeadline');
        if (elCountHead) elCountHead.innerText = cx.counterfactual?.headline || 'Batas Toleransi Kelayakan & Analisis Sensitivitas (What-If)';

        const elCountDet = document.getElementById('resCounterfactualDetails');
        if (elCountDet) elCountDet.innerText = cx.counterfactual?.details || '';

        // Scientific Justification
        const elSciJust = document.getElementById('resScientificJustification');
        if (elSciJust) elSciJust.innerText = cx.scientific_justification || '';
    }
    
    // Setup PDF Download Form Hidden Values
    const pdfForm = document.getElementById('formDownloadPdf');
    if (pdfForm) {
        pdfForm.elements['nik'].value = input.nik;
        pdfForm.elements['nama'].value = input.nama;
        pdfForm.elements['pekerjaan'].value = input.pekerjaan;
        pdfForm.elements['pendapatan'].value = input.pendapatan;
        pdfForm.elements['tanggungan'].value = input.tanggungan;
        pdfForm.elements['rumah'].value = input.rumah;
        pdfForm.elements['listrik'].value = input.listrik;
        pdfForm.elements['hasil'].value = isLayak ? 'LAYAK (Disetujui)' : 'TIDAK LAYAK (Ditolak)';
        pdfForm.elements['sanggahan'].value = input.sanggahan;
        if (pdfForm.elements['desil_dtsen']) {
            pdfForm.elements['desil_dtsen'].value = input.desil_dtsen || 'Belum Terdaftar';
        }
        if (pdfForm.elements['jalur_sanggahan']) {
            pdfForm.elements['jalur_sanggahan'].value = input.jalur_sanggahan || 'Normal';
        }
    }
    
    // Render LIME Bar Chart
    renderLimeChart(data.explanation);
    
    // Re-initialize icons
    if (window.lucide) window.lucide.createIcons();
    
    // Scroll to results smoothly
    resultContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function renderLimeChart(explanationData) {
    const ctx = document.getElementById('limeChartCanvas');
    if (!ctx) return;
    
    if (limeChartInstance) {
        limeChartInstance.destroy();
    }
    
    const labels = explanationData.map(item => item.feature);
    const weights = explanationData.map(item => item.weight);
    const backgroundColors = weights.map(w => w > 0 ? '#10B981' : '#EF4444');
    
    limeChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Pengaruh Faktor Kondisi Keluarga',
                data: weights,
                backgroundColor: backgroundColors,
                borderRadius: 8,
                borderSkipped: false
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const val = context.raw;
                            return (val > 0 ? '+ ' : '') + val + (val > 0 ? ' (Memperkuat Hak Bantuan)' : ' (Mengurangi Hak Bantuan)');
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: '#F3F4F6' },
                    ticks: { color: '#6B7280' }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#374151', font: { weight: '500' } }
                }
            }
        }
    });
}

// --- BATCH PROCESSOR ---
function setupBatchUploader() {
    const fileInput = document.getElementById('batchFileInput');
    const uploadArea = document.getElementById('batchDropArea');
    if (!fileInput || !uploadArea) return;
    
    uploadArea.addEventListener('click', () => fileInput.click());
    
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('border-teal-500', 'bg-teal-50/50');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('border-teal-500', 'bg-teal-50/50');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('border-teal-500', 'bg-teal-50/50');
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleBatchUpload();
        }
    });
    
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleBatchUpload();
        }
    });
}

async function handleBatchUpload() {
    const fileInput = document.getElementById('batchFileInput');
    if (!fileInput || fileInput.files.length === 0) return;
    
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    const loadingState = document.getElementById('batchLoadingState');
    const resultState = document.getElementById('batchResultState');
    
    if (loadingState) loadingState.classList.remove('hidden');
    if (resultState) resultState.classList.add('hidden');
    
    try {
        const response = await fetch('/api/batch-process', {
            method: 'POST',
            body: formData
        });
        
        const res = await response.json();
        if (res.status === 'success') {
            displayBatchResults(res.summary, res.preview);
        } else {
            alert('Gagal memproses file: ' + (res.message || 'Format tidak sesuai'));
        }
    } catch (err) {
        console.error(err);
        alert('Gagal mengunggah file. Pastikan file berformat CSV.');
    } finally {
        if (loadingState) loadingState.classList.add('hidden');
    }
}

function displayBatchResults(summary, preview) {
    const resultState = document.getElementById('batchResultState');
    if (!resultState) return;
    resultState.classList.remove('hidden');
    
    document.getElementById('bTotalRows').innerText = summary.total_rows.toLocaleString();
    document.getElementById('bLayakCount').innerText = summary.layak_count.toLocaleString();
    document.getElementById('bTidakLayakCount').innerText = summary.tidak_layak_count.toLocaleString();
    document.getElementById('bLayakPercentage').innerText = summary.layak_percentage + '%';
    
    const anomalyEl = document.getElementById('bAnomalyCount');
    if (anomalyEl) {
        anomalyEl.innerText = (summary.anomaly_dtsen_count || 0).toLocaleString();
    }
    
    const tbody = document.getElementById('batchTableBody');
    if (tbody && preview) {
        tbody.innerHTML = preview.map((row, idx) => {
            const isAnomaly = (row.Status_Audit_DTSEN || '').includes('Anomali');
            const isSanggahan = (row.Status_Audit_DTSEN || '').includes('Sanggahan');
            
            return `
                <tr class="hover:bg-stone-50/80 transition-colors ${isAnomaly ? 'bg-purple-50/30' : ''}">
                    <td class="px-3.5 py-3 text-xs font-mono font-bold text-stone-600">${row.Peringkat_Kelayakan || ('#' + (idx + 1))}</td>
                    <td class="px-3.5 py-3 text-xs font-mono font-medium text-stone-800">${row.NIK_Keluarga}</td>
                    <td class="px-3.5 py-3 text-xs text-stone-700">${row.Pekerjaan_Kepala_Keluarga}</td>
                    <td class="px-3.5 py-3 text-xs text-stone-700">Rp ${Number(row.Pendapatan_Bln_Rp).toLocaleString()}</td>
                    <td class="px-3.5 py-3 text-xs text-stone-700">${row.Jml_Tanggungan} Jiwa</td>
                    <td class="px-3.5 py-3 text-xs">
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold ${
                            row.Status_Rekomendasi === 'LAYAK' 
                                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' 
                                : 'bg-rose-100 text-rose-800 border border-rose-300'
                        }">
                            ${row.Status_Rekomendasi}
                        </span>
                    </td>
                    <td class="px-3.5 py-3 text-xs font-mono font-bold text-stone-700">${row.Skor_Kemiskinan}</td>
                    <td class="px-3.5 py-3 text-xs">
                        <span class="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-semibold ${
                            isAnomaly ? 'bg-purple-100 text-purple-900 border border-purple-300' :
                            isSanggahan ? 'bg-sky-100 text-sky-900 border border-sky-300' :
                            'bg-stone-100 text-stone-600'
                        }">
                            ${row.Status_Audit_DTSEN || 'Normal'}
                        </span>
                    </td>
                </tr>
            `;
        }).join('');
    }
    
    if (window.lucide) window.lucide.createIcons();
}

// --- APBN SIMULATION SLIDER ---
function setupSimulasiSlider() {
    const slider = document.getElementById('simQuotaSlider');
    const displayVal = document.getElementById('simQuotaDisplay');
    if (!slider || !displayVal) return;
    
    let debounceTimer;
    slider.addEventListener('input', (e) => {
        const val = e.target.value;
        displayVal.innerText = Number(val).toLocaleString() + ' Keluarga';
        
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            fetchSimulasi(val);
        }, 250);
    });
}

async function fetchSimulasi(quota) {
    try {
        const res = await fetch('/api/simulasi', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ quota: parseInt(quota) })
        });
        const data = await res.json();
        if (data.status === 'success') {
            updateSimulasiUI(data.data);
        }
    } catch (e) {
        console.error('Error fetching simulasi:', e);
    }
}

function updateSimulasiUI(sim) {
    if (document.getElementById('simCutoffScore')) {
        document.getElementById('simCutoffScore').innerText = sim.cutoff_score;
    }
    if (document.getElementById('simAvgIncome')) {
        document.getElementById('simAvgIncome').innerText = sim.avg_income_admitted;
    }
    if (document.getElementById('simMonthlyBudget')) {
        document.getElementById('simMonthlyBudget').innerText = sim.total_monthly_budget;
    }
    if (document.getElementById('simAnnualBudget')) {
        document.getElementById('simAnnualBudget').innerText = sim.total_annual_budget;
    }
    if (document.getElementById('simBufferQuota')) {
        document.getElementById('simBufferQuota').innerText = (sim.buffer_quota || 0) + ' KK';
    }
    if (document.getElementById('simBufferBudget')) {
        document.getElementById('simBufferBudget').innerText = (sim.buffer_monthly_budget || 'Rp 0') + '/bln cadangan';
    }
    
    const tbodyAdmitted = document.getElementById('simAdmittedTableBody');
    if (tbodyAdmitted && sim.admitted_preview) {
        tbodyAdmitted.innerHTML = sim.admitted_preview.map((row, idx) => `
            <tr class="hover:bg-emerald-50/40">
                <td class="px-4 py-2.5 text-xs font-mono text-emerald-800 font-medium">#${idx + 1}</td>
                <td class="px-4 py-2.5 text-xs font-mono">${row.NIK_Keluarga}</td>
                <td class="px-4 py-2.5 text-xs">${row.Pekerjaan_Kepala_Keluarga}</td>
                <td class="px-4 py-2.5 text-xs">Rp ${Number(row.Pendapatan_Bln_Rp).toLocaleString()}</td>
                <td class="px-4 py-2.5 text-xs font-semibold text-emerald-700">${row.Skor_Kemiskinan}</td>
                <td class="px-4 py-2.5 text-xs">
                    <span class="px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                        (row.Keputusan || '').includes('Buffer')
                            ? 'bg-purple-100 text-purple-900 border border-purple-200'
                            : 'bg-emerald-100 text-emerald-800'
                    }">
                        ${row.Keputusan || 'Lolos Kuota'}
                    </span>
                </td>
            </tr>
        `).join('');
    }
}
