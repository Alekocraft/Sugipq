#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_vulnerabilities_17.py

Validador local (sin dependencias externas) para detectar patrones de vulnerabilidades
reportadas por Kiuwan/OWASP/CWE en un conjunto de archivos "críticos" (17 por defecto).

Clasificación (4 niveles):
  - MUY_ALTA
  - ALTA
  - MEDIA
  - BAJA

Salida:
  - Consola: resumen + listado agrupado por clasificación
  - TXT: vulnerabilities_validation_report.txt (por defecto)
  - JSON opcional (--json-out)

Ejecución (desde la raíz del proyecto):
  python validate_vulnerabilities_17.py

Opciones útiles:
  --targets path1 path2 ...   Escanea SOLO estos archivos (relativos a la raíz)
  --all                       Escanea todo el repo (exts: .py,.html,.js,.jinja,.j2,.ts,.tsx)
  --paths dir1 dir2 ...       Limita el escaneo a directorios/archivos (solo con --all)
  --context 0|1|2             Imprime N líneas de contexto (default 0)
  --relaxed                   Reduce falsos positivos (NO recomendado)
  --txt-out archivo.txt       Cambia ruta del reporte TXT
  --json-out reporte.json     Exporta hallazgos en JSON
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


# ---------------------------------------------------------------------
# Configuración: archivos objetivo (17 por defecto)
# ---------------------------------------------------------------------
DEFAULT_TARGET_FILES: List[str] = [
    "app.py",
    "solicitudes.py",
    "blueprints/confirmacion_asignaciones.py",
    "blueprints/materials.py",               # alias -> blueprints/materiales.py
    "blueprints/oficinas.py",
    "blueprints/aprobacion.py",
    "blueprints/inventario_corporativo.py",
    "blueprints/reportes.py",
    "blueprints/solicitudes.py",
    "blueprints/usuarios.py",
    "services/auth_service.py",
    "services/notification_service.py",
    "utils/ldap_auth.py",
    "config/permissions.py",
    "config/config.py",
    "config/ldap_config.py",
    "templates/confirmacion/confirmar.html",
]

# Si en tu repo los nombres difieren, agrega el alias aquí.
TARGET_ALIASES: Dict[str, List[str]] = {
    "blueprints/materials.py": ["blueprints/materiales.py"],
    "blueprints/materiales.py": ["blueprints/materials.py"],
}

# Archivos/exts que se escanean cuando se usa --all
TEXT_EXTENSIONS = {".py", ".html", ".htm", ".js", ".jsx", ".ts", ".tsx", ".jinja", ".j2"}

EXCLUDE_DIRS = {
    ".git", ".hg", ".svn",
    "__pycache__", ".pytest_cache", ".mypy_cache",
    ".venv", "venv", "env",
    "node_modules", "dist", "build",
    ".idea", ".vscode",
}

EXCLUDE_FILES = {".env"}


# ---------------------------------------------------------------------
# Clasificación
# ---------------------------------------------------------------------
SEV_MUY_ALTA = "MUY_ALTA"
SEV_ALTA = "ALTA"
SEV_MEDIA = "MEDIA"
SEV_BAJA = "BAJA"
SEVERITY_ORDER = [SEV_MUY_ALTA, SEV_ALTA, SEV_MEDIA, SEV_BAJA]


@dataclass(frozen=True)
class RuleInfo:
    rule_id: str
    title: str
    severity: str


RULES: Dict[str, RuleInfo] = {
    # Seguridad
    "CWE-79": RuleInfo("CWE-79", "XSS / DOM-based XSS (inyección de scripts)", SEV_MUY_ALTA),
    "CWE-117": RuleInfo("CWE-117", "Log forging (input no validado en logs)", SEV_MUY_ALTA),
    "CWE-532": RuleInfo("CWE-532", "Exposición de información sensible en logs", SEV_BAJA),
    "CWE-209": RuleInfo("CWE-209", "Exposición de detalles técnicos en mensajes de error", SEV_MEDIA),
    "CWE-311": RuleInfo("CWE-311", "Transporte inseguro (HTTP sin TLS)", SEV_ALTA),
    "CWE-698": RuleInfo("CWE-698", "Execution After Redirect (EAR)", SEV_ALTA),
    "CWE-601": RuleInfo("CWE-601", "Open Redirect (redirección a sitio no confiable)", SEV_ALTA),
    "CWE-1022": RuleInfo("CWE-1022", "Reverse tabnabbing (target=_blank sin rel=noopener)", SEV_MEDIA),
    "CWE-200": RuleInfo("CWE-200", "IP hardcodeada / fuga de info (hardcoding)", SEV_MEDIA),
    "CWE-20": RuleInfo("CWE-20", "Validación deshabilitada (novalidate)", SEV_BAJA),

    # Mantenibilidad
    "CWE-563": RuleInfo("CWE-563", "Avoid unused local variable (variable local no usada)", SEV_ALTA),

    # Hardening
    "HARDENING": RuleInfo("HARDENING", "Hardening (configuración insegura)", SEV_ALTA),

    # Interno del script
    "PARSER": RuleInfo("PARSER", "No se pudo parsear el archivo (AST/SyntaxError)", SEV_BAJA),
    "MISSING": RuleInfo("MISSING", "Archivo objetivo no encontrado (no se pudo validar)", SEV_BAJA),
}

# ---------------------------------------------------------------------
# Overrides de prioridad (para alinear con el modelo/ PDF de Kiuwan)
# ---------------------------------------------------------------------
PRIORITY_SYNONYMS: Dict[str, str] = {
    # Español
    "MUY_ALTA": SEV_MUY_ALTA,
    "MUY ALTA": SEV_MUY_ALTA,
    "ALTA": SEV_ALTA,
    "MEDIA": SEV_MEDIA,
    "MEDIO": SEV_MEDIA,
    "BAJA": SEV_BAJA,
    "BAJO": SEV_BAJA,
    # Inglés (Kiuwan)
    "VERY HIGH": SEV_MUY_ALTA,
    "VERY_HIGH": SEV_MUY_ALTA,
    "HIGH": SEV_ALTA,
    "NORMAL": SEV_MEDIA,   # en Kiuwan, "Normal" es el nivel medio
    "LOW": SEV_BAJA,
}

