# config/ldap_config.py
"""
Configuración para conexión con Active Directory Qualitas Colombia
"""
import os
from dotenv import load_dotenv


load_dotenv()

LDAP_SERVER = os.getenv('LDAP_SERVER', '10.60.0.30')
LDAP_PORT = int(os.getenv('LDAP_PORT', '389'))
LDAP_DOMAIN = os.getenv('LDAP_DOMAIN', 'qualitascolombia.com.co')
LDAP_SEARCH_BASE = os.getenv('LDAP_SEARCH_BASE', 'DC=qualitascolombia,DC=com,DC=co')


LDAP_SERVICE_USER = os.getenv('LDAP_SERVICE_USER', 'userauge')
LDAP_SERVICE_PASSWORD = os.getenv('LDAP_SERVICE_PASSWORD')

# Configuración de mapeo de roles AD -> Sistema
AD_ROLE_MAPPING = {
    'administrador': ['gerencia', 'admin', 'administrador'],
    'lider_inventario': ['almacen', 'logistica', 'inventario'],
    'tesoreria': ['contabilidad', 'tesoreria'],
}

# Timeout en segundos
LDAP_CONNECTION_TIMEOUT = 10