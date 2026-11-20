/**
 * app.js - SangPintar Pro Version 1.0.0.0
 * Pure Vanilla JavaScript (Tanpa framework JS / No React / No Vue)
 * PT Ananda Technology Solution
 */

let activeStep = 1;
let currentRegisteredEmail = localStorage.getItem('sangpintar_user_email') || '';

// =========================================================================
// 1. STEP NAVIGATION
// =========================================================================
function switchWizardStep(stepNumber) {
    document.querySelectorAll('.step-panel').forEach(function(panel) {
        panel.classList.remove('active');
    });
    const targetPanel = document.getElementById('panel-step-' + stepNumber);
    if (targetPanel) {
        targetPanel.classList.add('active');
    }

    document.querySelectorAll('.steps .step').forEach(function(stepEl, index) {
        stepEl.classList.remove('active', 'completed');
        const num = index + 1;
        if (num < stepNumber) {
            stepEl.classList.add('completed');
        } else if (num === stepNumber) {
            stepEl.classList.add('active');
        }
    });

    activeStep = stepNumber;
    window.scrollTo({ top: 0, behavior: 'smooth' });

    if (stepNumber === 4 && currentRegisteredEmail) {
        checkUserLicenseStatus();
    }
}

// =========================================================================
// 2. STEP 1: VALIDASI KONEKSI HOST OPENCLAW & OLAMA
// =========================================================================
function validateHostsConnection() {
    const openclawHost = document.getElementById('openclaw-host').value.trim();
    const ollamaHost = document.getElementById('ollama-host').value.trim();

    if (!openclawHost || !ollamaHost) {
        alert('Mohon isi alamat host untuk OPENCLAW_HOST dan OLAMA_HOST.');
        return;
    }

    const resultsArea = document.getElementById('host-results-area');
    resultsArea.style.display = 'block';

    const badgeOpenclaw = document.getElementById('badge-openclaw');
    const badgeOllama = document.getElementById('badge-ollama');
    const successBox = document.getElementById('box-connect-success');
    const detailsBox = document.getElementById('box-connect-details');
    const btnNext = document.getElementById('btn-next-to-step2');

    badgeOpenclaw.className = 'status-indicator status-pending';
    document.getElementById('text-openclaw').textContent = 'OpenClaw: Memeriksa koneksi...';

    badgeOllama.className = 'status-indicator status-pending';
    document.getElementById('text-ollama').textContent = 'Ollama: Memeriksa koneksi...';

    successBox.style.display = 'none';
    detailsBox.innerHTML = '';

    fetch('/api/check-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            openclaw_host: openclawHost,
            ollama_host: ollamaHost
        })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        let anyConnected = false;

        // OpenClaw UI
        if (data.openclaw_connected) {
            badgeOpenclaw.className = 'status-indicator status-success';
            document.getElementById('text-openclaw').textContent = 'OpenClaw: ' + data.openclaw_status + ' ✅';
            anyConnected = true;
        } else {
            badgeOpenclaw.className = 'status-indicator status-error';
            document.getElementById('text-openclaw').textContent = 'OpenClaw: ' + data.openclaw_status;
        }

        // Ollama UI
        if (data.ollama_connected) {
            badgeOllama.className = 'status-indicator status-success';
            document.getElementById('text-ollama').textContent = 'Ollama: ' + data.ollama_status + ' ✅';
            anyConnected = true;
        } else {
            badgeOllama.className = 'status-indicator status-error';
            document.getElementById('text-ollama').textContent = 'Ollama: ' + data.ollama_status;
        }

        // Sesuai requirement: "apabila berhasil konek berwarna hijau bertuliskan conect succees"
        if (data.success) {
            successBox.style.display = 'flex';
            detailsBox.innerHTML = '<div class="alert alert-success" style="font-size:0.9rem;">' +
                                   '📡 Detail: ' + (data.message || 'Koneksi AI Host terhubung dengan baik!') +
                                   '</div>';
            btnNext.disabled = false;
        } else if (anyConnected) {
            successBox.style.display = 'flex';
            detailsBox.innerHTML = '<div class="alert alert-success" style="font-size:0.9rem;">' +
                                   '📡 Salah satu service aktif: ' + data.message +
                                   '</div>';
            btnNext.disabled = false;
        } else {
            successBox.style.display = 'none';
            detailsBox.innerHTML = '<div class="alert alert-error" style="font-size:0.9rem;">' +
                                   '❌ Gagal terhubung: ' + data.message +
                                   ' (Pastikan OpenClaw / Ollama berjalan di latar belakang)' +
                                   '</div>';
            btnNext.disabled = true;
        }
    })
    .catch(function(err) {
        badgeOpenclaw.className = 'status-indicator status-error';
        badgeOllama.className = 'status-indicator status-error';
        detailsBox.innerHTML = '<div class="alert alert-error">❌ Network Error: ' + err.message + '</div>';
    });
}