def apply_priority_overrides(priority_map_path: Optional[str]) -> None:
    """
    Permite sobreescribir la severidad por Rule ID (ej: CWE-117).
    Formato JSON esperado:
        {"CWE-117": "ALTA", "CWE-532": "BAJA"}
    También acepta valores estilo Kiuwan: "HIGH", "NORMAL", "LOW", "VERY HIGH".
    """
    if not priority_map_path:
        return

    p = Path(priority_map_path)
    if not p.exists() or not p.is_file():
        eprint(f"[WARN] --priority-map no encontrado: {priority_map_path}")
        return

    try:
        data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except Exception as ex:
        eprint(f"[WARN] No se pudo leer --priority-map ({priority_map_path}): {ex}")
        return

    if not isinstance(data, dict):
        eprint("[WARN] --priority-map debe ser un objeto JSON (dict). Ej: {\"CWE-117\":\"ALTA\"}")
        return

    for rid, sev in data.items():
        if not isinstance(rid, str) or not isinstance(sev, str):
            continue
        rid = rid.strip()
        sev_key = sev.strip().upper()
        mapped = PRIORITY_SYNONYMS.get(sev_key)
        if not mapped:
            eprint(f"[WARN] Severidad inválida en --priority-map para {rid}: {sev!r}")
            continue
        if rid not in RULES:
            eprint(f"[WARN] Rule ID no reconocido en --priority-map: {rid}")
            continue
        base = RULES[rid]
        RULES[rid] = RuleInfo(base.rule_id, base.title, mapped)




@dataclass(frozen=True)
class Finding:
    severity: str
    rule_id: str
    rule_title: str
    path: str
    line: int
    detail: str
    snippet: str = ""


# ---------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------
def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def normalize_path(p: str) -> str:
    return p.replace("\\", "/")


def is_binary_file(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            chunk = f.read(2048)
        return b"\0" in chunk
    except Exception:
        return True


def read_text(path: Path) -> Optional[str]:
    if is_binary_file(path):
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        try:
            return path.read_text(encoding="latin-1", errors="replace")
        except Exception:
            return None


def line_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, max(0, offset)) + 1


def get_line(text: str, lineno: int) -> str:
    lines = text.splitlines()
    if 1 <= lineno <= len(lines):
        return lines[lineno - 1]
    return ""


def find_line_snippet(text: str, lineno: int, context: int) -> str:
    if context <= 0:
        return get_line(text, lineno)
    lines = text.splitlines()
    if not lines:
        return ""
    start = max(0, lineno - 1 - context)
    end = min(len(lines), lineno + context)
    block: List[str] = []
    for i in range(start, end):
        prefix = ">" if (i + 1) == lineno else " "
        ln = lines[i]
        if len(ln) > 240:
            ln = ln[:240] + "…"
        block.append(f"{prefix}{i+1:04d}: {ln}")
    return "\n".join(block)


def safe_ast_parse(path: Path, text: str) -> Optional[ast.AST]:
    try:
        return ast.parse(text, filename=str(path))
    except SyntaxError:
        return None


# ---------------------------------------------------------------------
# Resolución de targets
# ---------------------------------------------------------------------
def resolve_targets(root: Path, targets: List[str]) -> Tuple[List[Path], List[str]]:
    """
    Devuelve:
      - archivos existentes
      - lista de targets no encontrados (para reportar)
    """
    existing: List[Path] = []
    missing: List[str] = []

    for t in targets:
        candidates = [t] + TARGET_ALIASES.get(t, [])
        found: Optional[Path] = None
        for c in candidates:
            p = (root / c)
            if p.exists() and p.is_file():
                found = p
                break
        if found is None:
            missing.append(t)
        else:
            existing.append(found)

    # dedup por path real
    uniq: Dict[str, Path] = {}
    for p in existing:
        key = normalize_path(str(p.resolve()))
        uniq[key] = p
    return list(uniq.values()), missing


def iter_repo_files(root: Path, only_paths: Optional[List[str]] = None) -> Iterable[Path]:
    """
    Itera por todos los archivos con extensiones de interés, excluyendo carpetas típicas.
    Si only_paths se provee, limita el rglob a esas rutas.
    """
    bases = [root] if not only_paths else [root / p for p in only_paths]
    seen: Set[Path] = set()

    for base in bases:
        if not base.exists():
            continue
        if base.is_file():
            if base.name in EXCLUDE_FILES:
                continue
            if base.suffix.lower() in TEXT_EXTENSIONS:
                yield base
            continue

        for p in base.rglob("*"):
            if p in seen:
                continue
            seen.add(p)

            if not p.is_file():
                continue
            if any(part in EXCLUDE_DIRS for part in p.parts):
                continue
            if p.name in EXCLUDE_FILES:
                continue
            if p.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            yield p


# ---------------------------------------------------------------------
# Reglas / Heurísticas (alineadas con hallazgos del PDF Kiuwan)
# ---------------------------------------------------------------------
# CWE-200: IP hardcodeada
IPV4_RE = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
ALLOWED_IPS = {"0.0.0.0", "127.0.0.1", "255.255.255.255"}

# CWE-20: novalidate
NOVALIDATE_RE = re.compile(r"\bnovalidate\b", re.IGNORECASE)

# CWE-1022: target="_blank" sin rel="noopener noreferrer"
TARGET_BLANK_RE = re.compile(r'target\s*=\s*["\']_blank["\']', re.IGNORECASE)

# CWE-117/532: logger.* con input sin sanitizar o keywords sensibles
LOGGER_METHODS = {"debug", "info", "warning", "error", "critical", "exception"}
SANITIZER_PREFIXES = ("sanitizar_", "sanitize_", "sanitise_")
SENSITIVE_KEYWORDS = {
    "password", "passwd", "contraseña", "contrasena",
    "token", "secret", "apikey", "api_key", "key",
    "authorization", "cookie", "session", "jwt",
    "ldap", "dsn", "connection string", "cadena de conexion",
}

