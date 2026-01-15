#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTING AUTOMÁTICO COMPLETO - DÍA 8 (VERSIÓN CORREGIDA)
Verifica todas las correcciones de seguridad de los Días 1-7
Versión 2.1 - Corregida para reconocer configuraciones dinámicas
"""

import os
import sys
import re
import subprocess
import importlib.util
from pathlib import Path
from datetime import datetime

# Colores para terminal
class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Color.CYAN}{'='*70}{Color.END}")
    print(f"{Color.YELLOW}{Color.BOLD}{text}{Color.END}")
    print(f"{Color.CYAN}{'='*70}{Color.END}\n")

def print_success(text):
    print(f"{Color.GREEN}✅ {text}{Color.END}")

def print_error(text):
    print(f"{Color.RED}❌ {text}{Color.END}")

def print_warning(text):
    print(f"{Color.YELLOW}⚠️  {text}{Color.END}")

def print_info(text):
    print(f"{Color.CYAN}ℹ️  {text}{Color.END}")

def check_file_exists(filepath):
    """Verifica si un archivo existe y es legible"""
    if not os.path.exists(filepath):
        return False
    if not os.access(filepath, os.R_OK):
        return False
    return True

def read_file_safely(filepath):
    """Lee un archivo de forma segura manejando diferentes encodings"""
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception as e:
            print_warning(f"Error leyendo {filepath}: {e}")
            return None
    
    # Si todo falla, leer como binario y decodificar ignorando errores
    try:
        with open(filepath, 'rb') as f:
            return f.read().decode('utf-8', errors='ignore')
    except:
        return None

# ============================================================================
# DÍAS 1-4: INFORMACIÓN SENSIBLE EN LOGS
# ============================================================================

def test_sanitizacion_logs():
    """Verifica que los logs no expongan información sensible"""
    print_header("TEST 1: Sanitización de Logs (Días 1-4)")
    
    archivos_a_verificar = {
        'blueprints/confirmacion_asignaciones.py': ['email', 'username', 'usuario'],
        'services/notification_service.py': ['email'],
        'services/auth_service.py': ['username', 'email'],
        'models/usuarios_model.py': ['contraseña', 'password', 'hash'],
        'utils/ldap_auth.py': ['username', 'password'],
        'utils/permissions.py': ['username']
    }
    
    total_tests = 0
    tests_ok = 0
    problemas = []
    
    for archivo, campos_sensibles in archivos_a_verificar.items():
        if not check_file_exists(archivo):
            continue
        
        contenido = read_file_safely(archivo)
        if not contenido:
            continue
        
        # Buscar patrones peligrosos en logs
        for campo in campos_sensibles:
            total_tests += 1
            
            # Patrones que indican exposición directa
            patrones_peligrosos = [
                rf'logger\.(info|debug|warning|error)\([^)]*\b{campo}\b[^)]*\)',
                rf'print\([^)]*\b{campo}\b[^)]*\)'
            ]
            
            expone_datos = False
            for patron in patrones_peligrosos:
                matches = list(re.finditer(patron, contenido, re.IGNORECASE))
                for match in matches:
                    # Verificar contexto
                    line_start = max(0, match.start() - 150)
                    line_end = min(len(contenido), match.end() + 150)
                    context = contenido[line_start:line_end]
                    
                    # Verificar si está usando función de sanitización
                    sanitizacion_patterns = [
                        rf'sanitizar[_-]?{campo}',
                        rf'sanitizar[_-]?(email|username|usuario)',
                        r'sanitizar_\w+',
                        r'\[.*protegido.*\]',
                        r'\*{3,}',
                        r'<oculto>'
                    ]
                    
                    tiene_sanitizacion = any(re.search(p, context, re.IGNORECASE) for p in sanitizacion_patterns)
                    
                    if not tiene_sanitizacion:
                        expone_datos = True
                        line_number = contenido[:match.start()].count('\n') + 1
                        problemas.append(f"{archivo}:{line_number} - Posible exposición de '{campo}'")
                        break
                
                if expone_datos:
                    break
            
            if not expone_datos:
                tests_ok += 1
    
    if problemas:
        for problema in problemas[:5]:
            print_warning(problema)
        if len(problemas) > 5:
            print_info(f"... y {len(problemas) - 5} problemas más")
    
    porcentaje = (tests_ok / total_tests * 100) if total_tests > 0 else 0
    print_info(f"Tests: {tests_ok}/{total_tests} correctos ({porcentaje:.1f}%)")
    
    return {
        'total': total_tests,
        'correctos': tests_ok,
        'errores': total_tests - tests_ok
    }

# ============================================================================
# DÍAS 1-4: EJECUCIÓN DESPUÉS DE REDIRECT
# ============================================================================

def test_redirects_seguros():
    """Verifica que todos los redirects tengan return"""
    print_header("TEST 2: Redirects Seguros (Días 1-4)")
    
    archivos_a_verificar = [
        'blueprints/usuarios.py',
        'blueprints/prestamos.py',
        'blueprints/reportes.py',
        'blueprints/inventario_corporativo.py',
        'blueprints/auth.py',
        'blueprints/confirmacion_asignaciones.py'
    ]
    
    total_tests = 0
    tests_ok = 0
    problemas = []
    
    for archivo in archivos_a_verificar:
        if not check_file_exists(archivo):
            continue
        
        contenido = read_file_safely(archivo)
        if not contenido:
            continue
        
        lineas = contenido.split('\n')
        
        for i, linea in enumerate(lineas, 1):
            if re.search(r'redirect\(', linea) and not linea.strip().startswith('#'):
                total_tests += 1
                
                # Verificar si tiene return
                if re.search(r'return\s+redirect\(', linea):
                    tests_ok += 1
                else:
                    problemas.append(f"{archivo}:{i} - redirect() sin return")
    
    if problemas:
        for problema in problemas[:5]:
            print_warning(problema)
        if len(problemas) > 5:
            print_info(f"... y {len(problemas) - 5} problemas más")
    
    porcentaje = (tests_ok / total_tests * 100) if total_tests > 0 else 0
    print_info(f"Tests: {tests_ok}/{total_tests} redirects seguros ({porcentaje:.1f}%)")
    
    return {
        'total': total_tests,
        'correctos': tests_ok,
        'errores': total_tests - tests_ok
    }

# ============================================================================
# DÍA 5: VARIABLES DE ENTORNO
# ============================================================================

def test_variables_entorno():
    """Verifica uso de variables de entorno"""
    print_header("TEST 3: Variables de Entorno (Día 5)")
    
    total_tests = 0
    tests_ok = 0
    
    # Verificar .env existe
    if not os.path.exists('.env'):
        print_error(".env no encontrado")
        return {'total': 1, 'correctos': 0, 'errores': 1}
    
    env_content = read_file_safely('.env')
    if not env_content:
        print_error("No se pudo leer .env")
        return {'total': 1, 'correctos': 0, 'errores': 1}
    
    # Verificar variables críticas
    variables_requeridas = [
        'LDAP_SERVER', 'SMTP_SERVER', 'SECRET_KEY',
        'DATABASE_URL', 'FLASK_ENV'
    ]
    
    for var in variables_requeridas:
        total_tests += 1
        if re.search(fr'^{var}\s*=', env_content, re.MULTILINE | re.IGNORECASE):
            tests_ok += 1
            print_success(f"{var} configurado en .env")
    
    porcentaje = (tests_ok / total_tests * 100) if total_tests > 0 else 0
    print_info(f"Tests: {tests_ok}/{total_tests} correctos ({porcentaje:.1f}%)")
    
    return {
        'total': total_tests,
        'correctos': tests_ok,
        'errores': total_tests - tests_ok
    }

# ============================================================================
# DÍA 5: SESIONES SEGURAS (CORREGIDO)
# ============================================================================

def test_session_cookie_secure():
    """Verifica configuración de sesiones seguras (con soporte para config dinámica)"""
    print_header("TEST 4: Configuración de Sesiones Seguras (Día 5)")
    
    archivos_a_verificar = ['config/config.py', 'blueprints/auth.py']
    
    total_tests = 0
    tests_ok = 0
    config_encontrada = []
    
    # Configuraciones a verificar (con soporte para valores dinámicos)
    configuraciones = {
        'SESSION_COOKIE_SECURE': {
            'valores_aceptados': ['True', '_is_production', 'is_production'],
            'es_critico': True,
            'permite_dinamico': True
        },
        'SESSION_COOKIE_HTTPONLY': {
            'valores_aceptados': ['True'],
            'es_critico': True,
            'permite_dinamico': False
        },
        'SESSION_COOKIE_SAMESITE': {
            'valores_aceptados': ['"Lax"', '"Strict"', "'Lax'", "'Strict'"],
            'es_critico': True,
            'permite_dinamico': False
        },
        'PERMANENT_SESSION_LIFETIME': {
            'valores_aceptados': ['timedelta'],
            'es_critico': False,
            'permite_dinamico': False
        },
        'REMEMBER_COOKIE_SECURE': {
            'valores_aceptados': ['True', '_is_production', 'is_production'],
            'es_critico': False,
            'permite_dinamico': True
        },
        'REMEMBER_COOKIE_HTTPONLY': {
            'valores_aceptados': ['True'],
            'es_critico': False,
            'permite_dinamico': False
        }
    }
    
    for archivo in archivos_a_verificar:
        if not check_file_exists(archivo):
            continue
        
        contenido = read_file_safely(archivo)
        if not contenido:
            continue
        
        for config_name, config_info in configuraciones.items():
            total_tests += 1
            
            # Buscar configuración
            patron = rf'{config_name}\s*=\s*(.+?)(?:\n|$|;)'
            match = re.search(patron, contenido, re.MULTILINE)
            
            if match:
                valor = match.group(1).strip()
                
                # Verificar si es un valor aceptado
                valor_valido = False
                
                # Si permite configuración dinámica, verificar patrones especiales
                if config_info['permite_dinamico']:
                    patrones_dinamicos = [
                        r'_is_production',
                        r'is_production',
                        r'os\.environ\.get.*production',
                        r'getenv.*production'
                    ]
                    
                    if any(re.search(p, valor, re.IGNORECASE) for p in patrones_dinamicos):
                        valor_valido = True
                        if config_name not in config_encontrada:
                            config_encontrada.append(config_name)
                            print_success(f"{config_name} = {valor[:50]}... (dinámico ✅)")
                
                # Verificar valores estáticos
                if not valor_valido:
                    for valor_aceptado in config_info['valores_aceptados']:
                        if valor_aceptado in valor:
                            valor_valido = True
                            if config_name not in config_encontrada:
                                config_encontrada.append(config_name)
                                print_success(f"{config_name} = {valor}")
                            break
                
                if valor_valido:
                    tests_ok += 1
                else:
                    if config_info['es_critico']:
                        print_warning(f"{archivo}: {config_name} = {valor} (revisar)")
            else:
                if config_info['es_critico']:
                    print_warning(f"{config_name} no encontrado en {archivo}")
    
    porcentaje = (tests_ok / total_tests * 100) if total_tests > 0 else 0
    print_info(f"Tests: {tests_ok}/{total_tests} correctos ({porcentaje:.1f}%)")
    
    if porcentaje >= 70:
        print_success("Configuración de sesiones APROBADA (incluye config dinámica)")
    
    return {
        'total': total_tests,
        'correctos': tests_ok,
        'errores': total_tests - tests_ok
    }

# ============================================================================
# DÍA 6: SMTP SSL
# ============================================================================

def test_smtp_ssl():
    """Verifica configuración segura de SMTP"""
    print_header("TEST 5: Configuración SMTP Segura (Día 6)")
    
    archivo = 'services/notification_service.py'
    
    total_tests = 0
    tests_ok = 0
    
    if not check_file_exists(archivo):
        return {'total': 1, 'correctos': 0, 'errores': 1}
    
    contenido = read_file_safely(archivo)
    if not contenido:
        return {'total': 1, 'correctos': 0, 'errores': 1}
    
    # Verificar SMTP_SSL
    total_tests += 1
    if 'SMTP_SSL(' in contenido:
        tests_ok += 1
        print_success("Usa SMTP_SSL")
    
    # Verificar puerto seguro en .env
    total_tests += 1
    if os.path.exists('.env'):
        env_content = read_file_safely('.env')
        if env_content and 'SMTP_PORT=465' in env_content:
            tests_ok += 1
            print_success("Puerto SMTP seguro: 465")
    
    # Verificar manejo de excepciones
    total_tests += 1
    if 'except' in contenido and 'smtp' in contenido.lower():
        tests_ok += 1
        print_success("Manejo de excepciones implementado")
    
    porcentaje = (tests_ok / total_tests * 100) if total_tests > 0 else 0
    print_info(f"Tests: {tests_ok}/{total_tests} correctos ({porcentaje:.1f}%)")
    
    return {
        'total': total_tests,
        'correctos': tests_ok,
        'errores': total_tests - tests_ok
    }

# ============================================================================
# DÍA 6: HTTPS (CORREGIDO)
# ============================================================================

def test_https_config():
    """Verifica configuración HTTPS"""
    print_header("TEST 6: Configuración HTTPS (Día 6)")
    
    total_tests = 0
    tests_ok = 0
    
    # Verificar pyopenssl
    total_tests += 1
    try:
        import OpenSSL
        tests_ok += 1
        print_success(f"pyopenssl instalado: {OpenSSL.__version__}")
    except ImportError:
        print_warning("pyopenssl no instalado")
    
    # Verificar ssl_context en app.py
    total_tests += 1
    if check_file_exists('app.py'):
        contenido = read_file_safely('app.py')
        if contenido and 'ssl_context' in contenido:
            tests_ok += 1
            print_success("ssl_context configurado en app.py")
    
    porcentaje = (tests_ok / total_tests * 100) if total_tests > 0 else 0
    print_info(f"Tests: {tests_ok}/{total_tests} correctos ({porcentaje:.1f}%)")
    
    return {
        'total': total_tests,
        'correctos': tests_ok,
        'errores': total_tests - tests_ok
    }

# ============================================================================
# DÍA 7: FORMULARIOS SEGUROS (CORREGIDO)
# ============================================================================

def test_formularios_seguros():
    """Verifica CSRF tokens y autocomplete en formularios"""
    print_header("TEST 7: Formularios Seguros (Día 7)")
    
    archivos_html = [
        'templates/auth/login.html',
        'templates/auth/test_ldap.html',
        'templates/usuarios/gestionar.html',
        'templates/confirmacion/confirmar.html',
        'templates/usuarios/crear.html',
        'templates/usuarios/editar.html'
    ]
    
    total_tests = 0
    tests_ok = 0
    problemas = []
    
    for archivo in archivos_html:
        if not check_file_exists(archivo):
            continue
        
        contenido = read_file_safely(archivo)
        if not contenido:
            continue
        
        # Buscar formularios con method POST
        formularios = re.findall(r'<form[^>]*>.*?</form>', contenido, re.DOTALL | re.IGNORECASE)
        
        for form_html in formularios:
            # Solo verificar formularios POST
            if 'method' not in form_html.lower() or 'post' not in form_html.lower():
                continue
            
            total_tests += 1
            
            # Verificar CSRF token (varias formas válidas)
            patrones_csrf = [
                r'csrf_token\(\)',
                r'csrf_token\s*}}',
                r'name=["\']csrf_token["\']',
                r'{{ form\.csrf_token }}'
            ]
            
            tiene_csrf = any(re.search(p, form_html, re.IGNORECASE) for p in patrones_csrf)
            
            if tiene_csrf:
                tests_ok += 1
            else:
                problemas.append(f"{archivo}: Formulario sin CSRF token")
    
    if problemas:
        for problema in problemas[:5]:
            print_warning(problema)
        if len(problemas) > 5:
            print_info(f"... y {len(problemas) - 5} problemas más")
    
    porcentaje = (tests_ok / total_tests * 100) if total_tests > 0 else 0
    print_info(f"Tests: {tests_ok}/{total_tests} correctos ({porcentaje:.1f}%)")
    
    return {
        'total': total_tests,
        'correctos': tests_ok,
        'errores': total_tests - tests_ok
    }

# ============================================================================
# DÍA 7: ENLACES EXTERNOS (CORREGIDO)
# ============================================================================

def test_enlaces_externos():
    """Verifica protección en enlaces externos"""
    print_header("TEST 8: Enlaces Externos Seguros (Día 7)")
    
    templates_dir = 'templates'
    archivos_html = []
    
    if os.path.exists(templates_dir):
        for root, dirs, files in os.walk(templates_dir):
            for file in files:
                if file.endswith('.html'):
                    archivos_html.append(os.path.join(root, file))
    
    total_tests = 0
    tests_ok = 0
    problemas = []
    
    for archivo in archivos_html:
        contenido = read_file_safely(archivo)
        if not contenido:
            continue
        
        # Buscar enlaces con target="_blank"
        patron_enlaces = r'<a\s+([^>]*target=["\']_blank["\'][^>]*)>'
        enlaces = re.finditer(patron_enlaces, contenido, re.IGNORECASE)
        
        for match in enlaces:
            total_tests += 1
            atributos = match.group(1)
            
            # Verificar rel="noopener noreferrer"
            if 'rel=' in atributos:
                rel_match = re.search(r'rel=["\']([^"\']+)["\']', atributos, re.IGNORECASE)
                if rel_match:
                    rel_value = rel_match.group(1).lower()
                    if 'noopener' in rel_value and 'noreferrer' in rel_value:
                        tests_ok += 1
                    else:
                        problemas.append(f"{archivo}: target='_blank' con rel incompleto")
                else:
                    problemas.append(f"{archivo}: target='_blank' sin rel")
            else:
                problemas.append(f"{archivo}: target='_blank' sin rel")
    
    if problemas:
        for problema in problemas[:5]:
            print_warning(problema)
        if len(problemas) > 5:
            print_info(f"... y {len(problemas) - 5} problemas más")
    
    porcentaje = (tests_ok / total_tests * 100) if total_tests > 0 else 0
    print_info(f"Tests: {tests_ok}/{total_tests} correctos ({porcentaje:.1f}%)")
    print_info(f"Archivos HTML analizados: {len(archivos_html)}")
    
    return {
        'total': total_tests if total_tests > 0 else 1,
        'correctos': tests_ok,
        'errores': (total_tests - tests_ok) if total_tests > 0 else 0
    }

# ============================================================================
# REPORTE FINAL
# ============================================================================

def generar_reporte_final(resultados):
    """Genera reporte final consolidado"""
    print_header("REPORTE FINAL - DÍA 8")
    
    total_tests = sum(r['total'] for r in resultados.values())
    total_correctos = sum(r['correctos'] for r in resultados.values())
    total_errores = sum(r['errores'] for r in resultados.values())
    
    porcentaje = (total_correctos / total_tests * 100) if total_tests > 0 else 0
    
    print(f"{Color.CYAN}{Color.BOLD}RESUMEN DETALLADO:{Color.END}\n")
    
    categorias = {
        'sanitizacion_logs': '1. Sanitización de Logs',
        'redirects': '2. Redirects Seguros',
        'variables_entorno': '3. Variables de Entorno',
        'session_cookie': '4. Sesiones Seguras',
        'smtp_ssl': '5. SMTP SSL/TLS',
        'https': '6. Configuración HTTPS',
        'formularios': '7. Formularios CSRF',
        'enlaces_externos': '8. Enlaces Externos'
    }
    
    print(f"{Color.WHITE}{'No.':<3} {'CATEGORÍA':<30} {'RESULTADO':<15} {'PORCENTAJE':<10}{Color.END}")
    print(f"{Color.CYAN}{'-'*60}{Color.END}")
    
    for key, nombre in categorias.items():
        if key in resultados:
            r = resultados[key]
            porcentaje_cat = (r['correctos'] / r['total'] * 100) if r['total'] > 0 else 0
            
            if porcentaje_cat >= 90:
                color = Color.GREEN
                simbolo = "✅"
            elif porcentaje_cat >= 70:
                color = Color.YELLOW
                simbolo = "⚠️ "
            else:
                color = Color.RED
                simbolo = "❌"
            
            resultado_str = f"{r['correctos']}/{r['total']}"
            print(f"{simbolo:<2} {nombre:<30} {resultado_str:<15} {color}{porcentaje_cat:>6.1f}%{Color.END}")
    
    print(f"\n{Color.CYAN}{'='*60}{Color.END}")
    print(f"{Color.BOLD}RESUMEN GENERAL:{Color.END}\n")
    
    print(f"{Color.WHITE}Tests totales ejecutados:     {total_tests:>5}{Color.END}")
    print(f"{Color.GREEN}Tests exitosos:              {total_correctos:>5}{Color.END}")
    print(f"{Color.RED}Tests fallidos:              {total_errores:>5}{Color.END}")
    print(f"{Color.CYAN}Porcentaje de éxito:         {porcentaje:>6.1f}%{Color.END}")
    
    # Barra de progreso
    barra_length = 50
    barra_llena = int(barra_length * porcentaje / 100)
    barra = '█' * barra_llena + '░' * (barra_length - barra_llena)
    
    print(f"\n{Color.WHITE}Progreso:{Color.END}")
    print(f"[{barra}] {porcentaje:.1f}%\n")
    
    # Evaluación
    if porcentaje >= 95:
        print_success("🏆 EXCELENTE - Sistema completamente seguro")
        estado = "APROBADO"
        recomendacion = "✅ Sistema listo para producción"
    elif porcentaje >= 85:
        print_success("👍 MUY BUENO - Sistema seguro")
        estado = "APROBADO"
        recomendacion = "✅ Sistema listo para producción con mejoras menores"
    elif porcentaje >= 70:
        print_warning("👌 ACEPTABLE - Mejoras recomendadas")
        estado = "APROBADO CON OBSERVACIONES"
        recomendacion = "⚠️ Aplicar correcciones antes de producción"
    else:
        print_error("❌ INSUFICIENTE - Correcciones necesarias")
        estado = "NO APROBADO"
        recomendacion = "🚫 No usar en producción"
    
    print(f"\n{Color.CYAN}Recomendación: {recomendacion}{Color.END}")
    
    # Certificado
    print(f"\n{Color.CYAN}{'='*70}{Color.END}")
    print(f"{Color.BOLD}CERTIFICACIÓN DE SEGURIDAD - SUGIPQ-V1{Color.END}")
    print(f"{Color.CYAN}{'='*70}{Color.END}")
    
    print(f"{Color.WHITE}{'Proyecto':<20}: {Color.CYAN}SUGIPQ-V1{Color.END}")
    print(f"{Color.WHITE}{'Fecha':<20}: {Color.CYAN}{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}{Color.END}")
    print(f"{Color.WHITE}{'Tests ejecutados':<20}: {Color.CYAN}{total_tests}{Color.END}")
    print(f"{Color.WHITE}{'Porcentaje éxito':<20}: {Color.CYAN}{porcentaje:.1f}%{Color.END}")
    print(f"{Color.WHITE}{'Estado':<20}: {Color.CYAN}{estado}{Color.END}")
    print(f"{Color.WHITE}{'Versión script':<20}: {Color.CYAN}2.1 (Corregida){Color.END}")
    
    print(f"{Color.CYAN}{'='*70}{Color.END}\n")
    
    # Guardar reporte
    try:
        with open('security_audit_report.txt', 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("REPORTE DE AUDITORÍA DE SEGURIDAD - SUGIPQ-V1\n")
            f.write("="*70 + "\n\n")
            f.write(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Tests totales: {total_tests}\n")
            f.write(f"Tests exitosos: {total_correctos}\n")
            f.write(f"Porcentaje: {porcentaje:.1f}%\n")
            f.write(f"Estado: {estado}\n\n")
            
            f.write("DETALLE POR CATEGORÍA:\n")
            f.write("-"*50 + "\n")
            for key, nombre in categorias.items():
                if key in resultados:
                    r = resultados[key]
                    porcentaje_cat = (r['correctos'] / r['total'] * 100) if r['total'] > 0 else 0
                    f.write(f"{nombre}: {r['correctos']}/{r['total']} ({porcentaje_cat:.1f}%)\n")
            
            f.write(f"\nRecomendación: {recomendacion}\n")
            f.write(f"\nNOTA: Este validador reconoce configuraciones dinámicas como válidas.\n")
        
        print_success(f"Reporte guardado en: {os.path.abspath('security_audit_report.txt')}")
    except Exception as e:
        print_warning(f"No se pudo guardar el reporte: {e}")
    
    return porcentaje >= 70

def main():
    """Función principal"""
    print_header("TESTING AUTOMÁTICO COMPLETO - DÍA 8 (VERSIÓN CORREGIDA)")
    print(f"{Color.WHITE}Proyecto: {Color.CYAN}SUGIPQ-V1{Color.END}")
    print(f"{Color.WHITE}Fecha: {Color.CYAN}{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}{Color.END}")
    print(f"{Color.WHITE}Directorio: {Color.CYAN}{os.getcwd()}{Color.END}")
    print(f"{Color.WHITE}Python: {Color.CYAN}{sys.version.split()[0]}{Color.END}")
    print(f"{Color.WHITE}Versión: {Color.CYAN}2.1 (Reconoce config dinámica){Color.END}")
    
    # Verificar dependencias
    print(f"\n{Color.WHITE}Verificando dependencias...{Color.END}")
    dependencias = ['flask', 'flask_wtf']
    
    for dep in dependencias:
        try:
            spec = importlib.util.find_spec(dep.replace('-', '_'))
            if spec:
                print_success(f"{dep}: instalado")
            else:
                print_warning(f"{dep}: no encontrado")
        except:
            print_warning(f"{dep}: error al verificar")
    
    # Ejecutar tests
    resultados = {}
    tests_funciones = [
        ('sanitizacion_logs', test_sanitizacion_logs),
        ('redirects', test_redirects_seguros),
        ('variables_entorno', test_variables_entorno),
        ('session_cookie', test_session_cookie_secure),
        ('smtp_ssl', test_smtp_ssl),
        ('https', test_https_config),
        ('formularios', test_formularios_seguros),
        ('enlaces_externos', test_enlaces_externos)
    ]
    
    print_header("EJECUTANDO TODOS LOS TESTS DE SEGURIDAD")
    
    for key, test_func in tests_funciones:
        try:
            resultados[key] = test_func()
        except Exception as e:
            print_error(f"Error en test {key}: {e}")
            resultados[key] = {'total': 1, 'correctos': 0, 'errores': 1}
    
    # Generar reporte
    aprobado = generar_reporte_final(resultados)
    
    return 0 if aprobado else 1

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Color.YELLOW}Testing cancelado por el usuario{Color.END}\n")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Color.RED}ERROR INESPERADO: {e}{Color.END}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)