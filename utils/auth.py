import logging
from flask import session, flash, redirect, url_for, request
from functools import wraps

logger = logging.getLogger(__name__)

def require_login():
    """
    Verifica si el usuario estÃ¡ autenticado en el sistema
    
    Returns:
        bool: True si el usuario tiene sesiÃ³n activa
    """
    is_authenticated = 'user_id' in session or 'usuario_id' in session
    logger.debug(f"VerificaciÃ³n de autenticaciÃ³n: {is_authenticated}")
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
    Decorador para proteger rutas que requieren autenticaciÃ³n
    
    Args:
        f: FunciÃ³n a decorar
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not require_login():
            logger.warning(f"Intento de acceso no autenticado a {request.endpoint}")
            flash('Por favor inicie sesiÃ³n para acceder a esta pÃ¡gina.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        logger.debug(f"Acceso autorizado a {request.endpoint}")
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """
    Decorador para proteger rutas que requieren roles especÃ­ficos
    
    Args:
        *roles: Roles requeridos para acceder
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not require_login():
                logger.warning(f"Intento de acceso no autenticado a ruta con roles {roles}")
                flash('Por favor inicie sesiÃ³n.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            if not has_role(*roles):
                user_role = session.get('rol', 'No definido')
                logger.warning(f"Usuario rol '{user_role}' intentÃ³ acceder a ruta que requiere roles {roles}")
                flash('No tiene permisos para acceder a esta secciÃ³n.', 'danger')
                return redirect(url_for('auth.dashboard'))
            
            logger.debug(f"Acceso autorizado con rol a {request.endpoint}")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_current_user():
    """
    Obtiene la informaciÃ³n del usuario actualmente autenticado
    
    Returns:
        dict: InformaciÃ³n del usuario o None si no estÃ¡ autenticado
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
    Verifica si el usuario puede acceder a un mÃ³dulo especÃ­fico segÃºn su rol
    
    Args:
        module_name: Nombre del mÃ³dulo a verificar
        
    Returns:
        bool: True si el usuario tiene acceso al mÃ³dulo
    """
    from config.config import Config
    user_role = (session.get('rol', '') or '').strip().lower()
    allowed_modules = Config.ROLES.get(user_role, [])
    
    has_access = module_name in allowed_modules
    logger.debug(f"Acceso a mÃ³dulo '{module_name}' para rol '{user_role}': {has_access}")
    return has_access