# CWE-209: exposición de detalles técnicos
CWE209_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("type(e).__name__", re.compile(r"type\s*\(\s*\w+\s*\)\s*\.\s*__name__", re.IGNORECASE)),
    ("traceback", re.compile(r"\btraceback\b", re.IGNORECASE)),
    ("format_exc", re.compile(r"\bformat_exc\b", re.IGNORECASE)),
    ("str(e)", re.compile(r"\bstr\s*\(\s*\w+\s*\)", re.IGNORECASE)),
    ("repr(e)", re.compile(r"\brepr\s*\(\s*\w+\s*\)", re.IGNORECASE)),
]

# CWE-311: app.run sin ssl_context (o ssl_context=None)
APP_RUN_FILE_CANDIDATES = ["app.py", "wsgi.py", "main.py", "run.py"]


def _contains_sensitive_keyword(s: str) -> bool:
    lower = s.lower()
    return any(k in lower for k in SENSITIVE_KEYWORDS)


def _call_func_name(call: ast.Call) -> str:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return ""


def _is_exception_typename(expr: ast.AST) -> bool:
    # type(e).__name__
    if isinstance(expr, ast.Attribute) and expr.attr == "__name__":
        v = expr.value
        if isinstance(v, ast.Call) and _call_func_name(v) == "type" and v.args:
            return True
    return False


def _is_sanitized_expr(expr: ast.AST) -> bool:
    # Aceptamos sanitizadores y casts seguros
    if _is_exception_typename(expr):
        return True
    if isinstance(expr, ast.Call):
        fname = _call_func_name(expr)
        if fname.startswith(SANITIZER_PREFIXES):
            return True
        if fname in {"int", "float", "bool"}:
            return True
        if fname in {"uuid4", "UUID"}:
            return True
    if isinstance(expr, ast.Constant):
        return True
    if isinstance(expr, (ast.Num, ast.BinOp, ast.UnaryOp)):
        return True
    return False


# ---------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------
def check_hardcoded_ips(root: Path, files: Iterable[Path], relaxed: bool, context: int) -> List[Finding]:
    r = RULES["CWE-200"]
    findings: List[Finding] = []

    for path in files:
        text = read_text(path)
        if text is None:
            continue

        for m in IPV4_RE.finditer(text):
            ip = m.group(0)
            if ip in ALLOWED_IPS:
                continue

            # relaxed: ignora comentarios obvios
            if relaxed:
                lineno = line_for_offset(text, m.start())
                line = get_line(text, lineno)
                if line.lstrip().startswith("#") or "<!--" in line:
                    continue

            lineno = line_for_offset(text, m.start())
            findings.append(Finding(
                severity=r.severity,
                rule_id=r.rule_id,
                rule_title=r.title,
                path=normalize_path(str(path.relative_to(root))),
                line=lineno,
                detail=f"IP hardcodeada detectada: {ip}",
                snippet=find_line_snippet(text, lineno, context),
            ))

        # Caso típico: os.getenv("X", "10.0.0.1")
        if path.suffix.lower() == ".py":
            for m in re.finditer(
                r"os\.getenv\(\s*['\"][^'\"]+['\"]\s*,\s*['\"]((?:\d{1,3}\.){3}\d{1,3})['\"]\s*\)",
                text
            ):
                ip = m.group(1)
                if ip in ALLOWED_IPS:
                    continue
                lineno = line_for_offset(text, m.start())
                findings.append(Finding(
                    severity=r.severity,
                    rule_id=r.rule_id,
                    rule_title=r.title,
                    path=normalize_path(str(path.relative_to(root))),
                    line=lineno,
                    detail=f"os.getenv(...) con IP por defecto ({ip}). En producción, el default no debe ser una IP hardcodeada.",
                    snippet=find_line_snippet(text, lineno, context),
                ))

    return findings


def check_form_validation_disabled(root: Path, files: Iterable[Path], context: int) -> List[Finding]:
    r = RULES["CWE-20"]
    findings: List[Finding] = []
    for path in files:
        if path.suffix.lower() not in {".html", ".htm", ".jinja", ".j2"}:
            continue
        text = read_text(path)
        if text is None:
            continue
        for m in NOVALIDATE_RE.finditer(text):
            lineno = line_for_offset(text, m.start())
            findings.append(Finding(
                severity=r.severity,
                rule_id=r.rule_id,
                rule_title=r.title,
                path=normalize_path(str(path.relative_to(root))),
                line=lineno,
                detail="Encontrado atributo 'novalidate' (deshabilita validación del navegador).",
                snippet=find_line_snippet(text, lineno, context),
            ))
    return findings


def check_target_blank_rel(root: Path, files: Iterable[Path], context: int) -> List[Finding]:
    r = RULES["CWE-1022"]
    findings: List[Finding] = []

    rel_attr = re.compile(r"\brel\s*=\s*['\"][^'\"]*['\"]", re.IGNORECASE)
    has_noopener = re.compile(r"\bnoopener\b", re.IGNORECASE)
    has_noreferrer = re.compile(r"\bnoreferrer\b", re.IGNORECASE)

    for path in files:
        if path.suffix.lower() not in {".html", ".htm", ".jinja", ".j2"}:
            continue
        text = read_text(path)
        if text is None:
            continue

        for m in TARGET_BLANK_RE.finditer(text):
            lineno = line_for_offset(text, m.start())
            line = get_line(text, lineno)

            # intenta capturar el tag completo (por si está partido en varias líneas)
            block = line
            if ">" not in block:
                lines = text.splitlines()
                i = lineno - 1
                for _ in range(10):
                    if i + 1 >= len(lines):
                        break
                    i += 1
                    block += "\n" + lines[i]
                    if ">" in lines[i]:
                        break

            rel_match = rel_attr.search(block)
            if not rel_match:
                ok = False
            else:
                rel_val = rel_match.group(0)
                ok = bool(has_noopener.search(rel_val) and has_noreferrer.search(rel_val))

            if not ok:
                findings.append(Finding(
                    severity=r.severity,
                    rule_id=r.rule_id,
                    rule_title=r.title,
                    path=normalize_path(str(path.relative_to(root))),
                    line=lineno,
                    detail='Encontrado target="_blank" sin rel="noopener noreferrer".',
                    snippet=find_line_snippet(text, lineno, context),
                ))

    return findings


