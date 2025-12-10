# services/auth_service.py
from utils.ldap_auth import LDAPAuth
from models.usuarios_model import Usuario
from flask_login import login_user
import bcrypt
import logging

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self.ldap_auth = LDAPAuth()
    
    def authenticate(self, username, password, remember=False):
        """
        Autentica usuario usando LDAP primero, luego base de datos como fallback
        """
        # 1. Intentar autenticación LDAP
        success, ldap_user_data, message = self.ldap_auth.authenticate(username, password)
        
        if success:
            # Buscar o crear usuario en base de datos
            user = Usuario.get_by_username(username)
            
            if not user:
                # Crear nuevo usuario desde LDAP
                user = Usuario.create_from_ldap(ldap_user_data)
            
            # Actualizar información desde LDAP
            user.update_from_ldap(ldap_user_data)
            
            # Login con Flask-Login
            login_user(user, remember=remember)
            return True, user, "Autenticación LDAP exitosa"
        
        # 2. Fallback a autenticación de base de datos
        logger.info(f"LDAP falló, intentando autenticación local para {username}")
        user = Usuario.get_by_username(username)
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            return True, user, "Autenticación local exitosa"
        
        return False, None, "Credenciales inválidas"