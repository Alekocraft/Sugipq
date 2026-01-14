from flask import Blueprint, render_template, request, redirect, session, flash, url_for, current_app
from models.usuarios_model import UsuarioModel
from utils.permissions import can_access
from utils.helpers import sanitizar_username
import logging

logger = logging.getLogger(__name__)

aprobadores_bp = Blueprint('aprobadores', __name__, url_prefix='/aprobadores')

def _require_login():
    return 'usuario_id' in session or 'user_id' in session

@aprobadores_bp.route('/')
def listar_aprobadores():
    if not _require_login():
        logger.warning("Intento de acceso sin sesión a /aprobadores")
        flash('Debe iniciar sesión para acceder a esta sección', 'warning')
        return redirect(url_for('auth.login'))

    if not can_access('aprobadores', 'view'):
        logger.warning(f"Usuario {sanitizar_username(str(session.get('usuario_id', 'desconocido')))} sin permisos para ver aprobadores")
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect(url_for('dashboard'))

    try:
        aprobadores = UsuarioModel.obtener_aprobadores_desde_tabla()
        
        if aprobadores:
            logger.info(f"Se encontraron {len(aprobadores)} aprobadores")
        else:
            logger.info("No se encontraron aprobadores")
        
        return render_template(
            'aprobadores/listar.html',
            aprobadores=aprobadores or [],
            debug=False
        )

    except Exception as e:
        logger.error(f"Error obteniendo aprobadores: {str(e)}", exc_info=True)
        flash('Ocurrió un error al cargar los aprobadores', 'danger')
        return render_template('aprobadores/listar.html', aprobadores=[], debug=False)