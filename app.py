"""
app.py - Backend Server Flask & Runner Bot Telegram SangPintar Pro Version 1.0.0.0
PT Ananda Technology Solution
"""
import os
import sys
import base64
import threading
import asyncio
import requests
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    session,
    send_from_directory,
    flash
)
from werkzeug.utils import secure_filename


def _d(b64_str: str, key: int = 0x5A) -> str:
    """Decode string ter-obfuscate saat runtime dengan auto-padding dan sanitasi spasi."""
    try:
        s = b64_str.strip().replace(" ", "").replace("\n", "").replace("\r", "")
        padding = (4 - len(s) % 4) % 4
        raw = base64.b64decode((s + "=" * padding).encode("utf-8"))
        return bytes(b ^ key for b in raw).decode("utf-8", errors="replace")
    except Exception:
        return ""


# Konfigurasi hardcode ter-obfuscate (sinkron dengan database.py)
_SECRETKEY = os.getenv("SECRETKEY", _d("GgwzLjNua2g="))
_FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", _d("GgwzLjNua2h3KTs0PSozNC47KHcpPzkoPy4="))
_PORT = int(os.getenv("PORT", 5100))
_TOKEN_BOT_TELEGRAM = os.getenv("TOKEN_BOT_TELEGRAM", _d("YmNta2trY2lraWAbGxIODhM+bjYVLDMTPisTFRQpHCI/MzsibRsxMm8cOSAtHw=="))
_OPENCLAW_HOST = os.getenv("OPENCLAW_HOST", _d("Mi4uKmB1dWtobXRqdGp0a2BrYm1iY3U="))
_OLAMA_HOST = os.getenv("OLAMA_HOST", os.getenv("OLLAMA_HOST", _d("Mi4uKmB1dWtobXRqdGp0a2Bra25pbg==")))
_SUPABASE_URL = os.getenv("SUPABASE_URL", _d("Mi4uKilgdXUqNj04MSk/ICMvNzwzMDU0PywjMnQpLyo7ODspP3Q5NQ=="))
_SUPABASE_KEY = os.getenv("SUPABASE_KEY", _d("KTgFKi84NjMpMjs4Nj8FPQMLCCk2NC4tOxR3HDRrCjEyN245PQUyawIsEms7IA=="))
_SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD", _d("Ghs9LykuLylua2g="))
_AUTO_START_BOT = True

# Set ke environment internal proses jika modul lain (seperti bot/database) memerlukannya
os.environ["SECRETKEY"] = _SECRETKEY
os.environ["FLASK_SECRET_KEY"] = _FLASK_SECRET_KEY
os.environ["PORT"] = str(_PORT)
os.environ["TOKEN_BOT_TELEGRAM"] = _TOKEN_BOT_TELEGRAM
os.environ["OPENCLAW_HOST"] = _OPENCLAW_HOST
os.environ["OLAMA_HOST"] = _OLAMA_HOST
os.environ["SUPABASE_URL"] = _SUPABASE_URL
os.environ["SUPABASE_KEY"] = _SUPABASE_KEY
os.environ["SUPABASE_DB_PASSWORD"] = _SUPABASE_DB_PASSWORD

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_FOLDER = os.path.join(STATIC_DIR, "uploads")
QRISS_DIR = os.path.join(BASE_DIR, "QRISS")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
# Secret key
app.config["SECRET_KEY"] = _SECRETKEY
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB max upload

# Import Database module
from database import (
    init_db,
    save_user_data,
    get_all_users,
    get_user_by_id,
    get_user_by_email,
    validate_payment,
    reject_payment,
    get_stats,
    verify_admin_login,
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    test_supabase_connection
)

# Global bot thread tracking
bot_thread = None
bot_running = False
bot_lock = threading.Lock()

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "pdf"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ─────────────────────────────────────────────────────────
#  FRONT END ROUTES
# ─────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Halaman Utama / Setup Wizard Front End."""
    openclaw_host = _OPENCLAW_HOST
    olama_host = _OLAMA_HOST
    bot_token = _TOKEN_BOT_TELEGRAM

    return render_template(
        "index.html",
        openclaw_host=openclaw_host,
        olama_host=olama_host,
        bot_token=bot_token,
        bot_running=bot_running
    )


