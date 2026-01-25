# -*- coding: utf-8 -*-
import os
import secrets
import warnings
from datetime import timedelta
from dotenv import load_dotenv

 
load_dotenv()

class Config:
    """Configuración base para toda la aplicación"""
    
    # Clave secreta
    # Clave secreta (NO usar un valor hardcodeado en código)
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        env_name = os.getenv('FLASK_ENV', os.getenv('ENV', 'development')).strip().lower()
        if env_name == 'production':
            warnings.warn('SECRET_KEY no configurado en producción; configure SECRET_KEY para sesiones seguras.', RuntimeWarning)
        # En desarrollo, generar una clave temporal para evitar fallos por falta de configuración
        SECRET_KEY = secrets.token_hex(32)
    # Configuración de Flask
    JSON_AS_ASCII = False
    TEMPLATES_AUTO_RELOAD = True
    SESSION_COOKIE_SECURE = False 
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    
    
    # Uploads
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx'}
    
    # Rutas
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'templates')
    STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
    
    # Configuración de roles y permisos
    ROLES = {
        'administrador': ['dashboard', 'materiales', 'solicitudes', 'oficinas', 'aprobadores', 'reportes', 'inventario_corporativo', 'prestamos'],
        'lider_inventario': ['dashboard', 'materiales', 'solicitudes', 'oficinas', 'aprobadores', 'reportes', 'inventario_corporativo', 'prestamos'],
        'oficina_principal': ['dashboard', 'materiales', 'solicitudes'],
        'aprobador': ['dashboard', 'solicitudes'],
        'tesoreria': ['dashboard', 'reportes'],
        'inventario_corporativo': ['dashboard', 'inventario_corporativo']
    }
    LDAP_SERVER = os.getenv('LDAP_SERVER', '').strip()
    LDAP_ENABLED = os.getenv('LDAP_ENABLED', 'true').strip().lower() in ('1','true','yes','y','si') and bool(LDAP_SERVER)
    LDAP_PORT = int(os.getenv('LDAP_PORT', '389'))
    LDAP_DOMAIN = os.getenv('LDAP_DOMAIN', 'qualitascolombia.com.co')
    LDAP_SEARCH_BASE = os.getenv('LDAP_SEARCH_BASE', 'DC=qualitascolombia,DC=com,DC=co')
    LDAP_SERVICE_USER = os.getenv('LDAP_SERVICE_USER')
    LDAP_SERVICE_PASSWORD = os.getenv('LDAP_SERVICE_PASSWORD')
    
    # Fallback a autenticación local si LDAP falla
    LDAP_FALLBACK_LOCAL = True


class DevelopmentConfig(Config):
    """Configuración para desarrollo"""
    DEBUG = True
    TESTING = False
    ENV = 'development'


class ProductionConfig(Config):
    """Configuración para producción"""
    DEBUG = False
    TESTING = False
    ENV = 'production'
    
    # Seguridad en producción
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True


class TestingConfig(Config):
    """Configuración para testing"""
    DEBUG = True
    TESTING = True
    ENV = 'testing'
    WTF_CSRF_ENABLED = False


# Configuración por entorno
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}