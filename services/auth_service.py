# services/auth_service.py

from utils.ldap_auth import ADAuth
from models.usuarios_model import UsuarioModel
from flask_login import login_user
from utils.helpers import sanitizar_username, sanitizar_email, sanitizar_ip
import logging
import re

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self.ad_auth = ADAuth()  
    
    def authenticate(self, username, password, remember=False):
        """
        Autentica un usuario mediante LDAP o base de datos local
        """
        sanitized_user = sanitizar_username(username)
        
        logger.info(f"🔐 Intentando autenticación LDAP para: {sanitized_user}")
        
        try:
            user_data = self.ad_auth.authenticate_user(username, password)
            
            if user_data:
                email = user_data.get('email', '')
                sanitized_email_log = sanitizar_email(email)
                
                logger.info(f"✅ LDAP: Autenticación exitosa para {sanitized_user} ({sanitized_email_log})")
                
                user = UsuarioModel.get_by_username(username)
                
                if not user:
                    logger.info(f"📝 Creando nuevo usuario desde LDAP: {sanitized_user}")
                    user = UsuarioModel.create_from_ldap(user_data)
                else:
                    logger.info(f"🔄 Actualizando usuario existente desde LDAP: {sanitized_user}")
                    user.update_from_ldap(user_data)
                
                try:
                    login_user(user, remember=remember)
                    logger.info(f"✅ Login completado para {sanitized_user}")
                except Exception as login_error:
                    logger.warning(f"⚠️ Flask-Login no está configurado para {sanitized_user}: {login_error}")
                
                return True, user, "Autenticación LDAP exitosa"
        
        except Exception as ldap_error:
            logger.warning(f"⚠️ LDAP falló para {sanitized_user}: {str(ldap_error)}")
        
        logger.info(f"🔄 Intentando autenticación local para {sanitized_user}")
        
        try:
            user = UsuarioModel.get_by_username(username)
            
            if user and user.check_password(password):
                email = getattr(user, 'email', '')
                sanitized_email_log = sanitizar_email(email)
                
                logger.info(f"✅ Autenticación local exitosa para {sanitized_user} ({sanitized_email_log})")
                
                try:
                    login_user(user, remember=remember)
                    logger.info(f"✅ Login completado para {sanitized_user}")
                except Exception as login_error:
                    logger.warning(f"⚠️ Flask-Login no está configurado para {sanitized_user}: {login_error}")
                
                return True, user, "Autenticación local exitosa"
        
        except Exception as db_error:
            logger.error(f"❌ Error en autenticación local para {sanitized_user}: {str(db_error)}")
        
        logger.warning(f"❌ Autenticación fallida para {sanitized_user}")
        return False, None, "Credenciales inválidas"
    
    def test_ldap_connection(self):
        """
        Prueba la conexión con el servidor LDAP
        """
        try:
            result = self.ad_auth.test_connection()
            logger.info("🔌 Prueba de conexión LDAP completada")
            return result
        except Exception as e:
            logger.error(f"❌ Error probando conexión LDAP: {str(e)}")
            return False
    
    def search_ldap_users(self, search_term):
        """
        Busca usuarios en el directorio LDAP
        """
        sanitized_search = sanitizar_username(search_term)
        
        try:
            logger.info(f"🔍 Buscando en LDAP: '{sanitized_search}'")
            results = self.ad_auth.search_user_by_name(search_term)
            logger.info(f"📊 Encontrados {len(results)} resultados para '{sanitized_search}'")
            return results
        except Exception as e:
            logger.error(f"❌ Error buscando usuarios en LDAP para '{sanitized_search}': {str(e)}")
            return []
    
    def logout_user(self, username, ip_address=None):
        """
        Registra el logout de un usuario de forma segura
        """
        sanitized_user = sanitizar_username(username)
        sanitized_ip = sanitizar_ip(ip_address) if ip_address else '[ip-no-disponible]'
        logger.info(f"👋 Logout de {sanitized_user} desde {sanitized_ip}")
    
    def password_reset_attempt(self, username, ip_address=None):
        """
        Registra intentos de reseteo de contraseña de forma segura
        """
        sanitized_user = sanitizar_username(username)
        sanitized_ip = sanitizar_ip(ip_address) if ip_address else '[ip-no-disponible]'
        logger.info(f"🔑 Intento de reseteo de contraseña para {sanitized_user} desde {sanitized_ip}")
    
    def failed_attempt(self, username, reason="desconocido", ip_address=None):
        """
        Registra intentos fallidos de forma segura
        """
        sanitized_user = sanitizar_username(username)
        sanitized_ip = sanitizar_ip(ip_address) if ip_address else '[ip-no-disponible]'
        logger.warning(f"🚫 Intento fallido para {sanitized_user} desde {sanitized_ip}. Razón: {reason}")
    
    def user_activity_log(self, username, activity, details=None, ip_address=None):
        """
        Registra actividades del usuario de forma segura
        """
        sanitized_user = sanitizar_username(username)
        sanitized_ip = sanitizar_ip(ip_address) if ip_address else '[ip-no-disponible]'
        
        log_message = f"📝 Actividad de {sanitized_user} desde {sanitized_ip}: {activity}"
        if details:
            # Limitar detalles para evitar logs excesivos
            if len(str(details)) > 200:
                details = str(details)[:197] + "..."
            log_message += f" - {details}"
        
        logger.info(log_message)