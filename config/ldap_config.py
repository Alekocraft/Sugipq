# config/ldap_config.py
"""
Configuración para conexión con Active Directory.

Nota:
- Soporta variables de entorno históricas: LDAP_USER/LDAP_PASSWORD y las nuevas LDAP_SERVICE_USER/LDAP_SERVICE_PASSWORD.
"""
import os
from dotenv import load_dotenv

load_dotenv()

def _env_bool(key: str, default: bool = False) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    raw = str(raw).strip().lower()
    if raw in ("1", "true", "yes", "y", "si", "sí", "on"):
        return True
    if raw in ("0", "false", "no", "n", "off"):
        return False
    return default

LDAP_ENABLED = _env_bool("LDAP_ENABLED", True)

LDAP_SERVER = os.getenv("LDAP_SERVER", "").strip()
LDAP_PORT = int(os.getenv("LDAP_PORT", "389"))
LDAP_USE_SSL = _env_bool("LDAP_USE_SSL", False)

LDAP_DOMAIN = os.getenv("LDAP_DOMAIN", "qualitascolombia.com.co").strip()
LDAP_SEARCH_BASE = os.getenv("LDAP_SEARCH_BASE", "DC=qualitascolombia,DC=com,DC=co").strip()

# Credenciales de cuenta de servicio (para búsquedas/lookup DN). Acepta nombres antiguos.
LDAP_SERVICE_USER = (
    os.getenv("LDAP_SERVICE_USER")
    or os.getenv("LDAP_USER")
    or "userauge"
).strip()

LDAP_SERVICE_PASSWORD = (
    os.getenv("LDAP_SERVICE_PASSWORD")
    or os.getenv("LDAP_PASSWORD")
)

# Configuración de mapeo de roles AD -> Sistema
AD_ROLE_MAPPING = {
    "administrador": ["gerencia", "admin", "administrador"],
    "lider_inventario": ["almacen", "logistica", "inventario"],
    "tesoreria": ["contabilidad", "tesoreria"],
}

# Timeout en segundos
LDAP_CONNECTION_TIMEOUT = int(os.getenv("LDAP_CONNECTION_TIMEOUT", "10"))
