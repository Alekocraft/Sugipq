# blueprints/confirmacion_asignaciones.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.confirmacion_asignaciones_model import ConfirmacionAsignacionesModel
from utils.helpers import sanitizar_email, sanitizar_username, sanitizar_ip, sanitizar_identificacion
from utils.auth import login_required
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)

confirmacion_bp = Blueprint(
    'confirmacion',
    __name__,
    url_prefix='/confirmacion'
)

def validar_ldap(username, password):
    try:
        from utils.ldap_auth import ad_auth
        
        resultado = ad_auth.authenticate_user(username, password)
        
        if resultado:
            email = resultado.get('email', f"{username}@qualitascolombia.com.co")
            nombre = resultado.get('full_name', username)
            
            logger.info(f"✅ LDAP: Autenticación exitosa para {sanitizar_username(username)} ({sanitizar_email(email)})")
            return (True, email, nombre, None)
        else:
            logger.warning(f"❌ LDAP: Credenciales inválidas para {sanitizar_username(username)}")
            return (False, None, None, "Usuario o contraseña incorrectos")
            
    except ImportError as e:
        logger.error(f"❌ Módulo LDAP no disponible: {e}")
        return (False, None, None, "Sistema de autenticación no disponible")
    except Exception as e:
        logger.error(f"❌ Error en validación LDAP: {e}", exc_info=True)
        return (False, None, None, f"Error de autenticación: {str(e)}")

def validar_numero_identificacion(numero_identificacion):
    if not numero_identificacion or not numero_identificacion.strip():
        return (False, None, "El número de identificación es obligatorio")
    
    numero_limpio = numero_identificacion.strip()
    
    if not numero_limpio.isdigit():
        return (False, None, "El número de identificación debe contener solo números")
    
    if len(numero_limpio) < 6:
        return (False, None, "El número de identificación debe tener al menos 6 dígitos")
    
    if len(numero_limpio) > 20:
        return (False, None, "El número de identificación no puede tener más de 20 dígitos")
    
    return (True, numero_limpio, None)

