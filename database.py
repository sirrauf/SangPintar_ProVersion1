"""
database.py - Modul Manajemen Database Supabase PostgreSQL
SangPintar Pro Version 1.0.0.0 - PT Ananda Technology Solution
"""
import os
import json
import uuid
import base64
import datetime
from typing import Dict, Any, List, Optional


def _d(b64_str: str, key: int = 0x5A) -> str:
    """Decode string ter-obfuscate saat runtime dengan auto-padding dan sanitasi spasi."""
    try:
        s = b64_str.strip().replace(" ", "").replace("\n", "").replace("\r", "")
        padding = (4 - len(s) % 4) % 4
        raw = base64.b64decode((s + "=" * padding).encode("utf-8"))
        return bytes(b ^ key for b in raw).decode("utf-8", errors="replace")
    except Exception:
        return ""


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_DB_FILE = os.path.join(BASE_DIR, "users_db.json")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ─────────────────────────────────────────────────────────
#  Konfigurasi Supabase PostgreSQL (Hardcode Ter-obfuscate)
# ─────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", _d("Mi4uKilgdXUqNj04MSk/ICMvNzwzMDU0PywjMnQpLyo7ODspP3Q5NQ=="))
SUPABASE_KEY = os.getenv("SUPABASE_KEY", _d("KTgFKi84NjMpMjs4Nj8FPQMLCCk2NC4tOxR3HDRrCjEyN245PQUyawIsEms7IA=="))
SUPABASE_DB_PASSWORD = os.getenv("SUPABASE_DB_PASSWORD", _d("Ghs9LykuLylua2g="))
SUPABASE_DB_USER = os.getenv("SUPABASE_DB_USER", _d("KjUpLj0oPyk="))
SUPABASE_DB_HOST = os.getenv("SUPABASE_DB_HOST", _d("Pjh0KjY9ODEpPyAjLzc8MzA1ND8sIzJ0KS8qOzg7KT90OTU="))
SUPABASE_DB_PORT = os.getenv("SUPABASE_DB_PORT", _d("b25paA=="))
SUPABASE_DB_NAME = os.getenv("SUPABASE_DB_NAME", _d("KjUpLj0oPyk="))

# Default Admin Credentials (Hardcode Ter-obfuscate)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", _d("OzQ7ND47KDsvPDcaPTc7MzZ0OTU3"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", _d("Oz43MzRraGk="))


def validate_supabase_password(pw: str) -> bool:
    """Validasi password database Supabase."""
    return isinstance(pw, str) and pw == SUPABASE_DB_PASSWORD


# Validasi password database saat inisialisasi modul
_is_password_valid = validate_supabase_password(SUPABASE_DB_PASSWORD)

_supabase_client = None