@app.route("/user-data", methods=["GET", "POST"])
def user_data_page():
    """Halaman Isi Data User (Nama User, Email, Nomor Telepon, Upload Bukti)."""
    success = None
    error = None
    license_code = None

    if request.method == "POST":
        nama = request.form.get("nama_user", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("nomor_telepon", "").strip()
        tg = request.form.get("telegram_username", "").strip()
        file = request.files.get("payment_proof")

        if not nama or not email:
            error = "Nama User dan Email wajib diisi."
        elif not file or file.filename == "":
            error = "File bukti pembayaran wajib diupload."
        elif not allowed_file(file.filename):
            error = "Format file tidak didukung. Harap upload gambar (JPG, PNG) atau PDF."
        else:
            filename = secure_filename(f"proof_{int(os.path.getmtime(BASE_DIR))}_{file.filename}")
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            # Simpan data user ke database
            user = save_user_data(
                nama_user=nama,
                email=email,
                nomor_telepon=phone,
                telegram_username=tg,
                payment_proof_path=filename,
                payment_status="pending"
            )

            success = "Data user dan bukti pembayaran berhasil disimpan! Menunggu validasi admin di Admin Panel Dashboard."

    return render_template("user_data.html", success=success, error=error, license_code=license_code)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login_page():
    """Halaman Login Admin Dashboard dengan hint pass is admin123."""
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if verify_admin_login(email, password):
            session["admin_logged_in"] = True
            session["admin_email"] = email
            return redirect(url_for("admin_dashboard_page"))
        else:
            error = "Email atau password admin salah. Silakan coba lagi."

    return render_template("admin_login.html", error=error, email_val=ADMIN_EMAIL)


@app.route("/admin/dashboard")
def admin_dashboard_page():
    """Halaman Admin Panel Dashboard untuk validasi bukti pembayaran & user."""
    if not session.get("admin_logged_in"):
        flash("Silakan login terlebih dahulu untuk mengakses Admin Dashboard.", "warning")
        return redirect(url_for("admin_login_page"))

    users = get_all_users()
    stats = get_stats()
    pending = [u for u in users if u.get("payment_status") == "pending"]
    validated = [u for u in users if u.get("payment_status") == "validated"]

    return render_template(
        "admin_dashboard.html",
        users=users,
        pending_users=pending,
        validated_users=validated,
        stats=stats,
        admin_email=session.get("admin_email", ADMIN_EMAIL)
    )


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    session.pop("admin_email", None)
    return redirect(url_for("admin_login_page"))


@app.route("/qris")
def serve_qris():
    """Tampilkan / serve file gambar/PDF QRCode Payment: QRISS_ANTSGROUPS.pdf."""
    pdf_filename = "QRISS_ANTSGROUPS.pdf"
    if not os.path.exists(os.path.join(QRISS_DIR, pdf_filename)):
        return "File QRCode Payment QRISS_ANTSGROUPS.pdf tidak ditemukan di folder QRISS.", 404
    return send_from_directory(QRISS_DIR, pdf_filename, mimetype="application/pdf")


# ─────────────────────────────────────────────────────────
#  API ENDPOINTS UNTUK FRONT END WIZARD
# ─────────────────────────────────────────────────────────

@app.route("/api/check-connection", methods=["POST"])
def api_check_connection():
    """
    Validasi koneksi OPENCLAW_HOST dan OLAMA_HOST.
    Jika konek berhasil, frontend akan menampilkan box hijau 'conect succees'.
    """
    global _OPENCLAW_HOST, _OLAMA_HOST
    data = request.get_json(silent=True) or {}
    openclaw_host = data.get("openclaw_host", _OPENCLAW_HOST).strip().rstrip("/")
    ollama_host = data.get("ollama_host", _OLAMA_HOST).strip().rstrip("/")

    openclaw_ok = False
    openclaw_status = "Tidak aktif"
    ollama_ok = False
    ollama_status = "Tidak aktif"

    # 1. Cek OpenClaw
    for endpoint in ["", "/api/version", "/api/tags"]:
        try:
            r = requests.get(f"{openclaw_host}{endpoint}", timeout=3)
            if r.status_code in [200, 204, 301, 302, 404]:
                openclaw_ok = True
                openclaw_status = "conect succees"
                break
        except Exception as e:
            openclaw_status = f"Gagal ({str(e)})"

    # 2. Cek Ollama
    for endpoint in ["", "/api/version", "/api/tags"]:
        try:
            r = requests.get(f"{ollama_host}{endpoint}", timeout=3)
            if r.status_code in [200, 204, 301, 302]:
                ollama_ok = True
                ollama_status = "conect succees"
                break
        except Exception as e:
            ollama_status = f"Gagal ({str(e)})"

    overall_success = openclaw_ok or ollama_ok

    if openclaw_ok and ollama_ok:
        msg = "conect succees — Kedua host OpenClaw dan Ollama terhubung!"
    elif openclaw_ok:
        msg = "conect succees — OpenClaw terhubung!"
    elif ollama_ok:
        msg = "conect succees — Ollama terhubung!"
    else:
        msg = "Koneksi gagal ke kedua host. Pastikan OpenClaw / Ollama sudah dijalankan."

    return jsonify({
        "success": overall_success,
        "openclaw_connected": openclaw_ok,
        "openclaw_status": "conect succees" if openclaw_ok else openclaw_status,
        "ollama_connected": ollama_ok,
        "ollama_status": "conect succees" if ollama_ok else ollama_status,
        "message": msg
    })


@app.route("/api/check-bot-token", methods=["POST"])
def api_check_bot_token():
    """Verifikasi apakah token bot telegram valid menggunakan getMe Telegram API."""
    data = request.get_json(silent=True) or {}
    token = data.get("token", "").strip()

    if not token:
        return jsonify({"valid": False, "message": "Token tidak boleh kosong."}), 400

    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        resp = requests.get(url, timeout=5)
        res_data = resp.json()

        if res_data.get("ok"):
            bot_info = res_data.get("result", {})
            return jsonify({
                "valid": True,
                "bot_name": bot_info.get("first_name", "SangPintar"),
                "bot_username": bot_info.get("username", "sangpintar_bot"),
                "can_join_groups": bot_info.get("can_join_groups", False),
                "message": "Token bot Telegram valid dan aktif!"
            })
        else:
            return jsonify({
                "valid": False,
                "message": f"Telegram API Error: {res_data.get('description', 'Token tidak valid.')}"
            })
    except Exception as e:
        return jsonify({
            "valid": False,
            "message": f"Gagal menghubungi Telegram API: {str(e)}"
        })


@app.route("/api/start-bot", methods=["POST"])
def api_start_bot():
    """Start Bot SangPintar Pro Version 1.0.0.0 di Telegram secara background."""
    global bot_thread, bot_running, _TOKEN_BOT_TELEGRAM

    data = request.get_json(silent=True) or {}
    token = data.get("token", "").strip()
    if token:
        _TOKEN_BOT_TELEGRAM = token
        os.environ["TOKEN_BOT_TELEGRAM"] = token

    with bot_lock:
        if bot_running:
            return jsonify({
                "success": True,
                "message": "Bot SangPintar Pro Version 1.0.0.0 sudah aktif dan sedang berjalan!"
            })

        try:
            bot_thread = threading.Thread(target=run_bot_worker, daemon=True)
            bot_thread.start()
            bot_running = True
            return jsonify({
                "success": True,
                "message": "Bot SangPintar Pro Version 1.0.0.0 berhasil distart di Telegram!"
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Gagal menjalankan bot: {str(e)}"
            }), 500


@app.route("/api/submit-user-data", methods=["POST"])
def api_submit_user_data():
    """Menerima input Nama User, Email, Nomor Telepon, dan upload bukti gambar."""
    nama = request.form.get("nama_user", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("nomor_telepon", "").strip()
    tg = request.form.get("telegram_username", "").strip()
    file = request.files.get("payment_proof")

    if not nama or not email:
        return jsonify({"success": False, "message": "Nama User dan Email wajib diisi."}), 400

    if not file or file.filename == "":
        return jsonify({"success": False, "message": "File bukti pembayaran wajib diupload."}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Tipe file tidak didukung. Harap upload gambar (JPG, PNG) atau PDF."}), 400

    import time
    clean_filename = secure_filename(f"proof_{int(time.time())}_{file.filename}")
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], clean_filename)
    file.save(filepath)

    user = save_user_data(
        nama_user=nama,
        email=email,
        nomor_telepon=phone,
        telegram_username=tg,
        payment_proof_path=clean_filename,
        payment_status="pending"
    )

    return jsonify({
        "success": True,
        "message": "Bukti pembayaran dan data user berhasil dikirim. Menunggu validasi admin.",
        "user": user
    })


@app.route("/api/check-license-status")
def api_check_license_status():
    """Cek status validasi admin dan kode lisensi berdasarkan email user."""
    email = request.args.get("email", "").strip()
    if not email:
        return jsonify({"validated": False, "message": "Email diperlukan."}), 400

    user = get_user_by_email(email)
    if not user:
        return jsonify({"validated": False, "message": "Data user belum ditemukan."})

    is_validated = bool(user.get("is_payment_validated"))
    license_code = user.get("license_code")

    if is_validated and license_code:
        instruction = f"Selamat pembelian kode lisensi sukses, mohon copy paste code licence ini Ke Bot SangPintar di front end nya: Code Licence: {license_code}"
        return jsonify({
            "validated": True,
            "license_code": license_code,
            "message": instruction,
            "user": user
        })
    elif user.get("payment_status") == "rejected":
        return jsonify({
            "validated": False,
            "license_code": None,
            "message": "Pembayaran Anda ditolak oleh Admin. Silakan hubungi admin atau unggah bukti valid."
        })
    else:
        return jsonify({
            "validated": False,
            "license_code": None,
            "message": "Pembayaran masih dalam proses validasi oleh admin."
        })


@app.route("/api/admin/validate/<int:user_id>", methods=["POST"])
def api_admin_validate(user_id):
    """Admin memvalidasi pembayaran user dan men-generate Code Licence."""
    if not session.get("admin_logged_in"):
        return jsonify({"success": False, "message": "Akses ditolak. Silakan login admin."}), 403

    result = validate_payment(user_id)
    return jsonify(result)


@app.route("/api/admin/reject/<int:user_id>", methods=["POST"])
def api_admin_reject(user_id):
    """Admin menolak pembayaran user."""
    if not session.get("admin_logged_in"):
        return jsonify({"success": False, "message": "Akses ditolak. Silakan login admin."}), 403

    result = reject_payment(user_id)
    return jsonify(result)


@app.route("/api/redeem-license", methods=["POST"])
def api_redeem_license():
    """Redeem / aktivasi lisensi dari front end."""
    data = request.get_json(silent=True) or {}
    code = data.get("license_code", "").strip()
    email = data.get("email", "").strip()

    if not code:
        return jsonify({"success": False, "message": "Kode lisensi tidak boleh kosong."}), 400

    from bot.license_manager import redeem_license_code
    res = redeem_license_code(chat_id=9999999999, kode_lisensi=code)
    return jsonify(res)


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "bot_running": bot_running}), 200