@confirmacion_bp.route('/confirmar-asignacion/<token>', methods=['GET', 'POST'])
def confirmar_asignacion(token):
    try:
        validacion = ConfirmacionAsignacionesModel.validar_token(token)
        
        if not validacion:
            logger.warning(f"Token inválido o no encontrado: {token[:20]}...")
            return render_template(
                'confirmacion/error.html',
                mensaje='Token inválido o no encontrado',
                titulo='Error de Validación'
            ), 404
        
        if not validacion.get('es_valido'):
            if validacion.get('ya_confirmado'):
                return render_template(
                    'confirmacion/ya_confirmado.html',
                    mensaje=validacion.get('mensaje_error'),
                    titulo='Asignación Ya Confirmada',
                    asignacion=validacion
                )
            elif validacion.get('expirado'):
                return render_template(
                    'confirmacion/token_expirado.html',
                    mensaje=validacion.get('mensaje_error'),
                    titulo='Token Expirado'
                )
            else:
                return render_template(
                    'confirmacion/error.html',
                    mensaje=validacion.get('mensaje_error', 'Error desconocido'),
                    titulo='Error de Validación'
                )
        
        if request.method == 'GET':
            ldap_disponible = True
            try:
                from utils.ldap_auth import ad_auth
                if ad_auth is None or not hasattr(ad_auth, 'authenticate_user'):
                    ldap_disponible = False
                    logger.warning("ADAuth no está disponible o mal configurado")
            except ImportError:
                ldap_disponible = False
                logger.warning("Módulo ldap_auth no disponible")
            
            return render_template(
                'confirmacion/confirmar.html',
                token=token,
                asignacion=validacion,
                ldap_disponible=ldap_disponible
            )
        
        if request.method == 'POST':
            numero_identificacion = request.form.get('numero_identificacion', '').strip()
            es_valido, numero_limpio, error_cedula = validar_numero_identificacion(numero_identificacion)
            
            if not es_valido:
                logger.warning(f"❌ Número de identificación inválido: {error_cedula}")
                flash(error_cedula, 'error')
                return render_template(
                    'confirmacion/confirmar.html',
                    token=token,
                    asignacion=validacion,
                    ldap_disponible=True,
                    error=error_cedula
                )
            
            logger.info(f"✅ Número de identificación validado: {sanitizar_identificacion(numero_limpio)}")
            
            sin_autenticar = request.form.get('sin_autenticar') == 'true'
            
            if not sin_autenticar:
                username = request.form.get('username', '').strip()
                password = request.form.get('password', '')
                
                if not username or not password:
                    flash('Debe ingresar usuario y contraseña', 'error')
                    return render_template(
                        'confirmacion/confirmar.html',
                        token=token,
                        asignacion=validacion,
                        ldap_disponible=True,
                        error='Debe ingresar usuario y contraseña'
                    )
                
                logger.info(f"🔐 Intentando validar LDAP para usuario: {sanitizar_username(username)}")
                
                exito, email_ldap, nombre_ldap, mensaje_error = validar_ldap(username, password)
                
                if not exito:
                    logger.warning(f"❌ Fallo autenticación LDAP para usuario: {sanitizar_username(username)}")
                    flash(f'Error de autenticación: {mensaje_error}', 'error')
                    return render_template(
                        'confirmacion/confirmar.html',
                        token=token,
                        asignacion=validacion,
                        ldap_disponible=True,
                        error=mensaje_error,
                        username_anterior=username
                    )
                
                logger.info(f"✅ LDAP validado: {sanitizar_username(username)} -> {sanitizar_email(email_ldap)}")
                
                email_asignado = validacion.get('usuario_email', '').lower()
                email_ldap_lower = (email_ldap or '').lower()
                
                logger.info(f"📧 Comparando emails: LDAP={sanitizar_email(email_ldap_lower)} vs Asignado={sanitizar_email(email_asignado)}")
                
                if email_ldap_lower != email_asignado:
                    # Log detallado para administradores (con sanitización)
                    logger.warning(f"❌ Usuario LDAP ({sanitizar_email(email_ldap)}) no coincide con asignado ({sanitizar_email(email_asignado)})")
                    
                    # Mensaje genérico para el usuario (sin detalles específicos)
                    flash('El usuario autenticado no coincide con el destinatario de la asignación', 'error')
                    return render_template(
                        'confirmacion/confirmar.html',
                        token=token,
                        asignacion=validacion,
                        ldap_disponible=True,
                        error='El usuario autenticado no coincide con el destinatario de la asignación',
                        username_anterior=username
                    )
                
                usuario_confirmacion = email_ldap
                nombre_confirmacion = nombre_ldap
                logger.info(f"✅ Usuario validado y coincidente: {sanitizar_username(username)} ({sanitizar_email(email_ldap)})")
            else:
                usuario_confirmacion = validacion.get('usuario_email', 'Usuario')
                nombre_confirmacion = validacion.get('usuario_nombre', 'Usuario')
                logger.warning(f"⚠️ Confirmación sin autenticación LDAP para: {sanitizar_email(usuario_confirmacion)}")
            
            direccion_ip = request.remote_addr
            user_agent = request.headers.get('User-Agent', '')
            
            logger.info(f"📝 Confirmando asignación - Usuario: {sanitizar_email(usuario_confirmacion)}, CC: {sanitizar_identificacion(numero_limpio)}, IP: {sanitizar_ip(direccion_ip)}")
            
            resultado = ConfirmacionAsignacionesModel.confirmar_asignacion(
                token=token,
                usuario_ad_username=usuario_confirmacion,
                numero_identificacion=numero_limpio,
                direccion_ip=direccion_ip,
                user_agent=user_agent
            )
            
            if resultado.get('success'):
                logger.info(f"✅ Asignación confirmada exitosamente: {resultado.get('asignacion_id')} - CC: {sanitizar_identificacion(numero_limpio)}")
                return render_template(
                    'confirmacion/confirmado_exitoso.html',
                    resultado=resultado,
                    titulo='Confirmación Exitosa',
                    mensaje='Su asignación ha sido confirmada correctamente.',
                    producto=resultado.get('producto_nombre'),
                    oficina=resultado.get('oficina_nombre'),
                    usuario=nombre_confirmacion,
                    fecha_confirmacion=datetime.now()
                )
            else:
                logger.error(f"❌ Error al confirmar asignación: {resultado.get('message')}")
                return render_template(
                    'confirmacion/error.html',
                    mensaje=resultado.get('message', 'Error al confirmar la asignación'),
                    titulo='Error al Confirmar'
                )
    
    except Exception as e:
        logger.error(f"❌ Error procesando confirmación: {e}", exc_info=True)
        return render_template(
            'confirmacion/error.html',
            mensaje=f'Error inesperado al procesar la confirmación: {str(e)}',
            titulo='Error del Sistema'
        ), 500

