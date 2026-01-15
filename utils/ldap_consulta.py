# utils/ldap_consulta.py
"""
Módulo para consultar información del Active Directory 
NO afecta la autenticación LDAP existente
"""
import logging
from ldap3 import Server, Connection, ALL, SUBTREE
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

class ADConsulta:
    """Clase para consultar información del Active Directory (solo lectura)"""
    
    def __init__(self):
        # Usar la misma configuración que ADAuth pero para solo lectura
        self.server_ip = os.getenv('LDAP_SERVER', '')
        self.domain = os.getenv('LDAP_DOMAIN', '')
        self.search_base = os.getenv('LDAP_SEARCH_BASE', '')
        self.service_user = os.getenv('LDAP_SERVICE_USER', '')
        self.service_password = os.getenv('LDAP_SERVICE_PASSWORD', '')
        
    def conectar(self):
        """Establece conexión de solo lectura con AD"""
        try:
            if not all([self.server_ip, self.domain, self.search_base, 
                       self.service_user, self.service_password]):
                logger.warning("Configuración LDAP incompleta para consultas")
                return None
            
            server = Server(self.server_ip, port=389, get_info=ALL)
            user_dn = f"{self.domain}\\{self.service_user}"
            
            conn = Connection(
                server,
                user=user_dn,
                password=self.service_password,
                auto_bind=True
            )
            
            if conn.bound:
                logger.debug("Conexión LDAP de consulta establecida")
                return conn
            else:
                logger.error(f"Error binding LDAP consulta: {conn.last_error}")
                return None
                
        except Exception as e:
            logger.error(f"Error conectando a LDAP para consulta: {e}")
            return None
    
    def buscar_usuario(self, username):
        """
        Busca un usuario en el Active Directory (solo lectura)
        
        Args:
            username: Nombre de usuario (sAMAccountName)
            
        Returns:
            dict: Información del usuario o None si no se encuentra
        """
        conn = None
        try:
            conn = self.conectar()
            if not conn:
                return None
            
            # Atributos a obtener
            atributos = [
                'sAMAccountName',
                'displayName',
                'givenName',
                'sn',
                'mail',
                'department',
                'telephoneNumber',
                'title',
                'userPrincipalName',
                'cn'
            ]
            
            # Buscar usuario por sAMAccountName
            search_filter = f"(&(objectClass=user)(sAMAccountName={username}))"
            
            conn.search(
                search_base=self.search_base,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=atributos,
                size_limit=1
            )
            
            if conn.entries and len(conn.entries) > 0:
                entry = conn.entries[0]
                
                # Extraer información
                info = {
                    'usuario': str(entry.sAMAccountName) if hasattr(entry, 'sAMAccountName') else username,
                    'nombre_completo': str(entry.displayName) if hasattr(entry, 'displayName') else None,
                    'nombre': str(entry.givenName) if hasattr(entry, 'givenName') else None,
                    'apellido': str(entry.sn) if hasattr(entry, 'sn') else None,
                    'email': str(entry.mail) if hasattr(entry, 'mail') else None,
                    'departamento': str(entry.department) if hasattr(entry, 'department') else None,
                    'telefono': str(entry.telephoneNumber) if hasattr(entry, 'telephoneNumber') else None,
                    'cargo': str(entry.title) if hasattr(entry, 'title') else None,
                    'user_principal': str(entry.userPrincipalName) if hasattr(entry, 'userPrincipalName') else None,
                    'cn': str(entry.cn) if hasattr(entry, 'cn') else None,
                    'encontrado': True
                }
                
                # Crear nombre completo si no existe
                if not info['nombre_completo']:
                    if info['nombre'] and info['apellido']:
                        info['nombre_completo'] = f"{info['nombre']} {info['apellido']}"
                    elif info['cn']:
                        info['nombre_completo'] = info['cn']
                
                logger.info(f"Información AD obtenida para {username}")
                return info
            else:
                logger.warning(f"Usuario {username} no encontrado en AD")
                return {
                    'usuario': username,
                    'encontrado': False,
                    'mensaje': 'Usuario no encontrado en Active Directory'
                }
                
        except Exception as e:
            logger.error(f"Error buscando usuario {username} en AD: {e}")
            return {
                'usuario': username,
                'encontrado': False,
                'error': str(e)
            }
        finally:
            if conn and conn.bound:
                conn.unbind()

# Instancia global para consultas
ad_consulta = ADConsulta()