// =========================================================================
// 3. STEP 2: CEK TOKEN & START BOT TELEGRAM
// =========================================================================
function verifyBotToken() {
    const token = document.getElementById('bot-token').value.trim();
    if (!token) {
        alert('Mohon masukkan Token Bot Telegram terlebih dahulu.');
        return;
    }

    const resultsArea = document.getElementById('bot-results-area');
    resultsArea.style.display = 'block';

    const badgeBot = document.getElementById('badge-bot');
    const msgBox = document.getElementById('box-bot-message');
    const btnStart = document.getElementById('btn-start-telegram-bot');
    const btnNext = document.getElementById('btn-next-to-step3');

    badgeBot.className = 'status-indicator status-pending';
    document.getElementById('text-bot').textContent = 'Memverifikasi Token ke Telegram API...';
    msgBox.innerHTML = '';

    fetch('/api/check-bot-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: token })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        if (data.valid) {
            badgeBot.className = 'status-indicator status-success';
            document.getElementById('text-bot').textContent = 'Bot Terverifikasi: ' + data.bot_name + ' (@' + data.bot_username + ') ✅';
            msgBox.innerHTML = '<div class="alert alert-success">' +
                               '✅ Token valid! Bot <strong>' + data.bot_name + '</strong> terdeteksi aktif di Telegram. Siap dijalankan!' +
                               '</div>';
            btnStart.disabled = false;
            btnNext.disabled = false;
        } else {
            badgeBot.className = 'status-indicator status-error';
            document.getElementById('text-bot').textContent = 'Token Bot Tidak Valid ❌';
            msgBox.innerHTML = '<div class="alert alert-error">❌ ' + data.message + '</div>';
            btnStart.disabled = true;
            btnNext.disabled = true;
        }
    })
    .catch(function(err) {
        badgeBot.className = 'status-indicator status-error';
        document.getElementById('text-bot').textContent = 'Gagal menghubungi server';
        msgBox.innerHTML = '<div class="alert alert-error">❌ Error: ' + err.message + '</div>';
    });
}

function startTelegramBot() {
    const token = document.getElementById('bot-token').value.trim();
    const btnStart = document.getElementById('btn-start-telegram-bot');
    const msgBox = document.getElementById('box-bot-message');

    btnStart.disabled = true;
    btnStart.textContent = '⏳ Memulai Bot...';

    fetch('/api/start-bot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: token })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        if (data.success) {
            btnStart.className = 'btn btn-success';
            btnStart.textContent = '🚀 Bot Sedang Berjalan (Active)';
            msgBox.innerHTML = '<div class="alert alert-success">✅ ' + data.message + '</div>';
            document.getElementById('btn-next-to-step3').disabled = false;
        } else {
            btnStart.disabled = false;
            btnStart.textContent = '🚀 Coba Start Bot Lagi';
            msgBox.innerHTML = '<div class="alert alert-error">❌ ' + data.message + '</div>';
        }
    })
    .catch(function(err) {
        btnStart.disabled = false;
        btnStart.textContent = '🚀 Start Bot SangPintar';
        msgBox.innerHTML = '<div class="alert alert-error">❌ Error: ' + err.message + '</div>';
    });
}

// =========================================================================
// 4. STEP 3: MODAL QRCODE PAYMENT & FORM USER DATA
// =========================================================================
function openQRPaymentModal() {
    const modal = document.getElementById('qr-payment-modal');
    if (modal) modal.classList.add('show');
}

function closeQRPaymentModal() {
    const modal = document.getElementById('qr-payment-modal');
    if (modal) modal.classList.remove('show');
}

function handleFileSelected(input) {
    const file = input.files[0];
    if (!file) return;

    document.getElementById('file-selected-name').textContent = '📎 File terpilih: ' + file.name + ' (' + Math.round(file.size / 1024) + ' KB)';
    document.getElementById('file-label-text').textContent = '✅ File dipilih: ' + file.name;

    if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const preview = document.getElementById('image-preview');
            preview.src = e.target.result;
            preview.style.display = 'block';
        };
        reader.readAsDataURL(file);
    }
}

