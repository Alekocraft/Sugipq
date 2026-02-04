# services/ldap_auth.py
"""Compatibilidad: expone ADAuth/ad_auth desde utils.ldap_auth."""
from utils.ldap_auth import ADAuth, ad_auth  # noqa: F401

def servicio_directorio_disponible() -> bool:
    try:
        return bool(ad_auth.is_available())
    except Exception:
        return False
