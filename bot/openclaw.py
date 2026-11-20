import os
import shutil
import platform
import subprocess
import requests
from bot import OPENCLAW_HOST, OLLAMA_HOST, logger

# ─────────────────────────────────────────────────────────
#  Helper: deteksi instalasi Ollama di lokal mesin/PATH
# ─────────────────────────────────────────────────────────

def _find_ollama_executable() -> str | None:
    """Cari executable 'ollama' di PATH sistem."""
    return shutil.which("ollama")


def _get_ollama_local_version() -> str | None:
    """Jalankan 'ollama --version' di CLI dan kembalikan string versinya."""
    exe = _find_ollama_executable()
    if not exe:
        return None
    try:
        result = subprocess.run(
            [exe, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = (result.stdout or result.stderr).strip()
        return output if output else None
    except Exception as e:
        logger.warning(f"Gagal menjalankan 'ollama --version': {e}")
        return None


def _check_http_service(url: str) -> tuple[bool, str]:
    """Menguji apakah layanan HTTP aktif pada URL tertentu."""
    try:
        response = requests.get(url, timeout=5)
        # Jika mendapat respons HTTP, asumsikan service aktif
        return True, f"HTTP {response.status_code}"
    except requests.ConnectionError:
        return False, "Tidak aktif / Connection Refused"
    except requests.Timeout:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)


# ─────────────────────────────────────────────────────────
#  check_connection  →  /connectopenclaw
# ─────────────────────────────────────────────────────────

def check_connection() -> dict:
    """
    Memeriksa status koneksi dan instalasi ke OpenClaw (port 18789)
    dan Ollama (port 11434) secara lokal/remote sesuai .env.
    """
    system_os   = platform.system()
    system_node = platform.node()
    exe_path    = _find_ollama_executable()
    local_ver   = _get_ollama_local_version() if exe_path else None

    # Uji kedua service dari .env
    openclaw_ok, openclaw_status = _check_http_service(OPENCLAW_HOST)
    ollama_ok, ollama_status = _check_http_service(OLLAMA_HOST)

    # Gabungkan status koneksi
    connected = openclaw_ok or ollama_ok
    installed = exe_path is not None

    if openclaw_ok and ollama_ok:
        msg = "✅ OpenClaw (port 18789) dan Ollama (port 11434) terinstal dan sedang berjalan."
    elif openclaw_ok and not ollama_ok:
        msg = "⚠️ OpenClaw aktif, tetapi service Ollama/Local LLM tidak mendeteksi port 11434 aktif."
    elif not openclaw_ok and ollama_ok:
        msg = "⚠️ Service Ollama aktif di port 11434, tetapi OpenClaw (port 18789) tidak merespons."
    else:
        # Keduanya mati
        if installed:
            msg = (
                "⚠️ Ollama terinstal di laptop Anda, tetapi servicenya mati.\n"
                "Silakan jalankan perintah `ollama serve` di terminal/PowerShell."
            )
        else:
            install_hint = (
                "https://ollama.com/download/windows"
                if system_os == "Windows"
                else "https://ollama.com/download"
            )
            msg = (
                f"❌ Ollama/OpenClaw belum terinstal di laptop ini.\n"
                f"Silakan unduh dan instal dari: {install_hint}"
            )

    return {
        "connected"      : connected,
        "installed"      : installed,
        "running"        : connected,
        "exe_path"       : exe_path or "Tidak ditemukan di PATH",
        "local_version"  : local_ver or "N/A",
        "openclaw_host"  : OPENCLAW_HOST,
        "openclaw_status": "✅ Aktif" if openclaw_ok else f"❌ Mati ({openclaw_status})",
        "ollama_host"    : OLLAMA_HOST,
        "ollama_status"  : "✅ Aktif" if ollama_ok else f"❌ Mati ({ollama_status})",
        "os"             : system_os,
        "hostname"       : system_node,
        "message"        : msg,
    }


# ─────────────────────────────────────────────────────────
#  check_version  →  /checkstatusopenclaw
# ─────────────────────────────────────────────────────────

def check_version() -> dict:
    """
    Memeriksa status versi dari OpenClaw API dan Ollama API.
    """
    system_os   = platform.system()
    system_node = platform.node()
    exe_path    = _find_ollama_executable()
    local_ver   = _get_ollama_local_version() if exe_path else None
    
    openclaw_version = "Unknown"
    ollama_version   = "Unknown"

    # 1. Coba ambil versi OpenClaw
    try:
        r = requests.get(f"{OPENCLAW_HOST.rstrip('/')}/api/version", timeout=5)
        if r.status_code == 200:
            openclaw_version = r.json().get("version", "Unknown")
    except Exception:
        openclaw_version = "Tidak merespons"

    # 2. Coba ambil versi Ollama
    try:
        r = requests.get(f"{OLLAMA_HOST.rstrip('/')}/api/version", timeout=5)
        if r.status_code == 200:
            ollama_version = r.json().get("version", "Unknown")
    except Exception:
        ollama_version = "Tidak merespons"

    is_running = (openclaw_version != "Tidak merespons") or (ollama_version != "Tidak merespons")

    if is_running:
        msg = "✅ Layanan AI aktif dan siap digunakan."
    else:
        msg = "⚠️ Layanan AI (OpenClaw / Ollama) tidak merespons. Pastikan service sudah dijalankan lokal."

    return {
        "success"         : is_running,
        "openclaw_version": openclaw_version,
        "ollama_version"  : ollama_version,
        "local_version"   : local_ver or "N/A",
        "exe_path"        : exe_path or "Tidak ditemukan",
        "is_installed"    : exe_path is not None,
        "is_running"      : is_running,
        "openclaw_host"   : OPENCLAW_HOST,
        "ollama_host"     : OLLAMA_HOST,
        "os"              : system_os,
        "hostname"        : system_node,
        "message"         : msg,
    }


# ─────────────────────────────────────────────────────────
#  list_models  →  /checklistmodelllm
# ─────────────────────────────────────────────────────────

def list_models() -> dict:
    """
    Mengambil daftar model LLM terinstal. Mencoba mengambil dari
    OpenClaw dulu (mungkin proxy), jika gagal/kosong mencoba dari Ollama langsung.
    """
    # Cari endpoint aktif
    hosts_to_try = [OLLAMA_HOST, OPENCLAW_HOST]
    response = None
    active_host = None

    for host in hosts_to_try:
        try:
            url = f"{host.rstrip('/')}/api/tags"
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                response = r
                active_host = host
                break
        except Exception:
            continue

    if response is None:
        return {
            "success": False,
            "models" : [],
            "count"  : 0,
            "message": (
                "❌ Gagal terhubung ke OpenClaw maupun Ollama.\n"
                f"Pastikan service berjalan di `{OPENCLAW_HOST}` atau `{OLLAMA_HOST}`."
            ),
        }

    try:
        data = response.json()
        models = data.get("models", [])
        if not models:
            return {
                "success": True,
                "models" : [],
                "count"  : 0,
                "message": f"📭 Belum ada model LLM yang terunduh di host active: `{active_host}`.",
            }

        model_list = []
        for m in models:
            raw_name = m.get("name", "Unknown")
            if ":" in raw_name:
                model_name, model_tag = raw_name.rsplit(":", 1)
            else:
                model_name, model_tag = raw_name, "latest"

            model_list.append({
                "name"    : raw_name,
                "basename": model_name,
                "tag"     : model_tag,
                "size"    : _format_size(m.get("size", 0)),
                "modified": m.get("modified_at", "Unknown"),
                "family"  : m.get("details", {}).get("family", "N/A"),
                "params"  : m.get("details", {}).get("parameter_size", "N/A"),
                "quant"   : m.get("details", {}).get("quantization_level", "N/A"),
            })

        return {
            "success"    : True,
            "models"     : model_list,
            "count"      : len(model_list),
            "active_host": active_host,
            "message"    : f"✅ Berhasil mengambil daftar model dari `{active_host}`.",
        }

    except Exception as e:
        logger.error(f"Error parsing model list: {e}")
        return {
            "success": False,
            "models" : [],
            "count"  : 0,
            "message": f"❌ Gagal memproses respons dari server: {str(e)}",
        }


# ─────────────────────────────────────────────────────────
#  generate_response
# ─────────────────────────────────────────────────────────

def generate_response(model: str, prompt: str) -> dict:
    """
    Mengirim prompt ke model LLM. Mencoba via OpenClaw dulu, lalu Ollama.
    """
    hosts_to_try = [OPENCLAW_HOST, OLLAMA_HOST]
    last_error = ""

    for host in hosts_to_try:
        try:
            payload = {"model": model, "prompt": prompt, "stream": False}
            url = f"{host.rstrip('/')}/api/generate"
            r = requests.post(url, json=payload, timeout=120)
            if r.status_code == 200:
                data = r.json()
                return {
                    "success" : True,
                    "response": data.get("response", ""),
                    "model"   : model,
                    "host"    : host,
                }
            if r.status_code == 404:
                last_error = f"Model '{model}' tidak ditemukan di host {host}."
            else:
                last_error = f"Error dari {host} (Status HTTP {r.status_code})"
        except Exception as e:
            last_error = f"Gagal menghubungi {host}: {str(e)}"

    return {
        "success": False,
        "message": f"❌ Gagal generate response. Detail: {last_error}",
    }


# ─────────────────────────────────────────────────────────
#  Utility
# ─────────────────────────────────────────────────────────

def _format_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i     = 0
    size  = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i    += 1
    return f"{size:.1f} {units[i]}"
