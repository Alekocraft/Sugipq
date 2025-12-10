import os
import logging
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, session, flash,
    jsonify, url_for, send_file
)
from werkzeug.utils import secure_filename

# Configuración de logging PRINCIPAL
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración de logging para LDAP
ldap_logger = logging.getLogger('ldap3')
ldap_logger.setLevel(logging.WARNING)  # Cambiar a DEBUG para troubleshooting

# Configurar formato para LDAP
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Crear directorio de logs si no existe
log_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Configurar handler para archivo de LDAP
ldap_log_file = os.path.join(log_dir, 'ldap.log')
file_handler = logging.FileHandler(ldap_log_file)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
ldap_logger.addHandler(file_handler)

# También configurar un handler para consola (opcional)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(formatter)
ldap_logger.addHandler(console_handler)

logger.info(f"Logging de LDAP configurado. Archivo: {ldap_log_file}")

# Importación de modelos
from models.materiales_model import MaterialModel
from models.oficinas_model import OficinaModel
from models.solicitudes_model import SolicitudModel
from models.usuarios_model import UsuarioModel
from models.inventario_corporativo_model import InventarioCorporativoModel

# Importación de utilidades
from utils.filters import filtrar_por_oficina_usuario, verificar_acceso_oficina
from utils.initialization import inicializar_oficina_principal
from utils.permissions import (
    can_access, can_view_actions,
    get_accessible_modules,
    can_create_novedad, can_manage_novedad
)

# Importación de blueprints principales (siempre disponibles)
from blueprints.auth import auth_bp
from blueprints.materiales import materiales_bp
from blueprints.solicitudes import solicitudes_bp
from blueprints.oficinas import oficinas_bp
from blueprints.aprobadores import aprobadores_bp
from blueprints.reportes import reportes_bp
from blueprints.api import api_bp
from blueprints.usuarios import usuarios_bp

# Importación condicional de blueprint de préstamos
try:
    from blueprints.prestamos import prestamos_bp
    logger.info("Blueprint de préstamos cargado exitosamente")
except ImportError as e:
    logger.warning(f"Blueprint de préstamos no disponible: {e}")
    from flask import Blueprint
    prestamos_bp = Blueprint('prestamos', __name__)
    
    @prestamos_bp.route('/')
    def prestamos_vacio():
        flash('Módulo de préstamos no disponible', 'warning')
        return redirect('/dashboard')

# Importación condicional de blueprint de inventario corporativo
try:
    from blueprints.inventario_corporativo import inventario_corporativo_bp
    logger.info("Blueprint de inventario corporativo cargado desde blueprints")
except ImportError as e:
    logger.warning(f"Blueprint de inventario corporativo no encontrado en blueprints: {e}")
    try:
        from routes_inventario_corporativo import bp_inv as inventario_corporativo_bp
        logger.info("Blueprint de inventario corporativo cargado desde routes_inventario_corporativo")
    except ImportError as e2:
        logger.warning(f"Blueprint de inventario corporativo no disponible: {e2}")
        from flask import Blueprint
        inventario_corporativo_bp = Blueprint('inventario_corporativo', __name__)
        
        @inventario_corporativo_bp.route('/')
        def inventario_vacio():
            flash('Módulo de inventario corporativo no disponible', 'warning')
            return redirect('/dashboard')

# Conexión a base de datos
from database import get_database_connection

# Configuración de la aplicación Flask
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)

# Configuración de seguridad y aplicación
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(32))
app.config['JSON_AS_ASCII'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Configuración de archivos subidos
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
logger.info(f"Directorio de uploads configurado en: {os.path.abspath(UPLOAD_FOLDER)}")

# Context processor para funciones de utilidad en templates
@app.context_processor
def utility_processor():
    """Inyecta funciones de permisos en todos los templates"""
    return dict(
        can_create_novedad=can_create_novedad,
        can_manage_novedad=can_manage_novedad,
        can_access=can_access,
        can_view_actions=can_view_actions,
        get_accessible_modules=get_accessible_modules
    )

# Registro de blueprints principales
app.register_blueprint(solicitudes_bp, url_prefix='/solicitudes')
app.register_blueprint(auth_bp)
app.register_blueprint(materiales_bp)
app.register_blueprint(oficinas_bp)
app.register_blueprint(aprobadores_bp)
app.register_blueprint(reportes_bp)
app.register_blueprint(api_bp)
app.register_blueprint(usuarios_bp)

# Registro de blueprints opcionales
app.register_blueprint(prestamos_bp, url_prefix='/prestamos')
logger.info("Blueprint de préstamos registrado")

app.register_blueprint(inventario_corporativo_bp, url_prefix='/inventario-corporativo')
logger.info("Blueprint de inventario corporativo registrado")

# Ruta principal y redirección
@app.route('/')
def index():
    """Redirige usuarios autenticados al dashboard, otros al login"""
    if 'user_id' in session:
        return redirect('/dashboard')
    return redirect('/auth/login')

@app.route('/dashboard')
def dashboard():
    """Página principal del dashboard de la aplicación"""
    if 'user_id' not in session:
        logger.warning("Intento de acceso al dashboard sin autenticación")
        return redirect('/auth/login')
    return render_template('dashboard.html')

# Manejadores de errores
@app.errorhandler(404)
def pagina_no_encontrada(error):
    """Maneja errores 404 - Página no encontrada"""
    logger.warning(f"Página no encontrada: {request.path}")
    return render_template('error/404.html'), 404

@app.errorhandler(500)
def error_interno(error):
    """Maneja errores 500 - Error interno del servidor"""
    logger.error(f"Error interno del servidor: {error}", exc_info=True)
    return render_template('error/500.html'), 500

@app.errorhandler(413)
def archivo_demasiado_grande(error):
    """Maneja errores 413 - Archivo demasiado grande"""
    logger.warning(f"Intento de subir archivo demasiado grande: {request.url}")
    flash('El archivo es demasiado grande. Tamaño máximo: 16MB', 'danger')
    return redirect(request.url)

# Punto de entrada de la aplicación
if __name__ == '__main__':
    logger.info("Iniciando servidor Flask de Sistema de Gestión de Inventarios")
    logger.info(f"Logging de LDAP activo en: {ldap_log_file}")
    
    # Inicialización del sistema
    inicializar_oficina_principal()
    
    # Configuración del puerto
    port = int(os.environ.get('PORT', 5010))
    logger.info(f"Servidor iniciado en puerto: {port}")
    
    app.run(
        debug=True,
        host='0.0.0.0',
        port=port
    )