def check_dom_xss_patterns(root: Path, files: Iterable[Path], context: int) -> List[Finding]:
    r = RULES["CWE-79"]
    findings: List[Finding] = []

    dangerous_sinks = [
        re.compile(r"\binnerHTML\s*=\s*[^;]+", re.IGNORECASE),
        re.compile(r"\bouterHTML\s*=\s*[^;]+", re.IGNORECASE),
        re.compile(r"\binsertAdjacentHTML\s*\(", re.IGNORECASE),
        re.compile(r"\bdocument\.write\s*\(", re.IGNORECASE),
    ]

    for path in files:
        if path.suffix.lower() not in {".html", ".htm", ".js", ".jsx", ".ts", ".tsx", ".jinja", ".j2"}:
            continue
        text = read_text(path)
        if text is None:
            continue

        # Caso específico (observado en Kiuwan): setAttribute('type', type) sin whitelist.
        for m in re.finditer(r"setAttribute\s*\(\s*['\"]type['\"]\s*,\s*type\s*\)", text, flags=re.IGNORECASE):
            lineno = line_for_offset(text, m.start())
            lines = text.splitlines()
            window = "\n".join(lines[max(0, lineno - 15): min(len(lines), lineno + 15)])
            has_whitelist = (
                (re.search(r"type\s*===\s*['\"]password['\"]", window) and re.search(r"type\s*===\s*['\"]text['\"]", window))
                or re.search(r"\[\s*['\"]password['\"]\s*,\s*['\"]text['\"]\s*\]\s*\.includes\s*\(\s*type\s*\)", window)
            )
            if not has_whitelist:
                findings.append(Finding(
                    severity=r.severity,
                    rule_id=r.rule_id,
                    rule_title=r.title,
                    path=normalize_path(str(path.relative_to(root))),
                    line=lineno,
                    detail="setAttribute('type', type) sin whitelist (permitir solo 'password' o 'text').",
                    snippet=find_line_snippet(text, lineno, context),
                ))

        # Sinks genéricos (heurístico)
        for sink in dangerous_sinks:
            for m in sink.finditer(text):
                lineno = line_for_offset(text, m.start())
                line = get_line(text, lineno)
                if re.search(r"\bescape\b|\bsanitize\b|\bsanitizar\b", line, flags=re.IGNORECASE):
                    continue
                findings.append(Finding(
                    severity=r.severity,
                    rule_id=r.rule_id,
                    rule_title=r.title,
                    path=normalize_path(str(path.relative_to(root))),
                    line=lineno,
                    detail=f"Uso de sink DOM potencialmente peligroso ({sink.pattern}).",
                    snippet=find_line_snippet(text, lineno, context),
                ))

    return findings


def check_logging_issues(root: Path, files: Iterable[Path], relaxed: bool, context: int) -> List[Finding]:
    """
    CWE-117 / CWE-532
      - f-string en logger.* con interpolación no sanitizada
      - logger.* con %s/{} y args no sanitizados
      - keywords sensibles en el mensaje o variables con nombre sensible
    """
    findings: List[Finding] = []
    r117 = RULES["CWE-117"]
    r532 = RULES["CWE-532"]

    for path in files:
        if path.suffix.lower() != ".py":
            continue
        text = read_text(path)
        if text is None:
            continue

        tree = safe_ast_parse(path, text)
        if tree is None:
            findings.append(Finding(
                severity=RULES["PARSER"].severity,
                rule_id=RULES["PARSER"].rule_id,
                rule_title=RULES["PARSER"].title,
                path=normalize_path(str(path.relative_to(root))),
                line=1,
                detail="No se pudo parsear el archivo Python (SyntaxError).",
                snippet="",
            ))
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            method = node.func.attr
            if method not in LOGGER_METHODS:
                continue
            if not node.args:
                continue

            msg_arg = node.args[0]
            lineno = getattr(node, "lineno", 1)

            # 1) f-string
            if isinstance(msg_arg, ast.JoinedStr):
                for fv in [x for x in msg_arg.values if isinstance(x, ast.FormattedValue)]:
                    if not _is_sanitized_expr(fv.value):
                        findings.append(Finding(
                            severity=r117.severity,
                            rule_id=r117.rule_id,
                            rule_title=r117.title,
                            path=normalize_path(str(path.relative_to(root))),
                            line=lineno,
                            detail="logger.* usa f-string con interpolación NO sanitizada. Usa sanitizar_log_text(...) o evita interpolar input.",
                            snippet=find_line_snippet(text, lineno, context),
                        ))
                        break

                const_parts = "".join(
                    [x.value for x in msg_arg.values if isinstance(x, ast.Constant) and isinstance(x.value, str)]
                )
                if _contains_sensitive_keyword(const_parts):
                    findings.append(Finding(
                        severity=r532.severity,
                        rule_id=r532.rule_id,
                        rule_title=r532.title,
                        path=normalize_path(str(path.relative_to(root))),
                        line=lineno,
                        detail="Mensaje de log contiene keywords sensibles (password/token/authorization/cookie/etc.).",
                        snippet=find_line_snippet(text, lineno, context),
                    ))

            # 2) formato logger.info("..%s..", var)
            if isinstance(msg_arg, ast.Constant) and isinstance(msg_arg.value, str):
                msg_text = msg_arg.value
                if _contains_sensitive_keyword(msg_text):
                    findings.append(Finding(
                        severity=r532.severity,
                        rule_id=r532.rule_id,
                        rule_title=r532.title,
                        path=normalize_path(str(path.relative_to(root))),
                        line=lineno,
                        detail="Mensaje de log contiene keywords sensibles (password/token/authorization/cookie/etc.).",
                        snippet=find_line_snippet(text, lineno, context),
                    ))

                if ("%s" in msg_text or "{}" in msg_text) and len(node.args) > 1:
                    for extra in node.args[1:]:
                        if not _is_sanitized_expr(extra):
                            if relaxed and isinstance(extra, ast.Name) and extra.id.endswith("_id"):
                                continue
                            findings.append(Finding(
                                severity=r117.severity,
                                rule_id=r117.rule_id,
                                rule_title=r117.title,
                                path=normalize_path(str(path.relative_to(root))),
                                line=lineno,
                                detail="logger.* pasa argumento no sanitizado a formato %s/{}. Envuélvelo con sanitizar_log_text(...) o sanitizador específico.",
                                snippet=find_line_snippet(text, lineno, context),
                            ))
                            break

            # 3) variables sensibles por nombre
            for arg in node.args[1:]:
                if isinstance(arg, ast.Name) and _contains_sensitive_keyword(arg.id):
                    findings.append(Finding(
                        severity=r532.severity,
                        rule_id=r532.rule_id,
                        rule_title=r532.title,
                        path=normalize_path(str(path.relative_to(root))),
                        line=lineno,
                        detail=f"Posible dato sensible loggeado por nombre de variable: {arg.id}",
                        snippet=find_line_snippet(text, lineno, context),
                    ))

    return findings


