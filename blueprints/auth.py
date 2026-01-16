# -*- coding: utf-8 -*-
"""
Blueprint de Autenticación
Combina funciones de utilidad y rutas de autenticación
"""
import logging
from flask import Blueprint, session, flash, redirect, url_for, request, render_template
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================================================
# CREAR BLUEPRINT
# ============================================================================
auth_bp = Blueprint('auth', __name__)

# ============================================================================
# FUNCIONES DE UTILIDAD (DECORADORES)
# ============================================================================

def require_login():
    """
    Verifica si el usuario está autenticado en el sistema
    
    Returns:
        bool: True si el usuario tiene sesión activa
    """
    is_authenticated = 'user_id' in session or 'usuario_id' in session
    logger.debug(f"Verificación de autenticación: {is_authenticated}")
    return is_authenticated


def has_role(*roles):
    """
    Verifica si el usuario tiene alguno de los roles especificados
    
    Args:
        *roles: Roles a verificar
        
    Returns:
        bool: True si el usuario tiene al menos uno de los roles
    """
    user_role = (session.get('rol', '') or '').strip().lower()
    target_roles = [r.lower() for r in roles]
    has_valid_role = user_role in target_roles
    
    logger.debug(f"Usuario rol '{user_role}' tiene alguno de {roles}: {has_valid_role}")
    return has_valid_role


