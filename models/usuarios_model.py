# models/usuarios_model.py - MODIFICADO para priorizar BD local, luego LDAP como fallback
from database import get_database_connection
import logging
from config.config import Config
import bcrypt

logger = logging.getLogger(__name__)

class UsuarioModel:
    
    @staticmethod
    def verificar_credenciales(usuario, contraseña):
        """
        Verifica credenciales PRIORIZANDO BD local, luego LDAP como fallback
        """
        logger.info(f"🔐 Intentando autenticación para: {usuario}")
        
        # 1. PRIMERO: Intentar autenticación local
        logger.info(f"🔄 1. Intentando autenticación LOCAL para: {usuario}")
        usuario_local = UsuarioModel._verificar_localmente_corregido(usuario, contraseña)
        
        if usuario_local:
            logger.info(f"✅ Autenticación LOCAL exitosa para: {usuario}")
            logger.info(f"📊 Datos usuario local: {usuario_local}")
            return usuario_local
        
        logger.info(f"❌ Autenticación LOCAL falló para: {usuario}")
        
        # 2. SEGUNDO: Solo si LDAP está habilitado
        if Config.LDAP_ENABLED:
            logger.info(f"🔄 2. Intentando LDAP para: {usuario}")
            try:
                from utils.ldap_auth import ad_auth
                ad_user = ad_auth.authenticate_user(usuario, contraseña)
                
                if ad_user:
                    logger.info(f"✅ LDAP exitoso para: {usuario}")
                    # Sincronizar con BD local
                    usuario_info = UsuarioModel.sync_user_from_ad(ad_user)
                    
                    if usuario_info:
                        return usuario_info
                    else:
                        logger.error(f"❌ Error sincronizando usuario LDAP: {usuario}")
                else:
                    logger.warning(f"❌ LDAP también falló para: {usuario}")
            except Exception as ldap_error:
                logger.error(f"❌ Error en LDAP: {ldap_error}")
        
        # 3. Si todo falla
        logger.error(f"❌ TODAS las autenticaciones fallaron para: {usuario}")
        return None

    @staticmethod
    def _verificar_localmente_corregido(usuario, contraseña):
        """
        Autenticación local CORREGIDA - compatible con tu BD exacta
        """
        conn = get_database_connection()
        if not conn:
            logger.error("❌ No hay conexión a la BD")
            return None
            
        try:
            cursor = conn.cursor()
            
            # CONSULTA CORREGIDA según tu estructura exacta de BD
            cursor.execute("""
                SELECT 
                    u.UsuarioId, 
                    u.NombreUsuario, 
                    u.CorreoElectronico,
                    u.Rol, 
                    u.OficinaId, 
                    o.NombreOficina,
                    u.ContraseñaHash
                FROM Usuarios u
                LEFT JOIN Oficinas o ON u.OficinaId = o.OficinaId
                WHERE u.NombreUsuario = ? AND u.Activo = 1
            """, (usuario,))
            
            row = cursor.fetchone()
            
            if row:
                logger.info(f"✅ Usuario encontrado en BD: {usuario}")
                logger.info(f"📋 Datos fila: UsuarioId={row[0]}, Rol={row[3]}, OficinaId={row[4]}")
                
                # Verificar contraseña hash
                stored_hash = row[6]  # ContraseñaHash está en posición 7 (índice 6)
                
                if not stored_hash:
                    logger.error(f"❌ Hash de contraseña vacío para: {usuario}")
                    return None
                
                logger.info(f"🔑 Hash almacenado (primeros 30 chars): {stored_hash[:30]}...")
                logger.info(f"🔑 Longitud hash: {len(stored_hash)}")
                
                try:
                    # IMPORTANTE: bcrypt.checkpw necesita ambos parámetros como bytes
                    password_bytes = contraseña.encode('utf-8')
                    hash_bytes = stored_hash.encode('utf-8')
                    
                    logger.info(f"🔑 Verificando contraseña...")
                    if bcrypt.checkpw(password_bytes, hash_bytes):
                        usuario_info = {
                            'id': row[0],           # UsuarioId
                            'usuario': row[1],      # NombreUsuario
                            'nombre': row[2] if row[2] else row[1],  # CorreoElectronico o NombreUsuario
                            'rol': row[3],          # Rol
                            'oficina_id': row[4],   # OficinaId
                            'oficina_nombre': row[5] if row[5] else ''  # NombreOficina
                        }
                        logger.info(f"✅ Contraseña CORRECTA para: {usuario}")
                        logger.info(f"📊 Info usuario final: {usuario_info}")
                        return usuario_info
                    else:
                        logger.error(f"❌ Contraseña INCORRECTA para: {usuario}")
                        return None
                        
                except Exception as bcrypt_error:
                    logger.error(f"❌ Error en bcrypt.checkpw: {bcrypt_error}")
                    logger.error(f"❌ Tipo de hash: {type(stored_hash)}")
                    logger.error(f"❌ Contraseña proporcionada: '{contraseña}'")
                    return None
            else:
                logger.warning(f"⚠️ Usuario NO encontrado en BD local: {usuario}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error en _verificar_localmente_corregido: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def sync_user_from_ad(ad_user):
        """
        Sincroniza usuario desde AD a la base de datos local
        SOLO para usuarios que no existan localmente
        """
        conn = get_database_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
        
            # Verificar si el usuario ya existe
            cursor.execute("""
                SELECT 
                    UsuarioId, 
                    NombreUsuario, 
                    CorreoElectronico, 
                    Rol, 
                    OficinaId
                FROM Usuarios 
                WHERE NombreUsuario = ? AND Activo = 1
            """, (ad_user['username'],))  # CAMBIADO: 'username' no 'samaccountname'
        
            existing = cursor.fetchone()
        
            if existing:
                # Usuario ya existe localmente
                usuario_info = {
                    'id': existing[0],
                    'usuario': existing[1],
                    'nombre': existing[2] if existing[2] else existing[1],
                    'rol': existing[3],
                    'oficina_id': existing[4],
                    'oficina_nombre': ''
                }
                logger.info(f"ℹ️ Usuario ya existía en BD local: {ad_user['username']}")
                return usuario_info
            else:
                # Crear nuevo usuario desde AD
                default_rol = 'usuario'
                if 'role' in ad_user:  # CAMBIADO: 'role' no 'grupos'
                    default_rol = ad_user['role']
                else:
                    # Verificar grupos para determinar rol
                    groups = ad_user.get('groups', [])
                    if any('administradores' in g.lower() for g in groups):
                        default_rol = 'admin'  # Tu sistema usa 'admin'
                    elif any('aprobadores' in g.lower() for g in groups):
                        default_rol = 'aprobador'
                    elif any('tesorer' in g.lower() for g in groups):
                        default_rol = 'tesoreria'
            
                # Obtener oficina por defecto
                departamento = ad_user.get('department', '')
                oficina_id = UsuarioModel.get_default_office(departamento)
            
                # Si no hay oficina, usar la primera
                if not oficina_id:
                    cursor.execute("SELECT TOP 1 OficinaId FROM Oficinas WHERE Activo = 1")
                    oficina_result = cursor.fetchone()
                    oficina_id = oficina_result[0] if oficina_result else 1
            
                # Insertar nuevo usuario
                cursor.execute("""
                    INSERT INTO Usuarios (
                        NombreUsuario, 
                        CorreoElectronico, 
                        Rol, 
                        OficinaId, 
                        Activo, 
                        FechaCreacion,
                        ContraseñaHash
                    ) VALUES (?, ?, ?, ?, 1, GETDATE(), 'LDAP_USER')
                """, (
                    ad_user['username'],
                    ad_user.get('email', f"{ad_user['username']}@qualitascolombia.com.co"),
                    default_rol,
                    oficina_id
                ))
            
                conn.commit()
            
                # Obtener el ID del usuario creado
                cursor.execute("SELECT UsuarioId FROM Usuarios WHERE NombreUsuario = ?", (ad_user['username'],))
                new_id = cursor.fetchone()[0]
            
                usuario_info = {
                    'id': new_id,
                    'usuario': ad_user['username'],
                    'nombre': ad_user.get('full_name', ad_user['username']),
                    'rol': default_rol,
                    'oficina_id': oficina_id,
                    'oficina_nombre': ''
                }
            
                logger.info(f"✅ Nuevo usuario sincronizado desde AD: {ad_user['username']}")
                return usuario_info
        except Exception as e:
            logger.error(f"❌ Error sincronizando usuario AD: {e}")
            import traceback
            traceback.print_exc()
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def get_default_office(department):
        """
        Obtiene el ID de oficina por defecto basado en departamento AD
        """
        conn = get_database_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
        
            # Mapeo de departamentos Qualitas a oficinas
            department_mapping = {
                'tesorería': 'Tesoreria',
                'finanzas': 'Tesoreria',
                'contabilidad': 'Tesoreria',
                'administración': 'Administración',
                'gerencia': 'Gerencia',
                'sistemas': 'Sistemas',
                'tecnología': 'Sistemas',
                'rrhh': 'Recursos Humanos',
                'recursos humanos': 'Recursos Humanos',
                'comercial': 'Comercial',
                'ventas': 'Comercial',
                'operaciones': 'Operaciones',
                'logística': 'Logística',
                'almacén': 'Logística'
            }
        
            department_lower = (department or '').lower()
        
            # Buscar oficina por mapeo de departamento
            for dept_key, dept_name in department_mapping.items():
                if dept_key in department_lower:
                    cursor.execute("""
                        SELECT OficinaId FROM Oficinas 
                        WHERE NombreOficina LIKE ? AND Activo = 1
                    """, (f'%{dept_name}%',))
                    result = cursor.fetchone()
                    if result:
                        return result[0]
        
            # Si no encuentra, buscar oficina por nombre similar al departamento
            if department:
                cursor.execute("""
                    SELECT OficinaId FROM Oficinas 
                    WHERE (NombreOficina LIKE ? OR Ubicacion LIKE ?) 
                    AND Activo = 1
                    ORDER BY OficinaId
                """, (f'%{department}%', f'%{department}%'))
                result = cursor.fetchone()
                if result:
                    return result[0]
        
            # Si todo falla, usar la primera oficina activa
            cursor.execute("SELECT TOP 1 OficinaId FROM Oficinas WHERE Activo = 1 ORDER BY OficinaId")
            default_office = cursor.fetchone()
        
            return default_office[0] if default_office else 1
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo oficina por defecto: {e}")
            return 1
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def obtener_aprobadores():
        """
        Obtiene usuarios con rol de aprobación
        """
        conn = get_database_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    UsuarioId, 
                    CorreoElectronico, 
                    NombreUsuario, 
                    OficinaId
                FROM Usuarios 
                WHERE Rol IN ('aprobador', 'administrador') AND Activo = 1
                ORDER BY CorreoElectronico
            """)
            
            aprobadores = []
            for row in cursor.fetchall():
                aprobadores.append({
                    'id': row[0],
                    'nombre': row[1] if row[1] else row[2],  # CorreoElectronico o NombreUsuario
                    'usuario': row[2],
                    'oficina_id': row[3]
                })
            
            return aprobadores
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo aprobadores: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def crear_usuario_manual(usuario_data):
        """
        Crea usuario manualmente (para casos especiales)
        
        Args:
            usuario_data: Dict con datos del usuario
            
        Returns:
            bool: True si éxito
        """
        conn = get_database_connection()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            
            # Generar hash de contraseña
            password_hash = bcrypt.hashpw(
                usuario_data['password'].encode('utf-8'), 
                bcrypt.gensalt()
            ).decode('utf-8')
            
            # Insertar usuario
            cursor.execute("""
                INSERT INTO Usuarios (
                    NombreUsuario, 
                    CorreoElectronico, 
                    Rol, 
                    OficinaId, 
                    ContraseñaHash, 
                    Activo, 
                    FechaCreacion
                ) VALUES (?, ?, ?, ?, ?, 1, GETDATE())
            """, (
                usuario_data['usuario'],
                usuario_data.get('nombre', usuario_data['usuario']),
                usuario_data['rol'],
                usuario_data['oficina_id'],
                password_hash
            ))
            
            conn.commit()
            logger.info(f"✅ Usuario manual creado: {usuario_data['usuario']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creando usuario manual: {e}")
            conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def crear_usuario_admin_inicial():
        """
        Crea un usuario administrador inicial si no existe ninguno
        Contraseña por defecto: admin123
        """
        conn = get_database_connection()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            
            # Verificar si ya existe un usuario admin
            cursor.execute("SELECT COUNT(*) FROM Usuarios WHERE Rol = 'administrador' AND Activo = 1")
            admin_count = cursor.fetchone()[0]
            
            if admin_count > 0:
                logger.info("✅ Ya existe al menos un usuario administrador")
                return True
            
            # Verificar si existe la oficina por defecto
            cursor.execute("SELECT TOP 1 OficinaId FROM Oficinas WHERE Activo = 1 ORDER BY OficinaId")
            default_office = cursor.fetchone()
            
            oficina_id = default_office[0] if default_office else None
            
            if not oficina_id:
                logger.error("❌ No hay oficinas activas para asignar al usuario admin")
                return False
            
            # Generar hash para contraseña 'admin123'
            password_hash = bcrypt.hashpw(
                'admin123'.encode('utf-8'), 
                bcrypt.gensalt()
            ).decode('utf-8')
            
            # Crear usuario admin - USANDO 'administrador' como rol (no 'admin')
            cursor.execute("""
                INSERT INTO Usuarios (
                    NombreUsuario, 
                    CorreoElectronico, 
                    Rol, 
                    OficinaId, 
                    ContraseñaHash, 
                    Activo, 
                    FechaCreacion
                ) VALUES ('admin', 'Administrador del Sistema', 'administrador', ?, ?, 1, GETDATE())
            """, (oficina_id, password_hash))
            
            conn.commit()
            logger.info("✅ Usuario administrador creado exitosamente")
            logger.info("🔑 Credenciales: usuario=admin, contraseña=admin123")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creando usuario admin: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def obtener_por_id(usuario_id):
        """
        Obtiene usuario por ID
        """
        conn = get_database_connection()
        if not conn:
            return None
            
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    u.UsuarioId, 
                    u.NombreUsuario, 
                    u.CorreoElectronico,
                    u.Rol, 
                    u.OficinaId, 
                    o.NombreOficina
                FROM Usuarios u
                LEFT JOIN Oficinas o ON u.OficinaId = o.OficinaId
                WHERE u.UsuarioId = ? AND u.Activo = 1
            """, (usuario_id,))
            
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row[0],
                    'usuario': row[1],
                    'nombre': row[2] if row[2] else row[1],
                    'rol': row[3],
                    'oficina_id': row[4],
                    'oficina_nombre': row[5] if row[5] else ''
                }
            return None
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo usuario por ID: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def obtener_todos():
        """
        Obtiene todos los usuarios activos
        """
        conn = get_database_connection()
        if not conn:
            return []
            
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    u.UsuarioId, 
                    u.NombreUsuario, 
                    u.CorreoElectronico,
                    u.Rol, 
                    u.OficinaId, 
                    o.NombreOficina,
                    u.FechaCreacion
                FROM Usuarios u
                LEFT JOIN Oficinas o ON u.OficinaId = o.OficinaId
                WHERE u.Activo = 1
                ORDER BY u.NombreUsuario
            """)
            
            usuarios = []
            for row in cursor.fetchall():
                usuarios.append({
                    'id': row[0],
                    'usuario': row[1],
                    'nombre': row[2] if row[2] else row[1],
                    'rol': row[3],
                    'oficina_id': row[4],
                    'oficina_nombre': row[5] if row[5] else '',
                    'fecha_creacion': row[6]
                })
            
            return usuarios
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo todos los usuarios: {e}")
            return []
        finally:
            if conn:
                conn.close()
    @staticmethod
    def map_ad_role_to_system_role(ad_user):
        """
        Mapea el rol de AD al rol del sistema según la configuración de permisos
    
        Args:
            ad_user: Diccionario con información del usuario de AD
        
        Returns:
            str: Rol del sistema (debe coincidir con ROLE_PERMISSIONS en config/permissions.py)
        """
        # Verificar si ldap_auth ya asignó un rol
        if 'role' in ad_user:
            ad_role = ad_user['role']
        
            # Mapear roles de AD a roles del sistema
            role_mapping = {
                'admin': 'administrador',  # AD dice 'admin', sistema dice 'administrador'
                'finanzas': 'tesoreria',
                'almacen': 'lider_inventario',
                'rrhh': 'usuario',
                'usuario': 'usuario'
            }
        
            # Si está mapeado, usar el mapeo
            if ad_role in role_mapping:
                return role_mapping[ad_role]
        
            # Si no, verificar si coincide con algún rol del sistema
            from config.permissions import ROLE_PERMISSIONS
            if ad_role in ROLE_PERMISSIONS:
                return ad_role
    
        # Si no hay rol de AD o no está mapeado, usar grupos/departamento
        groups = ad_user.get('groups', [])
        department = (ad_user.get('department') or '').lower()
    
        # Verificar por grupos
        if any('administradores' in g.lower() for g in groups):
            return 'administrador'
        elif any('tesorer' in g.lower() or 'financ' in g.lower() for g in groups):
            return 'tesoreria'
        elif any('lider' in g.lower() and 'invent' in g.lower() for g in groups):
            return 'lider_inventario'
        elif any('aprobador' in g.lower() for g in groups):
            return 'aprobador'
        elif any('coq' in g.lower() for g in groups):
            return 'oficina_coq'
        elif any('polo' in g.lower() for g in groups):
            return 'oficina_polo_club'
    
        # Verificar por departamento
        if 'tesorer' in department or 'financ' in department:
            return 'tesoreria'
        elif 'admin' in department:
            return 'administrador'
        elif 'logist' in department or 'almacen' in department:
            return 'lider_inventario'
    
        # Por defecto
        return 'usuario'