def check_sensitive_error_messages(root: Path, files: Iterable[Path], context: int) -> List[Finding]:
    r = RULES["CWE-209"]
    findings: List[Finding] = []

    for path in files:
        if path.suffix.lower() != ".py":
            continue
        text = read_text(path)
        if text is None:
            continue

        per_line: Dict[int, Set[str]] = {}
        for label, pat in CWE209_PATTERNS:
            for m in pat.finditer(text):
                lineno = line_for_offset(text, m.start())
                per_line.setdefault(lineno, set()).add(label)

        for lineno in sorted(per_line.keys()):
            labels = sorted(per_line[lineno])
            findings.append(Finding(
                severity=r.severity,
                rule_id=r.rule_id,
                rule_title=r.title,
                path=normalize_path(str(path.relative_to(root))),
                line=lineno,
                detail="Fuga de detalle técnico detectada en error/log: " + ", ".join(labels),
                snippet=find_line_snippet(text, lineno, context),
            ))

    return findings


def check_insecure_transport(root: Path, files: Iterable[Path], context: int) -> List[Finding]:
    """
    CWE-311: valida app.run(... ssl_context=...) en el entrypoint.
    - Si ssl_context no está presente o es None -> hallazgo.
    - Si ssl_context es variable pero se asigna None en algún punto -> hallazgo.
    """
    r = RULES["CWE-311"]
    findings: List[Finding] = []

    # prioriza app.py si está en la lista de files
    existing = {normalize_path(str(p.relative_to(root))): p for p in files if p.exists()}
    target: Optional[Path] = None
    for cand in APP_RUN_FILE_CANDIDATES:
        if cand in existing:
            target = existing[cand]
            break
        p = root / cand
        if p.exists() and p.is_file():
            target = p
            break

    if target is None:
        findings.append(Finding(
            severity=r.severity,
            rule_id=r.rule_id,
            rule_title=r.title,
            path="(no encontrado)",
            line=1,
            detail="No se encontró un entrypoint típico (app.py/wsgi.py/main.py/run.py). No se pudo validar TLS.",
            snippet="",
        ))
        return findings

    text = read_text(target)
    if text is None:
        findings.append(Finding(
            severity=r.severity,
            rule_id=r.rule_id,
            rule_title=r.title,
            path=normalize_path(str(target.relative_to(root))),
            line=1,
            detail="No se pudo leer el entrypoint para validar TLS.",
            snippet="",
        ))
        return findings

    tree = safe_ast_parse(target, text)
    if tree is None:
        findings.append(Finding(
            severity=RULES["PARSER"].severity,
            rule_id=RULES["PARSER"].rule_id,
            rule_title=RULES["PARSER"].title,
            path=normalize_path(str(target.relative_to(root))),
            line=1,
            detail="No se pudo parsear el entrypoint para validar TLS (SyntaxError).",
            snippet="",
        ))
        return findings

    # detecta asignaciones: ssl_context = None
    ssl_ctx_is_none = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "ssl_context":
                    if isinstance(node.value, ast.Constant) and node.value.value is None:
                        ssl_ctx_is_none = True

    found_run = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "run":
            continue

        found_run = True
        lineno = getattr(node, "lineno", 1)

        kw = {k.arg: k.value for k in node.keywords if k.arg}
        ssl = kw.get("ssl_context")

        if ssl is None:
            findings.append(Finding(
                severity=r.severity,
                rule_id=r.rule_id,
                rule_title=r.title,
                path=normalize_path(str(target.relative_to(root))),
                line=lineno,
                detail="app.run(...) sin ssl_context=... (TLS requerido).",
                snippet=find_line_snippet(text, lineno, context),
            ))
        elif isinstance(ssl, ast.Constant) and ssl.value is None:
            findings.append(Finding(
                severity=r.severity,
                rule_id=r.rule_id,
                rule_title=r.title,
                path=normalize_path(str(target.relative_to(root))),
                line=lineno,
                detail="ssl_context=None en app.run(...). Debe estar configurado para TLS.",
                snippet=find_line_snippet(text, lineno, context),
            ))
        elif isinstance(ssl, ast.Name) and ssl.id == "ssl_context" and ssl_ctx_is_none:
            findings.append(Finding(
                severity=r.severity,
                rule_id=r.rule_id,
                rule_title=r.title,
                path=normalize_path(str(target.relative_to(root))),
                line=lineno,
                detail="ssl_context se pasa como variable, pero en el archivo hay asignación ssl_context=None (posible HTTP sin TLS).",
                snippet=find_line_snippet(text, lineno, context),
            ))

        dbg = kw.get("debug")
        if isinstance(dbg, ast.Constant) and dbg.value is True:
            findings.append(Finding(
                severity=RULES["HARDENING"].severity,
                rule_id=RULES["HARDENING"].rule_id,
                rule_title=RULES["HARDENING"].title,
                path=normalize_path(str(target.relative_to(root))),
                line=lineno,
                detail="debug=True en app.run(...). En entornos no locales debe ser False.",
                snippet=find_line_snippet(text, lineno, context),
            ))

    if not found_run:
        findings.append(Finding(
            severity=r.severity,
            rule_id=r.rule_id,
            rule_title=r.title,
            path=normalize_path(str(target.relative_to(root))),
            line=1,
            detail="No se encontró ninguna llamada a *.run(...). No se pudo validar TLS.",
            snippet="",
        ))

    return findings