// Form Submission Event Listener
document.addEventListener('DOMContentLoaded', function() {
    const userForm = document.getElementById('wizard-user-form');
    if (userForm) {
        userForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const nama = document.getElementById('form-nama').value.trim();
            const email = document.getElementById('form-email').value.trim();
            const proof = document.getElementById('form-proof').files[0];

            if (!nama || !email || !proof) {
                alert('Nama User, Email, dan Bukti Upload Gambar wajib diisi!');
                return;
            }

            const formData = new FormData(userForm);
            const statusArea = document.getElementById('submit-status-area');
            statusArea.innerHTML = '<div class="alert alert-info">⏳ Mengunggah bukti pembayaran & menyimpan data user...</div>';

            fetch('/api/submit-user-data', {
                method: 'POST',
                body: formData
            })
            .then(function(res) { return res.json(); })
            .then(function(data) {
                if (data.success) {
                    currentRegisteredEmail = email;
                    localStorage.setItem('sangpintar_user_email', email);

                    statusArea.innerHTML = '<div class="alert alert-success">' +
                                           '✅ ' + data.message + '<br>' +
                                           '<small>Data Anda telah tercatat dan siap divalidasi oleh Admin di Admin Panel Dashboard.</small>' +
                                           '</div>';
                    document.getElementById('btn-next-to-step4').disabled = false;

                    // Otomatis pindah ke Step 4 setelah 1.5 detik
                    setTimeout(function() {
                        switchWizardStep(4);
                    }, 1500);
                } else {
                    statusArea.innerHTML = '<div class="alert alert-error">❌ ' + data.message + '</div>';
                }
            })
            .catch(function(err) {
                statusArea.innerHTML = '<div class="alert alert-error">❌ Error: ' + err.message + '</div>';
            });
        });
    }

    // Prefill email if exists
    if (currentRegisteredEmail) {
        const emailInput = document.getElementById('form-email');
        if (emailInput && !emailInput.value) {
            emailInput.value = currentRegisteredEmail;
        }
    }
});

// =========================================================================
// 5. STEP 4: KODE LISENSI & VALIDASI PEMBAYARAN
// =========================================================================
function checkUserLicenseStatus() {
    const email = currentRegisteredEmail || (document.getElementById('form-email') ? document.getElementById('form-email').value.trim() : '');
    if (!email) {
        return;
    }

    const pendingBox = document.getElementById('license-pending-box');
    const successBox = document.getElementById('license-success-box');
    const codeDisplay = document.getElementById('display-license-code');

    fetch('/api/check-license-status?email=' + encodeURIComponent(email))
    .then(function(res) { return res.json(); })
    .then(function(data) {
        if (data.validated && data.license_code) {
            pendingBox.style.display = 'none';
            successBox.style.display = 'block';
            codeDisplay.textContent = data.license_code;

            const redeemInput = document.getElementById('input-redeem-license');
            if (redeemInput) redeemInput.value = data.license_code;
        } else {
            pendingBox.style.display = 'flex';
            successBox.style.display = 'none';
        }
    })
    .catch(function(err) {
        console.error('Error checking license:', err);
    });
}

function copyGeneratedLicenseCode() {
    const codeEl = document.getElementById('display-license-code');
    const codeText = codeEl.textContent.trim();
    if (!codeText) return;

    // Requirement:
    // "Selamat pembelian kode lisensi sukses, mohon copy paste code licence ini Ke Bot SangPintar di front end nya: Code Licence: <codelicence yang sudah digenerate>"
    const fullTextToCopy = "Selamat pembelian kode lisensi sukses, mohon copy paste code licence ini Ke Bot SangPintar di front end nya: Code Licence: " + codeText;

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(fullTextToCopy).then(function() {
            const btn = document.getElementById('btn-copy-code');
            btn.textContent = '✅ Berhasil Dicopy!';
            btn.className = 'btn btn-outline';
            setTimeout(function() {
                btn.textContent = '📋 Copy Code Licence';
                btn.className = 'btn btn-success';
            }, 2500);
        });
    } else {
        // Fallback copy
        const tempInput = document.createElement('textarea');
        tempInput.value = fullTextToCopy;
        document.body.appendChild(tempInput);
        tempInput.select();
        document.execCommand('copy');
        document.body.removeChild(tempInput);
        alert('Code Licence berhasil disalin ke clipboard!');
    }
}

function redeemLicenseOnFrontend() {
    const input = document.getElementById('input-redeem-license');
    const code = input ? input.value.trim() : '';
    const resultArea = document.getElementById('redeem-result-area');

    if (!code) {
        alert('Masukkan kode lisensi.');
        return;
    }

    resultArea.innerHTML = '<div class="alert alert-info">⏳ Mengaktifkan kode lisensi...</div>';

    fetch('/api/redeem-license', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            license_code: code,
            email: currentRegisteredEmail
        })
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        if (data.success) {
            resultArea.innerHTML = '<div class="alert alert-success">✅ ' + data.message + '</div>';
        } else {
            resultArea.innerHTML = '<div class="alert alert-error">❌ ' + data.message + '</div>';
        }
    })
    .catch(function(err) {
        resultArea.innerHTML = '<div class="alert alert-error">❌ Error: ' + err.message + '</div>';
    });
}