@confirmacion_bp.route('/mis-pendientes')
@login_required
def mis_pendientes():
    try:
        usuario_email = session.get('email')
        if not usuario_email:
            flash('No se pudo obtener tu información de usuario', 'error')
            return redirect(url_for('auth.login'))
        
        pendientes = ConfirmacionAsignacionesModel.obtener_confirmaciones_pendientes(
            usuario_email=usuario_email
        )
        
        logger.info(f"Obteniendo confirmaciones pendientes para: {sanitizar_email(usuario_email)}")
        
        return render_template(
            'confirmacion/mis_pendientes.html',
            confirmaciones=pendientes,
            pendientes=pendientes,
            total_pendientes=len(pendientes),
            titulo='Mis Confirmaciones Pendientes'
        )
    
    except Exception as e:
        logger.error(f"Error obteniendo confirmaciones pendientes: {e}", exc_info=True)
        flash('Error al cargar las confirmaciones pendientes', 'error')
        return redirect(url_for('dashboard'))

@confirmacion_bp.route('/estadisticas')
@login_required
def estadisticas():
    try:
        if not session.get('is_admin', False):
            flash('No tienes permisos para ver esta página', 'error')
            return redirect(url_for('dashboard'))
        
        admin_email = session.get('email', 'admin')
        logger.info(f"Accediendo a estadísticas como admin: {sanitizar_email(admin_email)}")
        
        stats = ConfirmacionAsignacionesModel.obtener_estadisticas_confirmaciones()
        
        return render_template(
            'confirmacion/estadisticas.html',
            estadisticas=stats,
            titulo='Estadísticas de Confirmaciones'
        )
    
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}", exc_info=True)
        flash('Error al cargar las estadísticas', 'error')
        return redirect(url_for('dashboard'))

@confirmacion_bp.route('/limpiar-tokens', methods=['POST'])
@login_required
def limpiar_tokens():
    try:
        if not session.get('is_admin', False):
            flash('No tienes permisos para realizar esta acción', 'error')
            return redirect(url_for('dashboard'))
        
        admin_email = session.get('email', 'admin')
        logger.info(f"Iniciando limpieza de tokens por admin: {sanitizar_email(admin_email)}")
        
        eliminados = ConfirmacionAsignacionesModel.limpiar_tokens_expirados()
        
        flash(f'Se eliminaron {eliminados} tokens expirados', 'success')
        logger.info(f"Tokens expirados limpiados: {eliminados}")
        
        return redirect(url_for('confirmacion.estadisticas'))
    
    except Exception as e:
        logger.error(f"Error limpiando tokens: {e}", exc_info=True)
        flash('Error al limpiar tokens expirados', 'error')
        return redirect(url_for('confirmacion.estadisticas'))

@confirmacion_bp.errorhandler(404)
def not_found_error(error):
    logger.warning(f"Página no encontrada en confirmación: {request.url}")
    return render_template(
        'confirmacion/error.html',
        mensaje='La página solicitada no existe',
        titulo='Página No Encontrada'
    ), 404

@confirmacion_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Error interno en confirmación: {error}", exc_info=True)
    return render_template(
        'confirmacion/error.html',
        mensaje='Ocurrió un error interno en el servidor',
        titulo='Error del Servidor'
    ), 500