def _stmt_contains_redirect_call(stmt: ast.stmt) -> bool:
    for node in ast.walk(stmt):
        if isinstance(node, ast.Call) and _call_func_name(node) == "redirect":
            return True
    return False


def _is_return_redirect(stmt: ast.stmt) -> bool:
    return isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Call) and _call_func_name(stmt.value) == "redirect"


def _is_allowed_after_redirect(stmt: ast.stmt) -> bool:
    if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue, ast.Pass)):
        return True
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        call = stmt.value
        if isinstance(call.func, ast.Attribute) and call.func.attr in LOGGER_METHODS:
            return True
    return False


def _check_redirect_in_stmt_list(
    text: str,
    stmts: List[ast.stmt],
    path_rel: str,
    context: int,
    relaxed: bool,
    findings: List[Finding],
) -> None:
    """
    Heurística para CWE-698:
      - redirect(...) sin 'return redirect(...)' => hallazgo
      - 'return redirect(...)' que no es la última sentencia del bloque => hallazgo
    """
    r = RULES["CWE-698"]

    for idx, stmt in enumerate(stmts):
        # recursión sobre bloques anidados
        if isinstance(stmt, ast.If):
            _check_redirect_in_stmt_list(text, stmt.body, path_rel, context, relaxed, findings)
            _check_redirect_in_stmt_list(text, stmt.orelse, path_rel, context, relaxed, findings)

        if isinstance(stmt, (ast.For, ast.While, ast.With, ast.Try)):
            if hasattr(stmt, "body"):
                _check_redirect_in_stmt_list(text, getattr(stmt, "body", []) or [], path_rel, context, relaxed, findings)
            if hasattr(stmt, "orelse"):
                _check_redirect_in_stmt_list(text, getattr(stmt, "orelse", []) or [], path_rel, context, relaxed, findings)
            if hasattr(stmt, "finalbody"):
                _check_redirect_in_stmt_list(text, getattr(stmt, "finalbody", []) or [], path_rel, context, relaxed, findings)
            if isinstance(stmt, ast.Try):
                for h in stmt.handlers:
                    _check_redirect_in_stmt_list(text, h.body, path_rel, context, relaxed, findings)

        lineno = getattr(stmt, "lineno", None) or 1

        # Caso 1: return redirect(...) pero hay statements después en el mismo bloque
        if _is_return_redirect(stmt):
            if idx < len(stmts) - 1:
                after = stmts[idx + 1]
                if relaxed and _is_allowed_after_redirect(after):
                    continue
                findings.append(Finding(
                    severity=r.severity,
                    rule_id=r.rule_id,
                    rule_title=r.title,
                    path=path_rel,
                    line=lineno,
                    detail="Hay sentencias después de 'return redirect(...)' en el mismo bloque (SAST puede marcar EAR).",
                    snippet=find_line_snippet(text, lineno, context),
                ))
            continue

        # Caso 2: cualquier llamada a redirect(...) sin return redirect(...)
        if _stmt_contains_redirect_call(stmt):
            findings.append(Finding(
                severity=r.severity,
                rule_id=r.rule_id,
                rule_title=r.title,
                path=path_rel,
                line=lineno,
                detail="Llamada redirect(...) sin 'return redirect(...)' (posible EAR).",
                snippet=find_line_snippet(text, lineno, context),
            ))


def check_execution_after_redirect(root: Path, files: Iterable[Path], context: int, relaxed: bool) -> List[Finding]:
    findings: List[Finding] = []
    for path in files:
        if path.suffix.lower() != ".py":
            continue
        text = read_text(path)
        if text is None:
            continue
        tree = safe_ast_parse(path, text)
        if tree is None:
            continue

        path_rel = normalize_path(str(path.relative_to(root)))

        if isinstance(tree, ast.Module):
            _check_redirect_in_stmt_list(text, tree.body, path_rel, context, relaxed, findings)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _check_redirect_in_stmt_list(text, node.body, path_rel, context, relaxed, findings)

    return findings


def check_open_redirect_js(root: Path, files: Iterable[Path], context: int, relaxed: bool) -> List[Finding]:
    """
    CWE-601 (heurístico):
      - window.location / location.href asignado usando fuentes comunes (location.search, URLSearchParams, etc.)
    """
    r = RULES["CWE-601"]
    findings: List[Finding] = []

    if relaxed:
        return findings

    sinks = [
        re.compile(r"\bwindow\.location\.href\s*=\s*(.+);", re.IGNORECASE),
        re.compile(r"\blocation\.href\s*=\s*(.+);", re.IGNORECASE),
        re.compile(r"\bwindow\.location\s*=\s*(.+);", re.IGNORECASE),
        re.compile(r"\blocation\s*=\s*(.+);", re.IGNORECASE),
    ]
    sources = re.compile(r"(location\.search|URLSearchParams|params\.get\(|get\(['\"]next['\"]\)|get\(['\"]url['\"]\))", re.IGNORECASE)

    for path in files:
        if path.suffix.lower() not in {".html", ".htm", ".js", ".jsx", ".ts", ".tsx", ".jinja", ".j2"}:
            continue
        text = read_text(path)
        if text is None:
            continue
        for sink in sinks:
            for m in sink.finditer(text):
                rhs = m.group(1)
                if not sources.search(rhs):
                    continue
                lineno = line_for_offset(text, m.start())
                findings.append(Finding(
                    severity=r.severity,
                    rule_id=r.rule_id,
                    rule_title=r.title,
                    path=normalize_path(str(path.relative_to(root))),
                    line=lineno,
                    detail="Asignación a location.href/window.location desde parámetro/entrada (posible open redirect). Validar/whitelistear destinos.",
                    snippet=find_line_snippet(text, lineno, context),
                ))
    return findings