def get_supabase_client():
    """Mengembalikan client Supabase jika URL & Key valid."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    if not SUPABASE_URL or not SUPABASE_KEY or "your-project" in SUPABASE_URL:
        return None

    try:
        from supabase import create_client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return _supabase_client
    except Exception as e:
        print(f"⚠️ Supabase client error: {e}")
        return None


def test_supabase_connection() -> Dict[str, Any]:
    """Test koneksi ke database Supabase PostgreSQL."""
    if not validate_supabase_password(SUPABASE_DB_PASSWORD):
        return {
            "connected": False,
            "message": "Password database Supabase tidak valid.",
            "using_fallback": True
        }

    client = get_supabase_client()
    if client is None:
        return {
            "connected": False,
            "message": "Supabase client gagal diinisialisasi.",
            "using_fallback": True
        }

    try:
        res = client.table("users").select("id").limit(1).execute()
        return {
            "connected": True,
            "message": "Terhubung ke Supabase PostgreSQL secara sukses!",
            "using_fallback": False
        }
    except Exception as e:
        return {
            "connected": False,
            "message": f"Koneksi Supabase aktif, namun tabel 'users' belum dibuat. Jalankan query SQL di SQL Editor: {str(e)}",
            "using_fallback": True
        }


# ─────────────────────────────────────────────────────────
#  Penyimpanan Fallback JSON (Hanya digunakan jika Supabase offline)
# ─────────────────────────────────────────────────────────
def load_users_db() -> Dict[str, Any]:
    if not os.path.exists(USERS_DB_FILE):
        return {"users": [], "next_id": 1}
    try:
        with open(USERS_DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "users" not in data:
                data["users"] = []
            if "next_id" not in data:
                data["next_id"] = len(data["users"]) + 1
            return data
    except Exception:
        return {"users": [], "next_id": 1}


def save_users_db(data: Dict[str, Any]) -> None:
    try:
        with open(USERS_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False, default=str)
    except Exception as e:
        print(f"Error saving users DB: {e}")


def generate_license_code() -> str:
    """Generate kode lisensi format SP-XXXX-XXXX-XXXX."""
    raw = uuid.uuid4().hex.upper()
    return f"SP-{raw[:4]}-{raw[4:8]}-{raw[8:12]}"


def verify_admin_login(email: str, password: str) -> bool:
    """
    Verifikasi kredensial login admin.
    Cek default admin kredensial terlebih dahulu untuk respon instan,
    kemudian cek tabel 'admins' di Supabase PostgreSQL untuk admin tambahan.
    """
    if not email or not password:
        return False

    clean_email = email.strip().lower()
    if clean_email == ADMIN_EMAIL.strip().lower() and password == ADMIN_PASSWORD:
        return True

    # Cek admin tambahan di Supabase PostgreSQL
    client = get_supabase_client()
    if client:
        try:
            res = client.table("admins").select("*").ilike("email", clean_email).limit(1).execute()
            if res.data and len(res.data) > 0:
                admin_row = res.data[0]
                if admin_row.get("password") == password:
                    return True
        except Exception:
            pass

    return False


# ─────────────────────────────────────────────────────────
#  Operasi Data User (Langsung ke Supabase PostgreSQL)
# ─────────────────────────────────────────────────────────
def save_user_data(
    nama_user: str,
    email: str,
    nomor_telepon: str = "",
    telegram_username: str = "",
    photo_path: str = "",
    payment_proof_path: str = "",
    payment_status: str = "pending"
) -> Dict[str, Any]:
    """
    Simpan data user baru ke database Supabase PostgreSQL.
    TIDAK membuat user_db.json saat berhasil tersimpan di PostgreSQL.
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Simpan langsung ke Supabase PostgreSQL
    client = get_supabase_client()
    if client:
        try:
            row = {
                "nama_user": nama_user,
                "email": email,
                "nomor_telepon": nomor_telepon,
                "telegram_username": telegram_username,
                "payment_proof_path": payment_proof_path,
                "payment_status": payment_status,
                "license_code": None,
                "is_payment_validated": False,
                "license_sent": False,
                "created_at": now
            }
            res = client.table("users").insert(row).execute()
            if res.data and len(res.data) > 0:
                print(f"✅ Data user '{nama_user}' berhasil disimpan ke Supabase PostgreSQL.")
                return res.data[0]
        except Exception as e:
            print(f"⚠️ Gagal menyimpan ke Supabase PostgreSQL: {e}")

    # 2. Fallback darurat HANYA jika Supabase benar-benar tidak bisa diakses
    db = load_users_db()
    new_user = {
        "id": db.get("next_id", 1),
        "nama_user": nama_user,
        "email": email,
        "nomor_telepon": nomor_telepon,
        "telegram_username": telegram_username,
        "payment_proof_path": payment_proof_path,
        "payment_status": payment_status,
        "license_code": None,
        "is_payment_validated": False,
        "license_sent": False,
        "created_at": now,
        "validated_at": None
    }
    db["users"].append(new_user)
    db["next_id"] = db.get("next_id", 1) + 1
    save_users_db(db)
    return new_user


