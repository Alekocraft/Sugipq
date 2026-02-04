# -*- coding: utf-8 -*-
"""Utilidades de autenticación y búsqueda LDAP/AD.

Compatibilidad:
- Se expone una instancia `ad_auth` de `ADAuth`.
- Métodos: test_connection, authenticate_user, search_user_by_name, search_user_by_email,
  get_user_details.

Notas para Python 3.13 + ldap3 2.9.1:
- En algunos entornos NTLM puede fallar por falta de soporte MD4 (p. ej. error
  "unsupported hash type md4"). Este módulo hace fallback a SIMPLE y además intenta
  SIMPLE+STARTTLS (389) / SIMPLE sobre LDAPS (636).
- Si tu AD *exige* NTLM y falla por MD4, instala `pycryptodome`.

Mejoras de robustez/seguridad:
- Sin recursión ante LDAPSocketOpenError (se prueban endpoints y se corta).
- Escapado de filtros LDAP para evitar inyección.
- Logs sanitizados (CWE-117 / CWE-209 / CWE-532).
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ldap3 import ALL, NTLM, SIMPLE, SUBTREE, Connection, Server
from ldap3.core.exceptions import (
    LDAPBindError,
    LDAPException,
    LDAPSocketOpenError,
    LDAPUnknownAuthenticationMethodError,
)
from ldap3.utils.conv import escape_filter_chars

logger = logging.getLogger(__name__)


# =========================
# Imports tolerantes
# =========================
try:
    from config.config import Config  # type: ignore
except Exception:
    try:
        from config import Config  # type: ignore
    except Exception:

        class Config:  # fallback mínimo (solo para evitar crash)
            LDAP_ENABLED = True
            LDAP_SERVER = os.getenv("LDAP_SERVER", "")
            LDAP_PORT = int(os.getenv("LDAP_PORT", "389"))
            LDAP_DOMAIN = os.getenv("LDAP_DOMAIN", "")
            LDAP_SEARCH_BASE = os.getenv("LDAP_SEARCH_BASE", "")
            LDAP_SERVICE_USER = os.getenv("LDAP_SERVICE_USER")
            LDAP_SERVICE_PASSWORD = os.getenv("LDAP_SERVICE_PASSWORD")


# Sanitización + error id (tolerante)
_gen_error_id = None
try:
    from utils.helpers import sanitizar_username, sanitizar_log_text  # type: ignore

    try:
        from utils.helpers import generar_error_id as _gen_error_id  # type: ignore
    except Exception:
        _gen_error_id = None
except Exception:
    try:
        from helpers import sanitizar_username, sanitizar_log_text  # type: ignore
    except Exception:

        def sanitizar_username(_v):  # type: ignore
            return "[usuario-protegido]"

        def sanitizar_log_text(_v, max_len: int = 500):  # type: ignore
            return "[texto-protegido]"


def generar_error_id() -> str:
    """Id corto para correlación de errores sin filtrar info sensible."""
    try:
        if callable(_gen_error_id):
            v = _gen_error_id()
            if v:
                return str(v)
    except Exception:
        pass
    return uuid.uuid4().hex[:8]


@dataclass(frozen=True)
class _LdapEndpoint:
    port: int
    use_ssl: bool


def _bool_env(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "si", "sí", "on")


class ADAuth:
    """Cliente LDAP simple para autenticación y búsquedas."""

    def __init__(self):
        self.server_address: str = getattr(Config, "LDAP_SERVER", os.getenv("LDAP_SERVER", "")) or ""
        try:
            self.port: int = int(getattr(Config, "LDAP_PORT", os.getenv("LDAP_PORT", "389")))
        except Exception:
            self.port = 389

        self.domain: str = getattr(Config, "LDAP_DOMAIN", os.getenv("LDAP_DOMAIN", "")) or ""
        self.search_base: str = getattr(Config, "LDAP_SEARCH_BASE", os.getenv("LDAP_SEARCH_BASE", "")) or ""

        self.service_user: Optional[str] = getattr(Config, "LDAP_SERVICE_USER", os.getenv("LDAP_SERVICE_USER"))
        self.service_password: Optional[str] = getattr(
            Config, "LDAP_SERVICE_PASSWORD", os.getenv("LDAP_SERVICE_PASSWORD")
        )

        # Permite forzar SSL desde env
        self.force_ssl: Optional[bool] = None
        if os.getenv("LDAP_USE_SSL") is not None:
            self.force_ssl = _bool_env("LDAP_USE_SSL", default=False)

        # Timeout de conexión
        try:
            self.connect_timeout = int(os.getenv("LDAP_CONNECT_TIMEOUT", "10"))
        except Exception:
            self.connect_timeout = 10

        # Último endpoint bueno
        self._last_good: Optional[_LdapEndpoint] = None

    # ---------------------
    # Endpoints
    # ---------------------

    def _endpoints_to_try(self) -> List[_LdapEndpoint]:
        """Lista ordenada de endpoints (puerto/ssl) a intentar."""
        if not self.server_address:
            return []

        endpoints: List[_LdapEndpoint] = []

        if self._last_good:
            endpoints.append(self._last_good)

        use_ssl_primary = (self.force_ssl if self.force_ssl is not None else (self.port == 636))
        endpoints.append(_LdapEndpoint(port=self.port, use_ssl=use_ssl_primary))

        if self.port != 389:
            endpoints.append(_LdapEndpoint(port=389, use_ssl=False))
        if self.port != 636:
            endpoints.append(_LdapEndpoint(port=636, use_ssl=True))

        # dedupe preservando orden
        seen = set()
        uniq: List[_LdapEndpoint] = []
        for ep in endpoints:
            key = (ep.port, ep.use_ssl)
            if key not in seen:
                seen.add(key)
                uniq.append(ep)
        return uniq

    # Backwards-compat (por si hay código viejo)
    def _endpoints(self) -> List[Dict[str, object]]:
        return [{"host": self.server_address, "port": ep.port, "use_ssl": ep.use_ssl} for ep in self._endpoints_to_try()]

    def _make_server(self, ep: _LdapEndpoint) -> Server:
        return Server(
            self.server_address,
            port=ep.port,
            use_ssl=ep.use_ssl,
            get_info=ALL,
            connect_timeout=self.connect_timeout,
        )

    # Backwards-compat (firma antigua)
    def _make_server_legacy(self, host: str, port: int, use_ssl: bool) -> Server:
        return Server(host, port=port, use_ssl=use_ssl, get_info=ALL, connect_timeout=self.connect_timeout)

    # ---------------------
    # Principals
    # ---------------------

    def _format_user_for_ntlm(self, user: str) -> str:
        """Devuelve el usuario en formato DOMINIO\\usuario si aplica."""
        u = (user or "").strip()
        if not u:
            return u
        if "\\" in u or "@" in u:
            return u
        return f"{self.domain}\\{u}" if self.domain else u

    def _format_user_for_simple(self, user: str) -> str:
        """Devuelve el usuario preferiblemente en formato UPN (usuario@dominio)."""
        u = (user or "").strip()
        if not u:
            return u
        if "@" in u:
            return u
        if "\\" in u:
            u = u.split("\\", 1)[1]
        if self.domain and "." in self.domain:
            return f"{u}@{self.domain}"
        return u

    # ---------------------
    # Binds
    # ---------------------

    def _bind_simple_starttls(self, server: Server, principal: str, password: str) -> Optional[Connection]:
        """SIMPLE con StartTLS (útil cuando AD bloquea simple bind sin TLS en 389)."""
        conn: Optional[Connection] = None
        try:
            conn = Connection(server, user=principal, password=password, authentication=SIMPLE, auto_bind=False)
            if not conn.open():
                return None
            # Si el servidor no soporta StartTLS, devuelve False
            if not conn.start_tls():
                try:
                    conn.unbind()
                except Exception:
                    pass
                return None
            if not conn.bind():
                try:
                    conn.unbind()
                except Exception:
                    pass
                return None
            return conn
        except Exception:
            try:
                if conn:
                    conn.unbind()
            except Exception:
                pass
            return None

    def _service_bind(self, server: Server) -> Optional[Connection]:
        """Bind con cuenta de servicio para búsquedas.

        Si LDAP_SERVICE_USER viene sin dominio, NTLM puede fallar. Se normaliza y se
        hace fallback a SIMPLE/UPN.
        """
        if not self.service_user or not self.service_password:
            return None

        principal_ntlm = self._format_user_for_ntlm(self.service_user)
        principal_simple = self._format_user_for_simple(self.service_user)

        last_error: str | None = None

        for auth_name, auth_method, principal, use_starttls in (
            ("NTLM", NTLM, principal_ntlm, False),
            ("SIMPLE+STARTTLS", SIMPLE, principal_simple, True),
            ("SIMPLE", SIMPLE, principal_simple, False),
        ):
            try:
                if auth_method == SIMPLE and use_starttls:
                    conn = self._bind_simple_starttls(server, principal, self.service_password)
                else:
                    conn = Connection(
                        server,
                        user=principal,
                        password=self.service_password,
                        authentication=auth_method,
                        auto_bind=True,
                    )
                if conn and conn.bound:
                    return conn
                last_error = f"Bind falló ({auth_name})"
            except LDAPSocketOpenError:
                raise
            except ValueError as ve:
                # Caso típico: MD4/NTLM en entornos nuevos
                msg = str(ve).lower()
                if "md4" in msg:
                    last_error = "NTLM requiere MD4 (instale pycryptodome)"
                else:
                    last_error = f"Error ({auth_name})"
                continue
            except (LDAPUnknownAuthenticationMethodError, LDAPBindError, LDAPException):
                last_error = f"Error ({auth_name})"
                continue
            except Exception:
                last_error = f"Error ({auth_name})"
                continue

        logger.error(
            "❌ LDAP: Error autenticando con cuenta de servicio: %s",
            sanitizar_log_text(last_error or "Unknown"),
        )
        return None

    # ---------------------
    # API pública
    # ---------------------

    def test_connection(self) -> Dict[str, object]:
        """Prueba apertura de socket (y bind si hay cuenta de servicio)."""
        if not getattr(Config, "LDAP_ENABLED", True):
            return {"success": False, "message": "LDAP deshabilitado"}

        if not self.server_address:
            return {"success": False, "message": "LDAP_SERVER no configurado"}

        last_err: Optional[str] = None
        for ep in self._endpoints_to_try():
            try:
                server = self._make_server(ep)

                if self.service_user and self.service_password:
                    conn = self._service_bind(server)
                    if conn:
                        try:
                            conn.unbind()
                        except Exception:
                            pass
                        self._last_good = ep
                        return {
                            "success": True,
                            "message": "Conexión LDAP exitosa",
                            "server": self.server_address,
                            "port": ep.port,
                            "use_ssl": ep.use_ssl,
                        }
                    last_err = "Bind de servicio falló"
                else:
                    conn = Connection(server, auto_bind=False)
                    if conn.open():
                        try:
                            conn.unbind()
                        except Exception:
                            pass
                        self._last_good = ep
                        return {
                            "success": True,
                            "message": "Socket LDAP accesible",
                            "server": self.server_address,
                            "port": ep.port,
                            "use_ssl": ep.use_ssl,
                        }
                    last_err = "No se pudo abrir socket"

            except LDAPSocketOpenError:
                last_err = "No se pudo abrir socket"
                continue
            except Exception:
                last_err = "Error"
                continue

        return {"success": False, "message": last_err or "No se pudo conectar a LDAP"}

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Autentica un usuario contra Active Directory.

        Estrategia:
          - Intenta endpoints (último bueno, 389, 636).
          - Para cada endpoint intenta: NTLM -> SIMPLE+STARTTLS -> SIMPLE.
        """
        username_clean = str(username or "").strip()
        password = "" if password is None else str(password)

        if not username_clean or not password:
            return None

        principal_ntlm = self._format_user_for_ntlm(username_clean)
        principal_simple = self._format_user_for_simple(username_clean)

        for ep in self._endpoints_to_try():
            server = self._make_server(ep)

            attempts = [
                ("NTLM", NTLM, principal_ntlm, False),
            ]

            # En 389 sin SSL, intentar StartTLS antes del simple bind normal
            if not ep.use_ssl and ep.port == 389:
                attempts.append(("SIMPLE+STARTTLS", SIMPLE, principal_simple, True))

            attempts.append(("SIMPLE", SIMPLE, principal_simple, False))

            for auth_name, auth_method, principal, use_starttls in attempts:
                conn: Optional[Connection] = None
                try:
                    if auth_method == SIMPLE and use_starttls:
                        conn = self._bind_simple_starttls(server, principal, password)
                    else:
                        conn = Connection(
                            server,
                            user=principal,
                            password=password,
                            authentication=auth_method,
                            auto_bind=True,
                        )

                    if not conn or not conn.bound:
                        try:
                            if conn:
                                conn.unbind()
                        except Exception:
                            pass
                        continue

                    # Detalles (preferiblemente con la misma conexión del usuario)
                    details = self.get_user_details(username_clean, conn=conn) or {}

                    # Normalizar llaves esperadas por el sistema
                    nombre = details.get("full_name") or details.get("nombre") or ""
                    dept = details.get("department") or details.get("departamento") or ""
                    email = details.get("email") or details.get("correo") or ""

                    # memberOf puede venir como lista o string
                    groups = details.get("groups") or details.get("memberOf") or []
                    if isinstance(groups, str):
                        groups = [groups]
                    if not isinstance(groups, list):
                        groups = []

                    user_info: Dict[str, Any] = {
                        "username": username_clean,
                        "full_name": nombre,
                        "email": email,
                        "department": dept,
                        "role": details.get("role") or details.get("rol") or "",
                        "groups": groups,
                        "groups_count": len(groups),
                        "auth_method": auth_name,
                        "endpoint": f"{self.server_address}:{ep.port}",
                    }

                    try:
                        conn.unbind()
                    except Exception:
                        pass

                    self._last_good = ep
                    return user_info

                except LDAPSocketOpenError:
                    # probar siguiente endpoint
                    try:
                        if conn:
                            conn.unbind()
                    except Exception:
                        pass
                    break
                except LDAPBindError:
                    # credenciales/política -> probar método alterno
                    try:
                        if conn:
                            conn.unbind()
                    except Exception:
                        pass
                    continue
                except ValueError as ve:
                    # Caso típico: MD4 ausente para NTLM
                    msg = str(ve).lower()
                    if "md4" in msg and ("unsupported" in msg or "not supported" in msg):
                        logger.warning(
                            "LDAP: NTLM no disponible en este entorno (MD4). "
                            "Instale pycryptodome o use SIMPLE sobre TLS/LDAPS."
                        )
                    try:
                        if conn:
                            conn.unbind()
                    except Exception:
                        pass
                    continue
                except LDAPException:
                    try:
                        if conn:
                            conn.unbind()
                    except Exception:
                        pass
                    continue
                except Exception:
                    try:
                        if conn:
                            conn.unbind()
                    except Exception:
                        pass
                    continue

        error_id = generar_error_id()
        logger.error(
            "❌ LDAP: Falló autenticación para %s (ref=%s)",
            sanitizar_log_text(sanitizar_username(username_clean)),
            sanitizar_log_text(error_id),
        )
        return None

    def search_user_by_name(self, name: str, max_results: int = 20) -> List[Dict[str, str]]:
        """Busca usuarios por nombre (displayName) o sAMAccountName."""
        term = (name or "").strip()
        if not term:
            return []

        safe_term = escape_filter_chars(term)
        ldap_filter = f"(|(displayName=*{safe_term}*)(sAMAccountName=*{safe_term}*))"
        return self._search_users(ldap_filter, max_results=max_results)

    def search_user_by_email(self, email: str, max_results: int = 20) -> List[Dict[str, str]]:
        """Busca usuarios por correo."""
        term = (email or "").strip()
        if not term:
            return []

        safe_term = escape_filter_chars(term)
        ldap_filter = f"(mail=*{safe_term}*)"
        return self._search_users(ldap_filter, max_results=max_results)

    def _search_users(self, ldap_filter: str, max_results: int = 20) -> List[Dict[str, str]]:
        if not self.search_base:
            logger.error("LDAP_SEARCH_BASE no configurado")
            return []

        last_error: Optional[str] = None

        for ep in self._endpoints_to_try():
            try:
                server = self._make_server(ep)

                conn = self._service_bind(server)
                if conn is None:
                    last_error = "Bind de servicio falló"
                    break

                attrs = [
                    "sAMAccountName",
                    "displayName",
                    "mail",
                    "department",
                    "title",
                    "distinguishedName",
                ]

                conn.search(
                    search_base=self.search_base,
                    search_filter=ldap_filter,
                    search_scope=SUBTREE,
                    attributes=attrs,
                    size_limit=max_results,
                )

                results: List[Dict[str, str]] = []
                for entry in conn.entries:
                    results.append(
                        {
                            "usuario": str(getattr(entry, "sAMAccountName", "") or ""),
                            "nombre": str(getattr(entry, "displayName", "") or ""),
                            "email": str(getattr(entry, "mail", "") or ""),
                            "departamento": str(getattr(entry, "department", "") or ""),
                            "cargo": str(getattr(entry, "title", "") or ""),
                            "dn": str(getattr(entry, "distinguishedName", "") or ""),
                        }
                    )

                try:
                    conn.unbind()
                except Exception:
                    pass

                self._last_good = ep
                return results

            except LDAPSocketOpenError:
                last_error = "No se pudo abrir socket"
                continue
            except Exception:
                last_error = "Error interno"
                break

        if last_error:
            logger.error("❌ LDAP: Búsqueda falló: %s", sanitizar_log_text(last_error))
        return []

    def get_user_details(self, username: str, conn: Optional[Connection] = None) -> Optional[Dict[str, Any]]:
        """Obtiene detalles del usuario. Si se pasa `conn`, se usa esa conexión."""
        user = (username or "").strip()
        if not user or not self.search_base:
            return None

        safe_user = escape_filter_chars(user)
        ldap_filter = f"(sAMAccountName={safe_user})"
        attrs = ["displayName", "mail", "department", "title", "memberOf"]

        def _extract(entry) -> Dict[str, Any]:
            display_name = str(getattr(entry, "displayName", "") or "")
            mail = str(getattr(entry, "mail", "") or "")
            dept = str(getattr(entry, "department", "") or "")
            title = str(getattr(entry, "title", "") or "")

            groups_val = []
            try:
                member_of = getattr(entry, "memberOf", None)
                if member_of is not None:
                    # ldap3 entry attributes suelen tener .values
                    vals = getattr(member_of, "values", None)
                    if vals:
                        groups_val = list(vals)
                    else:
                        groups_val = [str(member_of)]
            except Exception:
                groups_val = []

            return {
                "nombre": display_name,
                "email": mail,
                "departamento": dept,
                "cargo": title,
                # llaves alternativas
                "full_name": display_name,
                "department": dept,
                "groups": groups_val,
            }

        if conn is not None:
            try:
                conn.search(
                    search_base=self.search_base,
                    search_filter=ldap_filter,
                    search_scope=SUBTREE,
                    attributes=attrs,
                    size_limit=1,
                )
                if not conn.entries:
                    return None
                return _extract(conn.entries[0])
            except Exception:
                return None

        for ep in self._endpoints_to_try():
            try:
                server = self._make_server(ep)
                service_conn = self._service_bind(server)
                if service_conn is None:
                    return None

                service_conn.search(
                    search_base=self.search_base,
                    search_filter=ldap_filter,
                    search_scope=SUBTREE,
                    attributes=attrs,
                    size_limit=1,
                )

                if not service_conn.entries:
                    try:
                        service_conn.unbind()
                    except Exception:
                        pass
                    return None

                data = _extract(service_conn.entries[0])

                try:
                    service_conn.unbind()
                except Exception:
                    pass

                self._last_good = ep
                return data

            except LDAPSocketOpenError:
                continue
            except Exception:
                break

        return None


# Instancia global usada por el resto de la app
ad_auth = ADAuth()