def check_cwe563_unused_locals(root: Path, files: Iterable[Path], context: int) -> List[Finding]:
    r = RULES["CWE-563"]
    findings: List[Finding] = []
    patterns = [
        r"\btooltipList\s*=\s*tooltipTriggerList\.map\(",
        r"\bnewState\s*=\s*isHidden\s*\?\s*['\"]visible['\"]\s*:\s*['\"]oculta['\"]",
        r"\busuario\s*=\s*response\.usuario\b",
        r"\binfo\s*=\s*tabla\.page\.info\(\)",
        r"\bfechaArchivo\s*=\s*new Date\(\)\.toISOString\(\)\.split\(",
    ]
    combined = re.compile("|".join(f"(?:{p})" for p in patterns), re.IGNORECASE)

    for path in files:
        if path.suffix.lower() not in {".html", ".htm", ".js", ".jsx", ".ts", ".tsx", ".jinja", ".j2"}:
            continue
        text = read_text(path)
        if text is None:
            continue
        for m in combined.finditer(text):
            lineno = line_for_offset(text, m.start())
            findings.append(Finding(
                severity=r.severity,
                rule_id=r.rule_id,
                rule_title=r.title,
                path=normalize_path(str(path.relative_to(root))),
                line=lineno,
                detail="Patrón conocido de variable local no usada (según reportes).",
                snippet=find_line_snippet(text, lineno, context),
            ))
    return findings


# ---------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------
def run_all(root: Path, files: List[Path], relaxed: bool, context: int) -> List[Finding]:
    findings: List[Finding] = []
    findings += check_hardcoded_ips(root, files, relaxed=relaxed, context=context)
    findings += check_insecure_transport(root, files, context=context)
    findings += check_form_validation_disabled(root, files, context=context)
    findings += check_target_blank_rel(root, files, context=context)
    findings += check_dom_xss_patterns(root, files, context=context)
    findings += check_logging_issues(root, files, relaxed=relaxed, context=context)
    findings += check_sensitive_error_messages(root, files, context=context)
    findings += check_execution_after_redirect(root, files, context=context, relaxed=relaxed)
    findings += check_open_redirect_js(root, files, context=context, relaxed=relaxed)
    findings += check_cwe563_unused_locals(root, files, context=context)

    # Deduplicación: misma regla + archivo + línea + detalle
    uniq: Dict[Tuple[str, str, int, str], Finding] = {}
    for f in findings:
        key = (f.rule_id, f.path, f.line, f.detail)
        uniq.setdefault(key, f)

    def sev_rank(s: str) -> int:
        try:
            return SEVERITY_ORDER.index(s)
        except ValueError:
            return len(SEVERITY_ORDER)

    ordered = sorted(
        uniq.values(),
        key=lambda x: (sev_rank(x.severity), x.rule_id, x.path, x.line, x.detail)
    )
    return ordered


def group_findings(findings: List[Finding]) -> Dict[str, Dict[str, List[Finding]]]:
    """
    {severity: {path: [findings...]}}
    """
    out: Dict[str, Dict[str, List[Finding]]] = {s: {} for s in SEVERITY_ORDER}
    for f in findings:
        out.setdefault(f.severity, {})
        out[f.severity].setdefault(f.path, []).append(f)
    # orden dentro
    for sev in out:
        for p in out[sev]:
            out[sev][p] = sorted(out[sev][p], key=lambda x: (x.line, x.rule_id, x.detail))
    return out


def compute_high_priority_file_ranking(findings: List[Finding]) -> List[Tuple[str, int, int, int]]:
    """
    Retorna lista ordenada de archivos con severidad MUY_ALTA/ALTA:
      (path, muy_alta_count, alta_count, total)

    Orden: total desc, MUY_ALTA desc, ALTA desc, path asc.
    """
    per_file: Dict[str, Dict[str, int]] = {}
    for f in findings:
        if f.severity not in {SEV_MUY_ALTA, SEV_ALTA}:
            continue
        per_file.setdefault(f.path, {SEV_MUY_ALTA: 0, SEV_ALTA: 0})
        per_file[f.path][f.severity] += 1

    ranking: List[Tuple[str, int, int, int]] = []
    for path, counts in per_file.items():
        muy = counts.get(SEV_MUY_ALTA, 0)
        alta = counts.get(SEV_ALTA, 0)
        total = muy + alta
        if total <= 0:
            continue
        ranking.append((path, muy, alta, total))

    ranking.sort(key=lambda x: (-x[3], -x[1], -x[2], x[0]))
    return ranking


