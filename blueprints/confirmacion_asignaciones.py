# blueprints/confirmacion_asignaciones.py
"""
Blueprint para gestionar confirmaciones de asignaciones mediante tokens temporales.
VERSIÓN CORREGIDA: Usa ADAuth correctamente de utils.ldap_auth
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.confirmacion_asignaciones_model import ConfirmacionAsignacionesModel
from utils.auth import login_required
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Crear blueprint
confirmacion_bp = Blueprint(
    'confirmacion',
    __name__,
    url_prefix='/confirmacion'
)


def validar_ldap(username, password):
    """
    Valida credenciales contra Active Directory usando ADAuth.
    Retorna: (éxito: bool, email: str, nombre: str, mensaje_error: str)
    """
    try:
        # Importar la instancia global de ADAuth
        from utils.ldap_auth import ad_auth
        
        # Autenticar usuario
        resultado = ad_auth.authenticate_user(username, password)
        
        if resultado:
            # Éxito - extraer datos del resultado
            email = resultado.get('email', f"{username}@qualitascolombia.com.co")
            nombre = resultado.get('full_name', username)
            
            logger.info(f"✅ LDAP: Autenticación exitosa para {username} ({email})")
            return (True, email, nombre, None)
        else:
            # Fallo de autenticación
            logger.warning(f"❌ LDAP: Credenciales inválidas para {username}")
            return (False, None, None, "Usuario o contraseña incorrectos")
            
    except ImportError as e:
        logger.error(f"❌ Módulo LDAP no disponible: {e}")
        return (False, None, None, "Sistema de autenticación no disponible")
    except Exception as e:
        logger.error(f"❌ Error en validación LDAP: {e}", exc_info=True)
        return (False, None, None, f"Error de autenticación: {str(e)}")


@confirmacion_bp.route('/confirmar-asignacion/<token>', methods=['GET', 'POST'])
def confirmar_asignacion(token):
    """
    Procesa la confirmación de una asignación mediante token.
    GET: Muestra el formulario de confirmación con login LDAP
    POST: Valida LDAP y procesa la confirmación
    """
    try:
        # Validar el token
        validacion = ConfirmacionAsignacionesModel.validar_token(token)
        
        if not validacion:
            logger.warning(f"Token inválido o no encontrado: {token[:20]}...")
            return render_template(
                'confirmacion/error.html',
                mensaje='Token inválido o no encontrado',
                titulo='Error de Validación'
            ), 404
        
        if not validacion.get('es_valido'):
            # Token no válido (expirado o ya usado)
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
        
        # Si es GET, mostrar formulario de confirmación
        if request.method == 'GET':
            # Verificar si LDAP está disponible
            ldap_disponible = True
            try:
                from utils.ldap_auth import ad_auth
                # Probar que ADAuth esté instanciado correctamente
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
        
        # Si es POST, procesar la confirmación
        if request.method == 'POST':
            # Verificar si se usa autenticación LDAP
            sin_autenticar = request.form.get('sin_autenticar') == 'true'
            
            if not sin_autenticar:
                # VALIDAR CREDENCIALES LDAP
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
                
                logger.info(f"🔐 Intentando validar LDAP para usuario: {username}")
                
                # Validar contra LDAP
                exito, email_ldap, nombre_ldap, mensaje_error = validar_ldap(username, password)
                
                if not exito:
                    logger.warning(f"❌ Falló autenticación LDAP para usuario: {username}")
                    flash(f'Error de autenticación: {mensaje_error}', 'error')
                    return render_template(
                        'confirmacion/confirmar.html',
                        token=token,
                        asignacion=validacion,
                        ldap_disponible=True,
                        error=mensaje_error,
                        username_anterior=username  # Mantener el usuario ingresado
                    )
                
                logger.info(f"✅ LDAP validado: {username} -> {email_ldap}")
                
                # Verificar que el usuario LDAP coincida con el asignado
                email_asignado = validacion.get('usuario_email', '').lower()
                email_ldap_lower = (email_ldap or '').lower()
                
                if email_ldap_lower != email_asignado:
                    logger.warning(f"❌ Usuario LDAP ({email_ldap}) no coincide con asignado ({email_asignado})")
                    flash('El usuario autenticado no coincide con el destinatario de la asignación', 'error')
                    return render_template(
                        'confirmacion/confirmar.html',
                        token=token,
                        asignacion=validacion,
                        ldap_disponible=True,
                        error=f'El usuario autenticado ({email_ldap}) no coincide con el destinatario ({email_asignado})',
                        username_anterior=username
                    )
                
                usuario_confirmacion = email_ldap
                nombre_confirmacion = nombre_ldap
                logger.info(f"✅ Usuario validado y coincidente: {username} ({email_ldap})")
            else:
                # Sin autenticación LDAP (fallback)
                usuario_confirmacion = validacion.get('usuario_email', 'Usuario')
                nombre_confirmacion = validacion.get('usuario_nombre', 'Usuario')
                logger.warning(f"⚠️ Confirmación sin autenticación LDAP para: {usuario_confirmacion}")
            
            # Obtener datos adicionales
            direccion_ip = request.remote_addr
            user_agent = request.headers.get('User-Agent', '')
            
            logger.info(f"📝 Confirmando asignación - Usuario: {usuario_confirmacion}, IP: {direccion_ip}")
            
            # Confirmar la asignación
            resultado = ConfirmacionAsignacionesModel.confirmar_asignacion(
                token=token,
                usuario_ad_username=usuario_confirmacion,
                direccion_ip=direccion_ip,
                user_agent=user_agent
            )
            
            if resultado.get('success'):
                logger.info(f"✅ Asignación confirmada exitosamente: {resultado.get('asignacion_id')}")
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
    """
    Muestra las confirmaciones pendientes del usuario autenticado.
    Requiere login.
    """
    try:
        # Obtener email del usuario de la sesión
        usuario_email = session.get('email')
        if not usuario_email:
            flash('No se pudo obtener tu información de usuario', 'error')
            return redirect(url_for('auth.login'))
        
        # Obtener confirmaciones pendientes
        pendientes = ConfirmacionAsignacionesModel.obtener_confirmaciones_pendientes(
            usuario_email=usuario_email
        )
        
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
    """
    Muestra estadísticas generales de confirmaciones.
    Solo para administradores.
    """
    try:
        # Verificar si el usuario es administrador
        if not session.get('is_admin', False):
            flash('No tienes permisos para ver esta página', 'error')
            return redirect(url_for('dashboard'))
        
        # Obtener estadísticas
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
    """
    Limpia tokens expirados de la base de datos.
    Solo para administradores.
    """
    try:
        # Verificar si el usuario es administrador
        if not session.get('is_admin', False):
            flash('No tienes permisos para realizar esta acción', 'error')
            return redirect(url_for('dashboard'))
        
        # Limpiar tokens
        eliminados = ConfirmacionAsignacionesModel.limpiar_tokens_expirados()
        
        flash(f'Se eliminaron {eliminados} tokens expirados', 'success')
        logger.info(f"Tokens expirados limpiados: {eliminados}")
        
        return redirect(url_for('confirmacion.estadisticas'))
    
    except Exception as e:
        logger.error(f"Error limpiando tokens: {e}", exc_info=True)
        flash('Error al limpiar tokens expirados', 'error')
        return redirect(url_for('confirmacion.estadisticas'))


# Manejador de errores específico para este blueprint
@confirmacion_bp.errorhandler(404)
def not_found_error(error):
    """Maneja errores 404 específicos del blueprint de confirmaciones."""
    logger.warning(f"Página no encontrada en confirmación: {request.url}")
    return render_template(
        'confirmacion/error.html',
        mensaje='La página solicitada no existe',
        titulo='Página No Encontrada'
    ), 404


@confirmacion_bp.errorhandler(500)
def internal_error(error):
    """Maneja errores 500 específicos del blueprint de confirmaciones."""
    logger.error(f"Error interno en confirmación: {error}", exc_info=True)
    return render_template(
        'confirmacion/error.html',
        mensaje='Ocurrió un error interno en el servidor',
        titulo='Error del Servidor'
    ), 500