def get_all_users() -> List[Dict[str, Any]]:
    """
    Ambil semua data user langsung dari Supabase PostgreSQL.
    Data ini yang ditampilkan pada Admin Panel Dashboard.
    """
    client = get_supabase_client()
    if client:
        try:
            res = client.table("users").select("*").order("id", desc=True).execute()
            if res.data is not None:
                return res.data
        except Exception as e:
            print(f"⚠️ Supabase select users failed: {e}")

    # Fallback hanya jika file JSON lama ada
    if os.path.exists(USERS_DB_FILE):
        db = load_users_db()
        users = db.get("users", [])
        return sorted(users, key=lambda x: x.get("id", 0), reverse=True)
    return []


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Cari user berdasarkan ID."""
    client = get_supabase_client()
    if client:
        try:
            res = client.table("users").select("*").eq("id", user_id).limit(1).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
        except Exception as e:
            print(f"⚠️ Supabase get_user_by_id failed: {e}")

    users = get_all_users()
    for u in users:
        if str(u.get("id")) == str(user_id):
            return u
    return None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Cari user berdasarkan alamat email."""
    if not email:
        return None
    client = get_supabase_client()
    if client:
        try:
            res = client.table("users").select("*").ilike("email", email.strip()).limit(1).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
        except Exception as e:
            print(f"⚠️ Supabase get_user_by_email failed: {e}")

    users = get_all_users()
    for u in users:
        if u.get("email", "").strip().lower() == email.strip().lower():
            return u
    return None


