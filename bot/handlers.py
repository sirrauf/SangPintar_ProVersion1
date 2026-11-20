import os
import io
import datetime
from openpyxl import Workbook
from telegram import Update, BotCommand, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)
from bot import (
    BOT_TOKEN,
    BOT_VERSION,
    BOT_NAME,
    COMPANY_NAME,
    BOT_UPDATE_LINK,
    logger,
)
from bot.openclaw import check_connection, check_version, list_models, generate_response
from bot.guardrails import validate_command, sanitize_input
from bot.license_manager import (
    create_user_registration,
    redeem_license_code,
    get_user_license_status,
    EXPIRED_MESSAGE,
)

WP_URL, WP_USER, WP_PASS, WP_TITLE, WP_CONTENT = range(5)
FIN_PERSONAL_INPUT = range(1)
FIN_COMPANY_INPUT = range(1)
DEV_WEB_INPUT = range(1)
DEPLOY_METHOD, DEPLOY_HOST, DEPLOY_USER, DEPLOY_PASSWORD, DEPLOY_PATH = range(5)

REG_NAME, REG_USERNAME, REG_EMAIL, REG_PLAN, REG_REDEEM = range(10, 15)

user_wp_sessions = {}
user_finance_personal = {}
user_finance_company = {}
user_deploy_sessions = {}
user_registration_sessions = {}

MENU_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📝 Pendaftaran User"), KeyboardButton("💳 Status Lisensi")],
        [KeyboardButton("📋 Command List"), KeyboardButton("🔄 Update Version")],
        [KeyboardButton("✅ Check Versi"), KeyboardButton("🤖 OpenClaw Status")],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)


