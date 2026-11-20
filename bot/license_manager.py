import os
import json
import uuid
import datetime
from typing import Dict, Any, Optional

LICENSE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "licenses.json")
EXPIRED_MESSAGE = (
    "Mohon melakuan pembayaran langganan lagi, masa berlaku lisensi anda sudah expired, "
    "hubungi admin SangPintar melalui Whatsapp: +62-851-1704-1240 atau klik link url Whatsapp dibawah ini: "
    "https://wa.me/6285117041240."
)


def load_licenses() -> Dict[str, Any]:
    """Load licenses data from JSON file."""
    if not os.path.exists(LICENSE_FILE):
        return {"users": {}, "keys": {}}
    try:
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "users" not in data:
                data["users"] = {}
            if "keys" not in data:
                data["keys"] = {}
            return data
    except Exception:
        return {"users": {}, "keys": {}}


def save_licenses(data: Dict[str, Any]) -> None:
    """Save licenses data to JSON file."""
    try:
        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving licenses: {e}")


def generate_license_code() -> str:
    """Auto generate a unique license code in format SP-XXXX-XXXX-XXXX."""
    raw_uuid = uuid.uuid4().hex.upper()
    return f"SP-{raw_uuid[:4]}-{raw_uuid[4:8]}-{raw_uuid[8:12]}"


def create_user_registration(
    chat_id: int,
    nama_user: str,
    username_user: str,
    email_user: str,
    langganan: str,
) -> Dict[str, Any]:
    """
    Register a new user subscription request and auto generate a license code.
    langganan can be '1 Bulan' or '1 Tahun'.
    """
    data = load_licenses()
    kode_lisensi = generate_license_code()
    str_chat_id = str(chat_id)

    registration_info = {
        "chat_id": chat_id,
        "nama_user": nama_user,
        "username_user": username_user,
        "email_user": email_user,
        "langganan": langganan,
        "kode_lisensi": kode_lisensi,
        "is_activated": False,
        "used": False,
        "tanggal_pendaftaran": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tanggal_aktivasi": None,
        "waktu_expired": None,
    }

    data["users"][str_chat_id] = registration_info
    data["keys"][kode_lisensi] = {
        "chat_id": chat_id,
        "used": False,
        "langganan": langganan,
    }

    save_licenses(data)
    return registration_info


def redeem_license_code(chat_id: int, kode_lisensi: str) -> Dict[str, Any]:
    """
    Redeem / Enter license code once.
    Calculates license expiration based on subscription duration.
    """
    data = load_licenses()
    kode_clean = kode_lisensi.strip().upper()
    str_chat_id = str(chat_id)

    if kode_clean not in data.get("keys", {}):
        return {
            "success": False,
            "message": "❌ Kode lisensi tidak valid / tidak ditemukan.",
        }

    key_info = data["keys"][kode_clean]

    if key_info.get("used", False):
        return {
            "success": False,
            "message": "⚠️ Kode lisensi ini sudah pernah dimasukkan / digunakan! Kode lisensi hanya bisa dimasukkan satu kali.",
        }

    # Find user
    user_info = data["users"].get(str_chat_id)
    if not user_info and key_info.get("chat_id"):
        owner_chat_id = str(key_info.get("chat_id"))
        user_info = data["users"].get(owner_chat_id)

    if not user_info:
        # User mendaftar melalui Web Frontend
        user_info = {
            "chat_id": chat_id,
            "nama_user": key_info.get("nama_user", "User SangPintar"),
            "username_user": key_info.get("nama_user", "user"),
            "email_user": key_info.get("email", ""),
            "langganan": key_info.get("langganan", "1 Bulan"),
            "kode_lisensi": kode_clean,
            "is_activated": False,
            "used": False,
            "tanggal_pendaftaran": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tanggal_aktivasi": None,
            "waktu_expired": None,
        }
        data["users"][str_chat_id] = user_info

    now = datetime.datetime.now()
    langganan = user_info.get("langganan", key_info.get("langganan", "1 Bulan"))

    if "1 Tahun" in langganan:
        expired_dt = now + datetime.timedelta(days=365)
    else:
        expired_dt = now + datetime.timedelta(days=30)

    waktu_expired_str = expired_dt.strftime("%Y-%m-%d %H:%M:%S")

    user_info["is_activated"] = True
    user_info["used"] = True
    user_info["tanggal_aktivasi"] = now.strftime("%Y-%m-%d %H:%M:%S")
    user_info["waktu_expired"] = waktu_expired_str
    user_info["kode_lisensi"] = kode_clean

    data["users"][str(user_info["chat_id"])] = user_info
    data["keys"][kode_clean]["used"] = True
    data["keys"][kode_clean]["activated_by"] = chat_id

    save_licenses(data)

    return {
        "success": True,
        "message": "✅ Kode lisensi berhasil diaktivasi!",
        "data": user_info,
    }


def get_user_license_status(chat_id: int) -> Dict[str, Any]:
    """
    Get user license details and check expiration status.
    """
    data = load_licenses()
    str_chat_id = str(chat_id)
    user_info = data["users"].get(str_chat_id)

    if not user_info:
        return {
            "status": "NOT_REGISTERED",
            "message": "📭 Anda belum terdaftar dalam sistem lisensi. Silakan lakukan pendaftaran via `/pendaftaranuser`.",
        }

    if not user_info.get("is_activated"):
        return {
            "status": "NOT_ACTIVATED",
            "data": user_info,
            "message": "⚠️ Lisensi Anda belum diaktivasi. Silakan masukkan kode lisensi Anda.",
        }

    waktu_expired_str = user_info.get("waktu_expired")
    if not waktu_expired_str:
        return {
            "status": "EXPIRED",
            "data": user_info,
            "message": EXPIRED_MESSAGE,
        }

    try:
        expired_dt = datetime.datetime.strptime(waktu_expired_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.datetime.now()
        if now >= expired_dt:
            return {
                "status": "EXPIRED",
                "data": user_info,
                "message": EXPIRED_MESSAGE,
            }
        else:
            return {
                "status": "ACTIVE",
                "data": user_info,
                "message": "✅ Status Lisensi: Aktif",
            }
    except Exception:
        return {
            "status": "EXPIRED",
            "data": user_info,
            "message": EXPIRED_MESSAGE,
        }