def login_required(f):
    """
    Decorador para proteger rutas que requieren autenticación
    
    Args:
        f: Función a decorar
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not require_login():
            logger.warning(f"Intento de acceso no autenticado a {request.endpoint}")
            flash('Por favor inicie sesión para acceder a esta página.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        logger.debug(f"Acceso autorizado a {request.endpoint}")
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """
    Decorador para proteger rutas que requieren roles específicos
    
    Args:
        *roles: Roles requeridos para acceder
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not require_login():
                logger.warning(f"Intento de acceso no autenticado a ruta con roles {roles}")
                flash('Por favor inicie sesión.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            if not has_role(*roles):
                user_role = session.get('rol', 'No definido')
                logger.warning(f"Usuario rol '{user_role}' intentó acceder a ruta que requiere roles {roles}")
                flash('No tiene permisos para acceder a esta sección.', 'danger')
                return redirect(url_for('auth.dashboard'))
            
            logger.debug(f"Acceso autorizado con rol a {request.endpoint}")
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_current_user():
    """
    Obtiene la información del usuario actualmente autenticado
    
    Returns:
        dict: Información del usuario o None si no está autenticado
    """
    if not require_login():
        return None
    
    user_data = {
        'id': session.get('user_id') or session.get('usuario_id'),
        'nombre': session.get('user_name') or session.get('usuario_nombre'),
        'rol': session.get('rol'),
        'oficina_id': session.get('oficina_id'),
        'oficina_nombre': session.get('oficina_nombre')
    }
    
    logger.debug(f"Datos de usuario obtenidos: {user_data['nombre']} ({user_data['rol']})")
    return user_data


def can_access_module(module_name):
    """
    Verifica si el usuario puede acceder a un módulo específico según su rol
    
    Args:
        module_name: Nombre del módulo a verificar
        
    Returns:
        bool: True si el usuario tiene acceso al módulo
    """
    from config.config import Config
    user_role = (session.get('rol', '') or '').strip().lower()
    allowed_modules = Config.ROLES.get(user_role, [])
    
    has_access = module_name in allowed_modules
    logger.debug(f"Acceso a módulo '{module_name}' para rol '{user_role}': {has_access}")
    return has_access


# ============================================================================
# RUTAS DEL BLUEPRINT
# ============================================================================

@auth_bp.route('/')
def index():
    """Ruta raíz - redirige según estado de autenticación"""
    if 'usuario_id' in session:
        return redirect(url_for('auth.dashboard'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de inicio de sesión - VERSIÓN FINAL CORREGIDA"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        logger.info(f"🔐 Intento de login: {username}")
        
        if not username or not password:
            logger.warning(f"❌ Campos vacíos")
            flash('Por favor ingrese usuario y contraseña', 'warning')
            return render_template('auth/login.html')
        
        try:
            # ===== USAR EL MÉTODO CORRECTO DEL MODELO =====
            from models.usuarios_model import UsuarioModel
            
            logger.info(f"🔍 Verificando credenciales para: {username}")
            usuario_info = UsuarioModel.verificar_credenciales(username, password)
            
            if usuario_info:
                logger.info(f"✅ Autenticación exitosa para: {username}")
                logger.debug(f"Usuario info: {usuario_info}")
                
                # Establecer sesión con los datos correctos
                session.clear()
                session['usuario_id'] = usuario_info['id']
                session['user_id'] = usuario_info['id']  # Alias
                session['usuario_nombre'] = usuario_info.get('nombre', username)
                session['user_name'] = usuario_info.get('nombre', username)  # Alias
                session['username'] = usuario_info.get('usuario', username)
                session['rol'] = usuario_info['rol']
                session['oficina_id'] = usuario_info.get('oficina_id')
                session['oficina_nombre'] = usuario_info.get('oficina_nombre', '')
                session['last_activity'] = datetime.now().isoformat()
                session.permanent = True
                
                logger.info(f"✅ Sesión establecida - Usuario: {username}, Rol: {usuario_info['rol']}")
                flash(f'Bienvenido {usuario_info.get("nombre", username)}', 'success')
                return redirect(url_for('auth.dashboard'))
            else:
                logger.warning(f"❌ Credenciales inválidas para: {username}")
                flash('Credenciales inválidas', 'danger')
                
        except Exception as e:
            logger.error(f"❌ Error en login: {e}", exc_info=True)
            flash('Error en el proceso de autenticación', 'danger')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    """Cerrar sesión"""
    username = session.get('username', 'Usuario desconocido')
    session.clear()
    logger.info(f"Usuario cerró sesión: {username}")
    flash('Sesión cerrada exitosamente', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal del sistema"""
    try:
        # Obtener estadísticas según el rol del usuario
        rol = session.get('rol', '')
        oficina_id = session.get('oficina_id')
        
        stats = {
            'materiales': 0,
            'solicitudes_pendientes': 0,
            'prestamos_activos': 0,
            'inventario_items': 0,
            'novedades_recientes': 0
        }
        
        # Obtener estadísticas de materiales
        try:
            from models.materiales_model import MaterialModel
            from utils.filters import filtrar_por_oficina_usuario
            
            materiales = MaterialModel.obtener_todos() or []
            materiales_filtrados = filtrar_por_oficina_usuario(materiales, oficina_id)
            stats['materiales'] = len(materiales_filtrados)
        except Exception as e:
            logger.warning(f"Error obteniendo estadísticas de materiales: {e}")
        
        # Obtener estadísticas de solicitudes
        try:
            from models.solicitudes_model import SolicitudModel
            solicitudes = SolicitudModel.obtener_todas() or []
            if rol != 'administrador':
                solicitudes = [s for s in solicitudes if s.get('oficina_id') == oficina_id]
            stats['solicitudes_pendientes'] = len([
                s for s in solicitudes 
                if s.get('estado') in ['pendiente', 'en_revision']
            ])
        except Exception as e:
            logger.warning(f"Error obteniendo estadísticas de solicitudes: {e}")
        
        # Obtener estadísticas de préstamos
        try:
            # ✅ CORRECCIÓN: Usar PrestamosModel en lugar de PrestamoModel
            from models.prestamos_model import PrestamosModel  # <-- CORREGIDO AQUÍ
            prestamos = PrestamosModel.obtener_todos() or []
            if rol != 'administrador':
                prestamos = [p for p in prestamos if p.get('oficina_id') == oficina_id]
            stats['prestamos_activos'] = len([
                p for p in prestamos 
                if p.get('estado') == 'activo'
            ])
        except Exception as e:
            logger.warning(f"Error obteniendo estadísticas de préstamos: {e}")
        
        # Obtener estadísticas de inventario
        try:
            from models.inventario_corporativo_model import InventarioCorporativoModel
            inventario = InventarioCorporativoModel.obtener_todos() or []
            stats['inventario_items'] = len(inventario)
        except Exception as e:
            logger.warning(f"Error obteniendo estadísticas de inventario: {e}")
        
        # Obtener módulos accesibles según el rol
        try:
            from config.permissions import get_accessible_modules
            modulos_accesibles = get_accessible_modules()  
        except ImportError:
            
            try:
                from utils.permissions import get_accessible_modules
                
                modulos_accesibles = get_accessible_modules(rol)
            except ImportError:
                
                try:
                    from config.config import Config
                    modulos_accesibles = Config.ROLES.get(rol.lower(), [])
                except Exception:
                    logger.warning("No se pudo importar Config desde config.config")
                    modulos_accesibles = []
        except Exception as e:
            logger.warning(f"Error obteniendo módulos accesibles: {e}")
            modulos_accesibles = []
        
        return render_template('dashboard.html', 
                             stats=stats,
                             modulos_accesibles=modulos_accesibles,
                             usuario=session.get('usuario_nombre'),
                             rol=rol,
                             oficina=session.get('oficina_nombre'))
    
    except Exception as e:
        logger.error(f"Error en dashboard: {e}", exc_info=True)
        flash('Error cargando el dashboard', 'danger')
        return render_template('dashboard.html', 
                             stats={}, 
                             modulos_accesibles=[],
                             usuario=session.get('usuario_nombre'),
                             rol=session.get('rol'),
                             oficina=session.get('oficina_nombre'))


@auth_bp.route('/test-ldap')
@role_required('administrador')
def test_ldap():
    """Página de prueba de autenticación LDAP"""
    return render_template('auth/test_ldap.html')