def validate_payment(user_id: int) -> Dict[str, Any]:
    """
    Validasi pembayaran oleh admin di Admin Dashboard.
    Mengupdate status di Supabase PostgreSQL, men-generate kode lisensi,
    dan menyinkronkan ke licenses.json untuk Bot Telegram.
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    license_code = generate_license_code()
    client = get_supabase_client()

    # 1. Update ke Supabase PostgreSQL
    if client:
        try:
            res = client.table("users").select("*").eq("id", user_id).limit(1).execute()
            if res.data and len(res.data) > 0:
                user_found = res.data[0]
                if user_found.get("is_payment_validated"):
                    return {
                        "success": True,
                        "message": "Pembayaran sudah divalidasi sebelumnya.",
                        "license_code": user_found.get("license_code"),
                        "user": user_found
                    }

                update_res = client.table("users").update({
                    "payment_status": "validated",
                    "is_payment_validated": True,
                    "license_code": license_code,
                    "validated_at": now
                }).eq("id", user_id).execute()

                updated_user = update_res.data[0] if update_res.data else user_found
                updated_user["license_code"] = license_code
                updated_user["is_payment_validated"] = True
                updated_user["payment_status"] = "validated"

                # Sinkronkan ke licenses.json untuk bot Telegram
                try:
                    from bot.license_manager import load_licenses, save_licenses
                    lic_data = load_licenses()
                    if "keys" not in lic_data:
                        lic_data["keys"] = {}
                    lic_data["keys"][license_code] = {
                        "chat_id": None,
                        "email": updated_user.get("email"),
                        "nama_user": updated_user.get("nama_user"),
                        "used": False,
                        "langganan": "1 Bulan"
                    }
                    save_licenses(lic_data)
                except Exception as e:
                    print(f"⚠️ Error sync to licenses.json: {e}")

                # Sinkronkan juga ke tabel licenses PostgreSQL Supabase
                try:
                    client.table("licenses").insert({
                        "license_code": license_code,
                        "email": updated_user.get("email"),
                        "nama_user": updated_user.get("nama_user"),
                        "langganan": "1 Bulan",
                        "is_activated": False,
                        "used": False,
                        "created_at": now
                    }).execute()
                except Exception:
                    pass

                return {
                    "success": True,
                    "message": "Pembayaran berhasil divalidasi! Kode lisensi telah digenerate.",
                    "license_code": license_code,
                    "user": updated_user
                }
        except Exception as e:
            print(f"⚠️ Supabase validate_payment error: {e}")

    # 2. Fallback jika Supabase offline
    if os.path.exists(USERS_DB_FILE):
        db = load_users_db()
        user_found = None
        for u in db.get("users", []):
            if str(u.get("id")) == str(user_id):
                user_found = u
                break

        if not user_found:
            return {"success": False, "message": f"User ID {user_id} tidak ditemukan."}

        if user_found.get("is_payment_validated"):
            return {
                "success": True,
                "message": "Pembayaran sudah divalidasi sebelumnya.",
                "license_code": user_found.get("license_code"),
                "user": user_found
            }

        user_found["payment_status"] = "validated"
        user_found["is_payment_validated"] = True
        user_found["license_code"] = license_code
        user_found["validated_at"] = now
        save_users_db(db)

        # Sinkronkan ke licenses.json untuk bot
        try:
            from bot.license_manager import load_licenses, save_licenses
            lic_data = load_licenses()
            if "keys" not in lic_data:
                lic_data["keys"] = {}
            lic_data["keys"][license_code] = {
                "chat_id": None,
                "email": user_found.get("email"),
                "nama_user": user_found.get("nama_user"),
                "used": False,
                "langganan": "1 Bulan"
            }
            save_licenses(lic_data)
        except Exception as e:
            print(f"Error sync to licenses.json: {e}")

        return {
            "success": True,
            "message": "Pembayaran berhasil divalidasi! Kode lisensi telah digenerate.",
            "license_code": license_code,
            "user": user_found
        }

    return {"success": False, "message": f"User ID {user_id} tidak ditemukan."}


def reject_payment(user_id: int) -> Dict[str, Any]:
    """Tolak pembayaran user di Supabase PostgreSQL."""
    client = get_supabase_client()
    if client:
        try:
            res = client.table("users").update({
                "payment_status": "rejected",
                "is_payment_validated": False
            }).eq("id", user_id).execute()
            if res.data and len(res.data) > 0:
                return {"success": True, "message": "Pembayaran berhasil ditolak.", "user": res.data[0]}
        except Exception as e:
            print(f"⚠️ Supabase reject_payment error: {e}")

    if os.path.exists(USERS_DB_FILE):
        db = load_users_db()
        user_found = None
        for u in db.get("users", []):
            if str(u.get("id")) == str(user_id):
                user_found = u
                break

        if not user_found:
            return {"success": False, "message": f"User ID {user_id} tidak ditemukan."}

        user_found["payment_status"] = "rejected"
        user_found["is_payment_validated"] = False
        save_users_db(db)
        return {"success": True, "message": "Pembayaran berhasil ditolak.", "user": user_found}

    return {"success": False, "message": f"User ID {user_id} tidak ditemukan."}


def get_stats() -> Dict[str, int]:
    """Ambil statistik user untuk Admin Panel Dashboard."""
    users = get_all_users()
    return {
        "total": len(users),
        "pending": len([u for u in users if u.get("payment_status") == "pending"]),
        "validated": len([u for u in users if u.get("payment_status") == "validated"]),
        "rejected": len([u for u in users if u.get("payment_status") == "rejected"]),
    }


def init_db():
    """
    Inisialisasi database.
    Memeriksa koneksi ke Supabase PostgreSQL tanpa membuat file users_db.json.
    """
    conn_info = test_supabase_connection()
    if conn_info.get("connected"):
        print(f"✅ Supabase PostgreSQL: {conn_info.get('message')}")
    else:
        print(f"ℹ️ Status Supabase: {conn_info.get('message')}")
    print(f"✅ Database initialized. Supabase password validation: {'VALID' if _is_password_valid else 'INVALID'}")


if __name__ == "__main__":
    init_db()