def render_txt_report(root: Path, findings: List[Finding], missing: List[str]) -> str:
    grouped = group_findings(findings)
    counts = {sev: sum(len(v) for v in grouped.get(sev, {}).values()) for sev in SEVERITY_ORDER}

    lines: List[str] = []
    lines.append("VULNERABILITIES VALIDATION REPORT")
    lines.append("=" * 90)
    lines.append(f"Root: {root}")
    lines.append("Resumen por clasificación:")
    for sev in SEVERITY_ORDER:
        lines.append(f"  - {sev:8s}: {counts.get(sev, 0)}")
    lines.append("")

    if missing:
        lines.append("Archivos objetivo NO encontrados (no validados):")
        for m in sorted(set(missing)):
            lines.append(f"  - {m}")
        lines.append("")

    ranking = compute_high_priority_file_ranking(findings)
    if ranking:
        lines.append("Ranking de archivos con vulnerabilidades ALTA/MUY_ALTA (reconteo y ordenado):")
        lines.append("-" * 90)
        for path, muy, alta, total in ranking:
            lines.append(f"  - {path}: MUY_ALTA={muy}, ALTA={alta}, TOTAL={total}")
        lines.append("")

    for sev in SEVERITY_ORDER:
        total = counts.get(sev, 0)
        if total == 0:
            continue
        lines.append(f"[{sev}]")
        lines.append("-" * 90)
        for path, items in sorted(grouped[sev].items(), key=lambda x: x[0]):
            lines.append(f"  {path}  ({len(items)})")
            for f in items:
                lines.append(f"    - L{f.line}: [{f.rule_id}] {f.rule_title} :: {f.detail}")
                if f.snippet:
                    for ln in f.snippet.splitlines():
                        lines.append("      " + ln)
        lines.append("")

    if not findings:
        lines.append("OK: No se encontraron hallazgos según las reglas configuradas.")
        lines.append("")

    return "\n".join(lines)


def print_console_report(findings: List[Finding], missing: List[str], context: int) -> None:
    grouped = group_findings(findings)
    counts = {sev: sum(len(v) for v in grouped.get(sev, {}).values()) for sev in SEVERITY_ORDER}

    if findings:
        eprint("[FAIL] Hallazgos detectados.")
    else:
        print("[OK] Sin hallazgos detectados por las reglas configuradas.")

    eprint("Resumen por clasificación:")
    for sev in SEVERITY_ORDER:
        eprint(f"  - {sev:8s}: {counts.get(sev, 0)}")

    if missing:
        eprint("\nArchivos objetivo NO encontrados (no validados):")
        for m in sorted(set(missing)):
            eprint(f"  - {m}")

    
    ranking = compute_high_priority_file_ranking(findings)
    if ranking:
        eprint("\nArchivos con ALTA/MUY_ALTA (ordenado por reconteo):")
        for path, muy, alta, total in ranking:
            eprint(f"  - {path}: MUY_ALTA={muy}, ALTA={alta}, TOTAL={total}")
if not findings:
        return

    eprint("\nDetalle (agrupado por clasificación):")
    for sev in SEVERITY_ORDER:
        if counts.get(sev, 0) == 0:
            continue
        eprint(f"\n=== {sev} ===")
        for path, items in sorted(grouped[sev].items(), key=lambda x: x[0]):
            eprint(f"  {path} ({len(items)})")
            for f in items:
                eprint(f"    - L{f.line}: [{f.rule_id}] {f.detail}")
                if context > 0 and f.snippet:
                    for ln in f.snippet.splitlines():
                        eprint("      " + ln)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Valida vulnerabilidades (17 archivos por defecto) y clasifica en 4 niveles."
    )
    parser.add_argument(
        "--targets",
        nargs="*",
        default=None,
        help="Lista de archivos (relativos a la raíz). Si se omite, usa los 17 por defecto.",
    )
    parser.add_argument("--all", action="store_true", help="Escanea todo el repo (exts: .py/.html/.js/.jinja/.ts).")
    parser.add_argument(
        "--paths",
        nargs="*",
        default=None,
        help="(Solo con --all) limita el escaneo a estas rutas (directorios/archivos).",
    )
    parser.add_argument("--relaxed", action="store_true", help="Reduce falsos positivos (NO recomendado).")
    parser.add_argument("--context", type=int, default=0, choices=[0, 1, 2], help="Líneas de contexto a imprimir.")
    parser.add_argument("--txt-out", default="vulnerabilities_validation_report.txt", help="Ruta del reporte TXT.")
    parser.add_argument("--json-out", default=None, help="Ruta del reporte JSON (opcional).")
    parser.add_argument("--priority-map", default=None, help="JSON con override de prioridad por regla (ej: {\"CWE-117\":\"ALTA\"}).")

    # parse_known_args evita que falle si el entorno mete flags extras (p. ej. Jupyter)
    args, _unknown = parser.parse_known_args(argv)
    apply_priority_overrides(args.priority_map)

    root = Path.cwd()

    if args.all:
        files = list(iter_repo_files(root, only_paths=args.paths))
        missing: List[str] = []
    else:
        targets = args.targets if args.targets is not None else DEFAULT_TARGET_FILES
        files, missing = resolve_targets(root, targets)
        if not files:
            findings = [Finding(
                severity=RULES["MISSING"].severity,
                rule_id=RULES["MISSING"].rule_id,
                rule_title=RULES["MISSING"].title,
                path="(root)",
                line=1,
                detail="No se encontró ninguno de los archivos objetivo. Revisa que ejecutes el script desde la raíz del proyecto.",
                snippet=""
            )]
            print_console_report(findings, missing, context=args.context)
            Path(args.txt_out).write_text(render_txt_report(root, findings, missing), encoding="utf-8")
            if args.json_out:
                Path(args.json_out).write_text(
                    json.dumps({"root": str(root), "findings": [asdict(f) for f in findings]}, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            return 2

    findings = run_all(root=root, files=files, relaxed=args.relaxed, context=args.context)

    print_console_report(findings, missing, context=args.context)

    try:
        Path(args.txt_out).write_text(render_txt_report(root, findings, missing), encoding="utf-8")
        print(f"\n[INFO] Reporte TXT: {args.txt_out}")
    except Exception as ex:
        eprint(f"[ERROR] No se pudo escribir el TXT: {ex}")
        return 3

    if args.json_out:
        try:
            payload = {"root": str(root), "findings": [asdict(f) for f in findings], "missing_targets": missing}
            Path(args.json_out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[INFO] Reporte JSON: {args.json_out}")
        except Exception as ex:
            eprint(f"[ERROR] No se pudo escribir el JSON: {ex}")
            return 3

    return 2 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
