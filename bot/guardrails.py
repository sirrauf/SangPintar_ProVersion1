import re
import os
from bot import logger

BLACKLISTED_COMMANDS = [
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+/\*",
    r"rm\s+-rf\s+\.\*",
    r"chmod\s+777\s+-R",
    r"chown\s+root:root",
    r"mkfs",
    r"fdisk",
    r"\bdd\b\s+if=",
    r"iptables\s+-F",
    r"ufw\s+disable",
    r"shutdown",
    r"reboot",
    r"\binit\s+[0-6]",
]

SENSITIVE_PATHS = [
    "~/.ssh/",
    "/etc/",
    "/var/",
    "/root/",
    "/usr/",
    "/boot/",
    "/proc/",
    "/sys/",
]

CONFIRMATION_REQUIRED_PATTERNS = [
    r"drop\s+database",
    r"rm\s+-r\s+",
    r"git\s+push\s+-f",
    r"git\s+push\s+--force",
]


def is_blacklisted(command: str) -> bool:
    command_lower = command.lower().strip()
    for pattern in BLACKLISTED_COMMANDS:
        if re.search(pattern, command_lower):
            logger.warning(f"[GUARDRAIL] Blacklisted command blocked: {command}")
            return True
    return False


def is_outside_workspace(path: str) -> bool:
    normalized = os.path.normpath(path)
    for sensitive in SENSITIVE_PATHS:
        if normalized.startswith(sensitive) or normalized.startswith(os.path.expanduser(sensitive)):
            logger.warning(f"[GUARDRAIL] Access outside workspace blocked: {path}")
            return True
    return False


def needs_user_confirmation(command: str) -> bool:
    command_lower = command.lower().strip()
    for pattern in CONFIRMATION_REQUIRED_PATTERNS:
        if re.search(pattern, command_lower):
            return True
    return False


def validate_command(command: str) -> dict:
    if is_blacklisted(command):
        return {
            "allowed": False,
            "reason": "⛔ Perintah ini masuk daftar hitam (blacklisted) dan dilarang dieksekusi demi keamanan sistem.",
        }

    if needs_user_confirmation(command):
        return {
            "allowed": False,
            "needs_confirmation": True,
            "reason": "⚠️ Perintah ini memerlukan konfirmasi pengguna sebelum dieksekusi.",
        }

    return {"allowed": True, "reason": "✅ Perintah aman untuk dieksekusi."}


def validate_file_access(filepath: str) -> dict:
    if is_outside_workspace(filepath):
        return {
            "allowed": False,
            "reason": f"⛔ Akses ke path '{filepath}' diluar workspace tidak diizinkan.",
        }
    return {"allowed": True, "reason": "✅ Akses file dalam workspace diizinkan."}


def sanitize_input(user_input: str) -> str:
    dangerous_chars = [";", "&&", "||", "|", "`", "$(",  "$()", ">>"]
    sanitized = user_input
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "")
    return sanitized.strip()