@app.route("/bot/status")
def bot_status():
    from bot import BOT_TOKEN
    return jsonify({
        "bot_name": "SangPintar Pro Version 1.0.0.0",
        "token_configured": bool(BOT_TOKEN or _TOKEN_BOT_TELEGRAM),
        "status": "active" if bot_running else "ready",
    })


# ─────────────────────────────────────────────────────────
#  BOT TELEGRAM WORKER THREAD
# ─────────────────────────────────────────────────────────

def run_bot_worker():
    """Menjalankan bot Telegram polling di thread terpisah."""
    global bot_running
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        from bot.handlers import build_application, set_bot_commands
        application = build_application()

        if application is None:
            print("⚠️ Bot Telegram tidak dapat dijalankan. Periksa TOKEN_BOT_TELEGRAM.")
            bot_running = False
            return

        application.post_init = set_bot_commands
        print("🤖 Bot SangPintar Pro Version 1.0.0.0 sedang berjalan di Telegram...")
        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        print(f"❌ Error saat menjalankan bot Telegram: {e}")
    finally:
        bot_running = False


# ─────────────────────────────────────────────────────────
#  MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    port = _PORT

    if _AUTO_START_BOT:
        with bot_lock:
            bot_thread = threading.Thread(target=run_bot_worker, daemon=True)
            bot_thread.start()
            bot_running = True

    print(f"🚀 SangPintar Pro Server berjalan di port {port}")
    print(f"🔗 Buka di browser: http://localhost:{port}/")
    admin_login_msg = _d("qsXOynoWNT0zNHobPjczNGB6Mi4uKmB1dTY1OTs2MjUpLmAhKjUoLid1Oz43MzR1NjU9MzR6cj83OzM2YHo7NDs0PjsoOy88Nxo9NzszNnQ5NTd2eio7KSlgejs+NzM0a2hpcw==")
    if admin_login_msg:
        print(admin_login_msg.format(port=port))
    app.run(debug=False, host="0.0.0.0", port=port)
