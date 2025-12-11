# blueprints/aprobadores.py - MODIFICADO
from flask import Blueprint, render_template, request, redirect, session, flash, url_for, current_app
from models.usuarios_model import UsuarioModel
from utils.permissions import can_access
import logging

# Configurar logging
logger = logging.getLogger(__name__)

# Crear blueprint de aprobadores
aprobadores_bp = Blueprint('aprobadores', __name__, url_prefix='/aprobadores')

# Helper: Verifica si el usuario está logueado
def _require_login():
    # Verificar ambas posibles claves de sesión
    return 'usuario_id' in session or 'user_id' in session

# Ruta principal: listar aprobadores
@aprobadores_bp.route('/')
def listar_aprobadores():
    """Listar todos los aprobadores del sistema"""
    
    # Verificación de sesión
    if not _require_login():
        logger.warning("Intento de acceso sin sesión a /aprobadores")
        flash('Debe iniciar sesión para acceder a esta sección', 'warning')
        return redirect(url_for('auth.login'))

    # Verificación de permisos
    if not can_access('aprobadores', 'view'):
        logger.warning(f"Usuario {session.get('usuario_id')} sin permisos para ver aprobadores")
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect(url_for('dashboard'))

    try:
        # 🔴 PROBLEMA: Esto está mal - busca en tabla Usuarios
        # aprobadores = UsuarioModel.obtener_aprobadores()
        
        # 🟢 SOLUCIÓN: Usar el nuevo método que busca en tabla Aprobadores
        aprobadores = UsuarioModel.obtener_aprobadores_desde_tabla()
        
        # Log para debugging
        if aprobadores:
            logger.info(f"Se encontraron {len(aprobadores)} aprobadores")
            print(f"📊 Aprobadores obtenidos: {len(aprobadores)} registros")
        else:
            logger.info("No se encontraron aprobadores")
            print("⚠️ No se encontraron aprobadores en la tabla Aprobadores")
        
        return render_template(
            'aprobadores/listar.html',
            aprobadores=aprobadores or [],
            debug=False
        )

    except Exception as e:
        logger.error(f"Error obteniendo aprobadores: {str(e)}", exc_info=True)
        print(f"🔥 ERROR: {str(e)}")
        flash('Ocurrió un error al cargar los aprobadores', 'danger')
        return render_template('aprobadores/listar.html', aprobadores=[], debug=False)