async def set_bot_commands(application):
    commands = [
        BotCommand("start", "Mulai SangPintar"),
        BotCommand("pendaftaranuser", "Pendaftaran lisensi langganan"),
        BotCommand("checkstatuslisensilangganan", "Cek status lisensi langganan"),
        BotCommand("ceklisensi", "Cek kode lisensi setelah validasi admin"),
        BotCommand("connectopenclaw", "Cek koneksi OpenClaw"),
        BotCommand("checkstatusopenclaw", "Cek versi OpenClaw"),
        BotCommand("checklistmodelllm", "Lihat model LLM terinstal"),
        BotCommand("autonomuspostingartikel", "Auto posting artikel WordPress"),
        BotCommand("autonomuskeuanganpribadi", "Catat keuangan pribadi"),
        BotCommand("autonomuskeuanganperusahaan", "Catat keuangan perusahaan"),
        BotCommand("autonomusdevweb", "Bantuan development website"),
        BotCommand("autonomusdeployweb", "Deploy website via FTP/SSH"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands registered successfully")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        await context.bot.delete_my_commands()
        await set_bot_commands(context.application)
    except Exception as e:
        logger.warning(f"Could not reset commands: {e}")

    welcome_message = (
        f"🤖 *Selamat datang di {BOT_NAME}!*\n\n"
        f"_{BOT_NAME} merupakan produk terbaru dari {COMPANY_NAME}._\n\n"
        f"📌 *Version:* Pro Version 1.0.0.0\n\n"
        f"Gunakan menu di bawah atau ketik /help untuk melihat daftar perintah."
    )
    await update.message.reply_text(
        welcome_message, parse_mode="Markdown", reply_markup=MENU_KEYBOARD
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        f"📋 *Daftar Command {BOT_NAME}*\n\n"
        "🔹 /start — Mulai SangPintar\n"
        "🔹 /pendaftaranuser — Pendaftaran lisensi langganan\n"
        "🔹 /checkstatuslisensilangganan — Cek status lisensi langganan\n"
        "🔹 /connectopenclaw — Cek koneksi OpenClaw\n"
        "🔹 /checkstatusopenclaw — Cek versi OpenClaw\n"
        "🔹 /checklistmodelllm — Lihat model LLM\n"
        "🔹 /autonomuspostingartikel — Auto posting artikel\n"
        "🔹 /autonomuskeuanganpribadi — Keuangan pribadi\n"
        "🔹 /autonomuskeuanganperusahaan — Keuangan perusahaan\n"
        "🔹 /autonomusdevweb — Bantuan development web\n"
        "🔹 /autonomusdeployweb — Deploy website\n\n"
        "📌 Gunakan menu keyboard untuk akses cepat."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


# ==========================================
# HANDLER PENDAFTARAN USER & AKTVASI LISENSI
# ==========================================

async def cmd_pendaftaran_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_registration_sessions[chat_id] = {}
    msg = (
        "📝 *Pendaftaran User Lisensi Langganan SangPintar*\n\n"
        "Silakan masukkan *Nama User* (Nama Lengkap Anda):\n\n"
        "Ketik /cancel untuk membatalkan."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
    return REG_NAME


async def reg_receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    nama = sanitize_input(update.message.text.strip())
    user_registration_sessions[chat_id] = {"nama_user": nama}

    tg_username = update.effective_user.username if update.effective_user and update.effective_user.username else ""
    hint = f" (contoh Telegram Anda: `{tg_username}`)" if tg_username else ""

    msg = (
        f"👤 Nama User: *{nama}*\n\n"
        f"Selanjutnya, masukkan *Username User* Anda{hint}:"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
    return REG_USERNAME


async def reg_receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    username = sanitize_input(update.message.text.strip().lstrip("@"))
    if chat_id not in user_registration_sessions:
        user_registration_sessions[chat_id] = {}
    user_registration_sessions[chat_id]["username_user"] = username

    msg = (
        f"🏷️ Username User: *{username}*\n\n"
        "Selanjutnya, masukkan *Email User* Anda:"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
    return REG_EMAIL


async def reg_receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    email = sanitize_input(update.message.text.strip())
    if chat_id not in user_registration_sessions:
        user_registration_sessions[chat_id] = {}
    user_registration_sessions[chat_id]["email_user"] = email

    plan_keyboard = ReplyKeyboardMarkup(
        [
            [KeyboardButton("1 Bulan"), KeyboardButton("1 Tahun")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    msg = (
        f"📧 Email User: *{email}*\n\n"
        "Silakan pilih paket langganan Anda:\n"
        "1️⃣ *1 Bulan*\n"
        "2️⃣ *1 Tahun*"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=plan_keyboard)
    return REG_PLAN


async def reg_receive_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip().lower()

    if "tahun" in text or text == "2":
        langganan = "1 Tahun"
    elif "bulan" in text or text == "1":
        langganan = "1 Bulan"
    else:
        await update.message.reply_text(
            "⚠️ Pilihan tidak valid. Silakan pilih *1 Bulan* atau *1 Tahun*.",
            parse_mode="Markdown",
        )
        return REG_PLAN

    session = user_registration_sessions.get(chat_id, {})
    nama = session.get("nama_user", "User")
    username = session.get("username_user", "username")
    email = session.get("email_user", "email@example.com")

    reg_data = create_user_registration(chat_id, nama, username, email, langganan)
    kode_lisensi = reg_data["kode_lisensi"]
    session["kode_lisensi"] = kode_lisensi

    msg = (
        f"🎉 *Pendaftaran User Lisensi Berhasil!*\n"
        f"{'━' * 32}\n"
        f"👤 *Nama User     :* {nama}\n"
        f"🏷️ *Username User :* {username}\n"
        f"📧 *Email User    :* {email}\n"
        f"⏱️ *Langganan     :* {langganan}\n"
        f"🔑 *Kode Lisensi  :* `{kode_lisensi}`\n"
        f"{'━' * 32}\n\n"
        f"⚠️ *Langkah Terakhir (Aktivasi Kode Lisensi):*\n"
        f"Silakan *masukkan/ketik Kode Lisensi* Anda di atas (`{kode_lisensi}`) untuk mengaktifkan lisensi langganan Anda.\n\n"
        f"📌 *Catatan:* Kode lisensi hanya dapat dimasukkan satu kali."
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=MENU_KEYBOARD)
    return REG_REDEEM


async def reg_receive_redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    code_input = update.message.text.strip()

    result = redeem_license_code(chat_id, code_input)

    if result["success"]:
        data = result["data"]
        msg = (
            f"✅ *AKTIVASI LISENSI BERHASIL!*\n"
            f"{'━' * 32}\n"
            f"👤 *Nama User           :* {data['nama_user']}\n"
            f"🏷️ *Username User       :* {data['username_user']}\n"
            f"📧 *Email User          :* {data['email_user']}\n"
            f"🔑 *Kode Lisensi        :* `{data['kode_lisensi']}`\n"
            f"⏱️ *Waktu Expired Lisensi:* `{data['waktu_expired']}`\n"
            f"{'━' * 32}\n\n"
            f"Terima kasih telah berlangganan SangPintar! 🎉"
        )
        user_registration_sessions.pop(chat_id, None)
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=MENU_KEYBOARD)
        return ConversationHandler.END
    else:
        msg = (
            f"{result['message']}\n\n"
            f"Silakan masukkan Kode Lisensi yang benar:"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
        return REG_REDEEM


# ==========================================
# HANDLER CHECK STATUS LISENSI LANGGANAN
# ==========================================

async def cmd_cek_lisensi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cek kode lisensi yang sudah divalidasi admin."""
    chat_id = update.effective_chat.id
    tg_username = update.effective_user.username if update.effective_user and update.effective_user.username else ""
    
    # Ambil argumen email jika ada: /ceklisensi email@example.com
    email_arg = context.args[0].strip().lower() if context.args else ""

    from database import get_all_users
    users = get_all_users()
    matched_user = None

    for u in users:
        if email_arg and u.get("email", "").strip().lower() == email_arg:
            matched_user = u
            break
        elif tg_username and u.get("telegram_username", "").strip().lower().lstrip("@") == tg_username.lower().lstrip("@"):
            matched_user = u
            break

    if not matched_user and not email_arg:
        # Coba cari user tervalidasi yang paling baru jika belum ditentukan
        validated_users = [u for u in users if u.get("is_payment_validated") and u.get("license_code")]
        if validated_users:
            matched_user = validated_users[0]

    if matched_user:
        if matched_user.get("is_payment_validated") and matched_user.get("license_code"):
            lic_code = matched_user.get("license_code")
            msg = (
                f"🎉 *Selamat pembelian kode lisensi sukses!*\n\n"
                f"mohon copy paste code licence ini Ke Bot SangPintar di front end nya:\n\n"
                f"*Code Licence:* `{lic_code}`\n\n"
                f"📌 Anda juga dapat langsung mengetik `{lic_code}` di chat ini untuk mengaktifkan lisensi."
            )
            await update.message.reply_text(msg, parse_mode="Markdown")
            return
        elif matched_user.get("payment_status") == "pending":
            await update.message.reply_text(
                "⏳ Pembayaran Anda sedang dalam proses verifikasi oleh Admin. Mohon tunggu.",
                parse_mode="Markdown"
            )
            return
        elif matched_user.get("payment_status") == "rejected":
            await update.message.reply_text(
                "❌ Pembayaran Anda ditolak oleh Admin. Silakan upload bukti pembayaran yang valid.",
                parse_mode="Markdown"
            )
            return

    await update.message.reply_text(
        "📭 Data lisensi tidak ditemukan.\n\n"
        "Gunakan format: `/ceklisensi email_anda@example.com` untuk mengecek berdasarkan email yang Anda daftarkan di Web.",
        parse_mode="Markdown"
    )


async def cmd_check_status_lisensi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    result = get_user_license_status(chat_id)
    status = result.get("status")

    if status == "NOT_REGISTERED":
        msg = (
            "📭 *Status Lisensi Langganan*\n"
            f"{'━' * 32}\n"
            "Anda belum terdaftar dalam sistem lisensi.\n"
            "Silakan lakukan pendaftaran terlebih dahulu via menu atau perintah `/pendaftaranuser`."
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    elif status == "NOT_ACTIVATED":
        data = result.get("data", {})
        msg = (
            "⚠️ *Status Lisensi Langganan*\n"
            f"{'━' * 32}\n"
            f"👤 *Nama User     :* {data.get('nama_user', 'N/A')}\n"
            f"🏷️ *Username User :* {data.get('username_user', 'N/A')}\n"
            f"📧 *Email User    :* {data.get('email_user', 'N/A')}\n"
            f"🔑 *Kode Lisensi  :* `{data.get('kode_lisensi', 'N/A')}`\n"
            f"📊 *Status        :* ⚠️ Belum Diaktivasi\n"
            f"{'━' * 32}\n\n"
            "Silakan masukkan kode lisensi Anda untuk mengaktifkan."
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    elif status == "EXPIRED":
        await update.message.reply_text(EXPIRED_MESSAGE)
    elif status == "ACTIVE":
        data = result.get("data", {})
        msg = (
            "💳 *STATUS LISENSI LANGGANAN*\n"
            f"{'━' * 32}\n"
            f"👤 *Nama User           :* {data.get('nama_user', 'N/A')}\n"
            f"🏷️ *Username User       :* {data.get('username_user', 'N/A')}\n"
            f"📧 *Email User          :* {data.get('email_user', 'N/A')}\n"
            f"🔑 *Kode Lisensi        :* `{data.get('kode_lisensi', 'N/A')}`\n"
            f"⏱️ *Waktu Expired Lisensi:* `{data.get('waktu_expired', 'N/A')}`\n"
            f"📊 *Status Lisensi      :* ✅ Aktif\n"
            f"{'━' * 32}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_connect_openclaw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Memeriksa instalasi OpenClaw/Ollama di laptop lokal...")
    result = check_connection()

    installed_icon = "✅" if result.get("installed") else "❌"
    connected_icon = "✅" if result.get("connected") else "❌"

    msg = (
        f"{connected_icon} *Status Koneksi OpenClaw & Ollama*\n"
        f"{'━' * 32}\n"
        f"💻 *OS Laptop     :* {result.get('os', 'N/A')} (`{result.get('hostname', 'N/A')}`)\n"
        f"📂 *Ollama CLI    :* {installed_icon} {'Terinstal' if result.get('installed') else 'Tidak ditemukan di PATH'}\n"
        f"📍 *Lokasi exe    :* `{result.get('exe_path', 'N/A')}`\n"
        f"🏷️ *Versi CLI      :* `{result.get('local_version', 'N/A')}`\n"
        f"{'━' * 32}\n"
        f"📡 *OpenClaw Host :* `{result.get('openclaw_host', 'N/A')}`\n"
        f"📊 *Status        :* {result.get('openclaw_status', 'N/A')}\n"
        f"{'━' * 32}\n"
        f"🦙 *Ollama Host   :* `{result.get('ollama_host', 'N/A')}`\n"
        f"📊 *Status        :* {result.get('ollama_status', 'N/A')}\n"
        f"{'━' * 32}\n"
        f"{result.get('message', '')}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_check_status_openclaw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Memeriksa status & versi OpenClaw/Ollama...")
    result = check_version()

    installed_icon = "✅" if result.get("is_installed") else "❌"
    running_icon   = "✅" if result.get("is_running")   else "❌"

    msg = (
        f"📊 *Status Versi Layanan AI*\n"
        f"{'━' * 32}\n"
        f"💻 *OS Laptop     :* {result.get('os', 'N/A')} (`{result.get('hostname', 'N/A')}`)\n"
        f"📂 *Ollama CLI    :* {installed_icon} {'Terinstal' if result.get('is_installed') else 'Tidak'}\n"
        f"🏷️ *Versi CLI      :* `{result.get('local_version', 'N/A')}`\n"
        f"{'━' * 32}\n"
        f"📡 *OpenClaw Host :* `{result.get('openclaw_host', 'N/A')}`\n"
        f"🌐 *Versi API     :* `{result.get('openclaw_version', 'N/A')}`\n"
        f"{'━' * 32}\n"
        f"🦙 *Ollama Host   :* `{result.get('ollama_host', 'N/A')}`\n"
        f"🌐 *Versi API     :* `{result.get('ollama_version', 'N/A')}`\n"
        f"{'━' * 32}\n"
        f"{result.get('message', '')}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_check_list_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Mengambil daftar model LLM yang terinstal di Ollama...")
    result = list_models()

    if not result["success"]:
        await update.message.reply_text(
            f"⚠️ *Gagal Mengambil Daftar Model*\n\n{result['message']}",
            parse_mode="Markdown",
        )
        return

    models = result.get("models", [])
    if not models:
        await update.message.reply_text(
            "📭 *Belum Ada Model LLM Terinstal*\n\n"
            "Instal model dengan perintah di terminal:\n"
            "`ollama pull llama3.2`",
            parse_mode="Markdown",
        )
        return

    msg = (
        f"🧠 *Daftar Model LLM Terinstal*\n"
        f"{'━' * 32}\n"
        f"📡 *Sumber Host  :* `{result.get('active_host', 'N/A')}`\n"
        f"📦 *Total Model  :* *{result['count']} model*\n"
        f"{'━' * 32}\n\n"
    )

    for i, model in enumerate(models, 1):
        msg += (
            f"*{i}. {model['name']}*\n"
            f"   🏷️ Tag       : `{model['tag']}`\n"
            f"   👨‍👩‍👦 Family    : `{model['family']}`\n"
            f"   ⚙️ Parameter : `{model['params']}`\n"
            f"   🔢 Quantize  : `{model['quant']}`\n"
            f"   📦 Ukuran    : `{model['size']}`\n"
            f"   🕐 Modified  : `{model['modified']}`\n\n"
        )

    msg += f"💡 Gunakan `/autonomusdevweb` untuk memakai salah satu model di atas."

    if len(msg) > 4000:
        parts = [msg[i:i+4000] for i in range(0, len(msg), 4000)]
        for part in parts:
            await update.message.reply_text(part, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_autonomus_posting_artikel_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    status_info = get_user_license_status(chat_id)
    if status_info.get("status") == "EXPIRED":
        await update.message.reply_text(EXPIRED_MESSAGE)
        return ConversationHandler.END

    user_wp_sessions[chat_id] = {}
    msg = (
        "📝 *Autonomous Posting Artikel WordPress*\n\n"
        "Silakan kirim URL admin WordPress Anda.\n"
        "Contoh: `https://example.com/wp-admin`\n\n"
        "Ketik /cancel untuk membatalkan."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
    return WP_URL


async def wp_receive_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    url = sanitize_input(update.message.text.strip())
    user_wp_sessions[chat_id] = {"url": url}
    await update.message.reply_text("👤 Kirim *username* WordPress Anda:", parse_mode="Markdown")
    return WP_USER


async def wp_receive_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_wp_sessions[chat_id]["username"] = sanitize_input(update.message.text.strip())
    await update.message.reply_text("🔑 Kirim *Application Password* WordPress Anda:", parse_mode="Markdown")
    return WP_PASS


async def wp_receive_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_wp_sessions[chat_id]["password"] = update.message.text.strip()
    await update.message.reply_text("📰 Kirim *Judul Artikel:*", parse_mode="Markdown")
    return WP_TITLE


async def wp_receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_wp_sessions[chat_id]["title"] = update.message.text.strip()
    await update.message.reply_text("📄 Kirim *Isi Artikel:*", parse_mode="Markdown")
    return WP_CONTENT


async def wp_receive_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_wp_sessions.get(chat_id, {})
    session["content"] = update.message.text.strip()

    await update.message.reply_text("🔄 Memproses posting artikel ke WordPress...")

    import requests as req

    try:
        wp_api_url = session["url"].rstrip("/").replace("/wp-admin", "") + "/wp-json/wp/v2/posts"
        payload = {
            "title": session["title"],
            "content": session["content"],
            "status": "publish",
        }
        response = req.post(
            wp_api_url,
            json=payload,
            auth=(session["username"], session["password"]),
            timeout=30,
        )
        if response.status_code in [200, 201]:
            post_data = response.json()
            msg = (
                f"✅ *Artikel Berhasil Diposting!*\n\n"
                f"📰 Judul: {session['title']}\n"
                f"🔗 URL: {post_data.get('link', 'N/A')}\n"
                f"📅 Tanggal: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
        else:
            msg = f"❌ Gagal posting. Status: {response.status_code}\n\n{response.text[:200]}"
    except Exception as e:
        msg = f"❌ Error saat posting: {str(e)}"

    user_wp_sessions.pop(chat_id, None)
    await update.message.reply_text(msg, parse_mode="Markdown")
    return ConversationHandler.END


async def cmd_autonomus_keuangan_pribadi_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    status_info = get_user_license_status(chat_id)
    if status_info.get("status") == "EXPIRED":
        await update.message.reply_text(EXPIRED_MESSAGE)
        return ConversationHandler.END

    user_finance_personal[chat_id] = []
    msg = (
        "💰 *Autonomous Keuangan Pribadi*\n\n"
        "Catat pemasukan dan pengeluaran Anda.\n"
        "Format: `tipe|keterangan|jumlah`\n\n"
        "📥 Contoh pemasukan: `masuk|Gaji Bulanan|5000000`\n"
        "📤 Contoh pengeluaran: `keluar|Makan Siang|50000`\n\n"
        "Ketik *selesai* untuk generate file Excel.\n"
        "Ketik /cancel untuk membatalkan."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
    return 0


async def finance_personal_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if text.lower() == "selesai":
        records = user_finance_personal.get(chat_id, [])
        if not records:
            await update.message.reply_text("📭 Belum ada data. Masukkan data terlebih dahulu.")
            return 0

        wb = Workbook()
        ws = wb.active
        ws.title = "Keuangan Pribadi"
        ws.append(["No", "Tipe", "Keterangan", "Jumlah (Rp)", "Tanggal"])

        total_masuk = 0
        total_keluar = 0
        for i, rec in enumerate(records, 1):
            ws.append([i, rec["tipe"], rec["keterangan"], rec["jumlah"], rec["tanggal"]])
            if rec["tipe"] == "Pemasukan":
                total_masuk += rec["jumlah"]
            else:
                total_keluar += rec["jumlah"]

        ws.append([])
        ws.append(["", "Total Pemasukan", "", total_masuk, ""])
        ws.append(["", "Total Pengeluaran", "", total_keluar, ""])
        ws.append(["", "Saldo", "", total_masuk - total_keluar, ""])

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        filename = f"Keuangan_Pribadi_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        await update.message.reply_document(
            document=buffer,
            filename=filename,
            caption=f"✅ File Excel keuangan pribadi berhasil dibuat!\n\n💵 Total Pemasukan: Rp {total_masuk:,.0f}\n💸 Total Pengeluaran: Rp {total_keluar:,.0f}\n💰 Saldo: Rp {total_masuk - total_keluar:,.0f}",
        )
        user_finance_personal.pop(chat_id, None)
        return ConversationHandler.END

    try:
        parts = text.split("|")
        if len(parts) != 3:
            await update.message.reply_text("⚠️ Format salah. Gunakan: `tipe|keterangan|jumlah`", parse_mode="Markdown")
            return 0

        tipe_raw = parts[0].strip().lower()
        keterangan = parts[1].strip()
        jumlah = float(parts[2].strip())

        tipe = "Pemasukan" if tipe_raw in ["masuk", "pemasukan", "income"] else "Pengeluaran"

        if chat_id not in user_finance_personal:
            user_finance_personal[chat_id] = []

        user_finance_personal[chat_id].append({
            "tipe": tipe,
            "keterangan": keterangan,
            "jumlah": jumlah,
            "tanggal": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        })

        count = len(user_finance_personal[chat_id])
        await update.message.reply_text(
            f"✅ Data #{count} tercatat: *{tipe}* — {keterangan} — Rp {jumlah:,.0f}\n\nKirim data lagi atau ketik *selesai*.",
            parse_mode="Markdown",
        )
        return 0
    except ValueError:
        await update.message.reply_text("⚠️ Jumlah harus berupa angka. Contoh: `masuk|Gaji|5000000`", parse_mode="Markdown")
        return 0


async def cmd_autonomus_keuangan_perusahaan_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    status_info = get_user_license_status(chat_id)
    if status_info.get("status") == "EXPIRED":
        await update.message.reply_text(EXPIRED_MESSAGE)
        return ConversationHandler.END

    user_finance_company[chat_id] = {}
    msg = (
        "🏢 *Autonomous Keuangan Perusahaan*\n\n"
        "Catat keuangan perusahaan Anda.\n"
        "Kirim data dengan format:\n\n"
        "`laba_bersih|laba_kotor|modal_awal|hutang|piutang`\n\n"
        "Contoh: `50000000|80000000|100000000|20000000|15000000`\n\n"
        "Ketik /cancel untuk membatalkan."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
    return 0


async def finance_company_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    try:
        parts = text.split("|")
        if len(parts) != 5:
            await update.message.reply_text(
                "⚠️ Format salah. Gunakan: `laba_bersih|laba_kotor|modal_awal|hutang|piutang`",
                parse_mode="Markdown",
            )
            return 0

        data = {
            "Laba Bersih": float(parts[0].strip()),
            "Laba Kotor": float(parts[1].strip()),
            "Modal Awal": float(parts[2].strip()),
            "Hutang": float(parts[3].strip()),
            "Piutang": float(parts[4].strip()),
        }

        wb = Workbook()
        ws = wb.active
        ws.title = "Keuangan Perusahaan"
        ws.append(["Kategori", "Jumlah (Rp)"])
        for key, val in data.items():
            ws.append([key, val])
        ws.append([])
        ws.append(["Total Aset", data["Modal Awal"] + data["Piutang"]])
        ws.append(["Total Kewajiban", data["Hutang"]])
        ws.append(["Ekuitas", data["Modal Awal"] + data["Piutang"] - data["Hutang"]])
        ws.append([])
        ws.append(["Tanggal Laporan", datetime.datetime.now().strftime("%Y-%m-%d %H:%M")])

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        filename = f"Keuangan_Perusahaan_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        await update.message.reply_text("🔄 Memproses laporan keuangan perusahaan...")
        await update.message.reply_document(
            document=buffer,
            filename=filename,
            caption=f"✅ Laporan keuangan perusahaan berhasil dibuat!\n\n💰 Laba Bersih: Rp {data['Laba Bersih']:,.0f}\n📊 Laba Kotor: Rp {data['Laba Kotor']:,.0f}\n🏦 Modal Awal: Rp {data['Modal Awal']:,.0f}",
        )
        user_finance_company.pop(chat_id, None)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("⚠️ Semua nilai harus berupa angka.", parse_mode="Markdown")
        return 0


async def cmd_autonomus_dev_web_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    status_info = get_user_license_status(chat_id)
    if status_info.get("status") == "EXPIRED":
        await update.message.reply_text(EXPIRED_MESSAGE)
        return ConversationHandler.END

    msg = (
        "🌐 *Autonomous Development Website*\n\n"
        "Deskripsikan website yang ingin Anda buat.\n"
        "SangPintar akan menggunakan AI (OpenClaw) untuk membantu Anda.\n\n"
        "Contoh: `Buatkan landing page untuk toko online dengan fitur keranjang belanja`\n\n"
        "Ketik /cancel untuk membatalkan."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
    return 0


async def dev_web_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompt = update.message.text.strip()
    await update.message.reply_text("🔄 Memproses permintaan development website dengan AI...")

    system_prompt = (
        "Kamu adalah web developer profesional. "
        "Buatkan kode website sesuai permintaan user berikut. "
        "Berikan kode HTML, CSS, dan JavaScript yang lengkap dan fungsional."
    )
    full_prompt = f"{system_prompt}\n\nPermintaan user: {user_prompt}"

    result = generate_response("llama3.2", full_prompt)

    if result["success"]:
        response_text = result["response"]
        if len(response_text) > 4000:
            chunks = [response_text[i : i + 4000] for i in range(0, len(response_text), 4000)]
            for i, chunk in enumerate(chunks):
                await update.message.reply_text(f"📄 Bagian {i + 1}/{len(chunks)}:\n\n{chunk}")
        else:
            await update.message.reply_text(f"🌐 *Hasil Development Website:*\n\n{response_text}", parse_mode="Markdown")
    else:
        await update.message.reply_text(result["message"])

    return ConversationHandler.END


async def cmd_autonomus_deploy_web_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    status_info = get_user_license_status(chat_id)
    if status_info.get("status") == "EXPIRED":
        await update.message.reply_text(EXPIRED_MESSAGE)
        return ConversationHandler.END

    user_deploy_sessions[chat_id] = {}
    msg = (
        "🚀 *Autonomous Deploy Website*\n\n"
        "Pilih metode deploy:\n"
        "1️⃣ Ketik `FTP` untuk deploy via FTP\n"
        "2️⃣ Ketik `SSH` untuk deploy via SSH\n\n"
        "Ketik /cancel untuk membatalkan."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
    return DEPLOY_METHOD


async def deploy_receive_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    method = update.message.text.strip().upper()
    if method not in ["FTP", "SSH"]:
        await update.message.reply_text("⚠️ Pilih `FTP` atau `SSH`.", parse_mode="Markdown")
        return DEPLOY_METHOD
    user_deploy_sessions[chat_id] = {"method": method}
    await update.message.reply_text(f"🌐 Kirim *hostname/IP server* untuk {method}:", parse_mode="Markdown")
    return DEPLOY_HOST


async def deploy_receive_host(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_deploy_sessions[chat_id]["host"] = sanitize_input(update.message.text.strip())
    await update.message.reply_text("👤 Kirim *username:*", parse_mode="Markdown")
    return DEPLOY_USER


async def deploy_receive_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_deploy_sessions[chat_id]["username"] = sanitize_input(update.message.text.strip())
    await update.message.reply_text("🔑 Kirim *password:*", parse_mode="Markdown")
    return DEPLOY_PASSWORD


async def deploy_receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_deploy_sessions[chat_id]["password"] = update.message.text.strip()
    await update.message.reply_text("📁 Kirim *path direktori tujuan* di server:", parse_mode="Markdown")
    return DEPLOY_PATH


async def deploy_receive_path(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = user_deploy_sessions.get(chat_id, {})
    session["remote_path"] = sanitize_input(update.message.text.strip())

    method = session.get("method", "")
    host = session.get("host", "")
    username = session.get("username", "")

    if method == "SSH":
        try:
            import paramiko

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=host,
                username=username,
                password=session["password"],
                timeout=15,
            )
            stdin, stdout, stderr = ssh.exec_command(f"ls {session['remote_path']}")
            output = stdout.read().decode()
            error = stderr.read().decode()
            ssh.close()

            msg = (
                f"✅ *Koneksi SSH Berhasil!*\n\n"
                f"🖥 Server: `{host}`\n"
                f"👤 User: `{username}`\n"
                f"📁 Path: `{session['remote_path']}`\n\n"
                f"📄 Files:\n```\n{output or error}\n```\n\n"
                f"Kirim file yang ingin di-deploy ke chat ini."
            )
        except Exception as e:
            msg = f"❌ Gagal koneksi SSH: {str(e)}"
    elif method == "FTP":
        try:
            import ftplib

            ftp = ftplib.FTP()
            ftp.connect(host, 21, timeout=15)
            ftp.login(username, session["password"])
            ftp.cwd(session["remote_path"])
            files = ftp.nlst()
            ftp.quit()

            msg = (
                f"✅ *Koneksi FTP Berhasil!*\n\n"
                f"🖥 Server: `{host}`\n"
                f"👤 User: `{username}`\n"
                f"📁 Path: `{session['remote_path']}`\n\n"
                f"📄 Files: {', '.join(files[:10])}\n\n"
                f"Kirim file yang ingin di-deploy ke chat ini."
            )
        except Exception as e:
            msg = f"❌ Gagal koneksi FTP: {str(e)}"
    else:
        msg = "❌ Metode deploy tidak valid."

    user_deploy_sessions.pop(chat_id, None)
    await update.message.reply_text(msg, parse_mode="Markdown")
    return ConversationHandler.END


async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    if text == "📋 Command List":
        await cmd_help(update, context)
    elif text == "📝 Pendaftaran User":
        await cmd_pendaftaran_user_start(update, context)
    elif text in ["💳 Status Lisensi", "Cek Status Lisensi"]:
        await cmd_check_status_lisensi(update, context)
    elif text == "🔄 Update Version":
        msg = (
            f"🎉 *Update Version*\n\n"
            f"Selamat anda mendapatkan update versi terbaru yaitu versi {BOT_VERSION}.\n\n"
            f"Mohon klik link URL berikut ini untuk mendapatkan Versi terbaru {BOT_NAME}:\n"
            f"{BOT_UPDATE_LINK}"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    elif text == "✅ Check Versi":
        msg = (
            f"✅ *Check Versi*\n\n"
            f"Terima kasih sudah Subscribe {BOT_NAME} ^-^\n\n"
            f"Selamat anda sudah update versi terbaru {BOT_NAME}.\n"
            f"Anda sekarang menggunakan Versi: *{BOT_VERSION}*."
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    elif text == "🤖 OpenClaw Status":
        await cmd_connect_openclaw(update, context)
    elif text.startswith("SP-") and len(text) == 17:
        result = redeem_license_code(chat_id, text)
        if result["success"]:
            data = result["data"]
            msg = (
                f"✅ *AKTIVASI LISENSI BERHASIL!*\n"
                f"{'━' * 32}\n"
                f"👤 *Nama User           :* {data['nama_user']}\n"
                f"🏷️ *Username User       :* {data['username_user']}\n"
                f"📧 *Email User          :* {data['email_user']}\n"
                f"🔑 *Kode Lisensi        :* `{data['kode_lisensi']}`\n"
                f"⏱️ *Waktu Expired Lisensi:* `{data['waktu_expired']}`\n"
                f"{'━' * 32}\n\n"
                f"Terima kasih telah berlangganan SangPintar! 🎉"
            )
            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            await update.message.reply_text(result["message"], parse_mode="Markdown")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Operasi dibatalkan.", reply_markup=MENU_KEYBOARD)
    return ConversationHandler.END


def build_application():
    if not BOT_TOKEN:
        logger.error("TOKEN_BOT_TELEGRAM is not set in .env")
        return None

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    registration_conversation = ConversationHandler(
        entry_points=[
            CommandHandler("pendaftaranuser", cmd_pendaftaran_user_start),
            CommandHandler("pendaftaran", cmd_pendaftaran_user_start),
        ],
        states={
            REG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_receive_name)],
            REG_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_receive_username)],
            REG_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_receive_email)],
            REG_PLAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_receive_plan)],
            REG_REDEEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_receive_redeem)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    wp_conversation = ConversationHandler(
        entry_points=[CommandHandler("autonomuspostingartikel", cmd_autonomus_posting_artikel_start)],
        states={
            WP_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, wp_receive_url)],
            WP_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, wp_receive_user)],
            WP_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, wp_receive_pass)],
            WP_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, wp_receive_title)],
            WP_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, wp_receive_content)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    finance_personal_conversation = ConversationHandler(
        entry_points=[CommandHandler("autonomuskeuanganpribadi", cmd_autonomus_keuangan_pribadi_start)],
        states={0: [MessageHandler(filters.TEXT & ~filters.COMMAND, finance_personal_input)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    finance_company_conversation = ConversationHandler(
        entry_points=[CommandHandler("autonomuskeuanganperusahaan", cmd_autonomus_keuangan_perusahaan_start)],
        states={0: [MessageHandler(filters.TEXT & ~filters.COMMAND, finance_company_input)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    dev_web_conversation = ConversationHandler(
        entry_points=[CommandHandler("autonomusdevweb", cmd_autonomus_dev_web_start)],
        states={0: [MessageHandler(filters.TEXT & ~filters.COMMAND, dev_web_input)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    deploy_conversation = ConversationHandler(
        entry_points=[CommandHandler("autonomusdeployweb", cmd_autonomus_deploy_web_start)],
        states={
            DEPLOY_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, deploy_receive_method)],
            DEPLOY_HOST: [MessageHandler(filters.TEXT & ~filters.COMMAND, deploy_receive_host)],
            DEPLOY_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, deploy_receive_user)],
            DEPLOY_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, deploy_receive_password)],
            DEPLOY_PATH: [MessageHandler(filters.TEXT & ~filters.COMMAND, deploy_receive_path)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(registration_conversation)
    application.add_handler(CommandHandler("checkstatuslisensilangganan", cmd_check_status_lisensi))
    application.add_handler(CommandHandler("checkstatuslisensi", cmd_check_status_lisensi))
    application.add_handler(CommandHandler("ceklisensi", cmd_cek_lisensi))
    application.add_handler(CommandHandler("connectopenclaw", cmd_connect_openclaw))
    application.add_handler(CommandHandler("checkstatusopenclaw", cmd_check_status_openclaw))
    application.add_handler(CommandHandler("checklistmodelllm", cmd_check_list_model))

    application.add_handler(wp_conversation)
    application.add_handler(finance_personal_conversation)
    application.add_handler(finance_company_conversation)
    application.add_handler(dev_web_conversation)
    application.add_handler(deploy_conversation)

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_buttons))

    return application
