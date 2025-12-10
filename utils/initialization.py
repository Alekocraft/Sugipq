import os
import logging
from datetime import datetime
import pyodbc  # Añadir import para manejar errores específicos
from database import get_database_connection
from models.oficinas_model import OficinaModel

logger = logging.getLogger(__name__)

def inicializar_oficina_principal():
    """Verifica y crea la oficina COQ principal si no existe en la base de datos"""
    try:
        logger.info("Verificando existencia de la oficina COQ...")
        
        # Usar el modelo para verificar existencia
        oficina_principal = OficinaModel.obtener_por_nombre("COQ")

        if not oficina_principal:
            logger.info("Creando oficina COQ...")
            conn = get_database_connection()
            
            if conn is None:
                logger.error("No se pudo obtener conexión a la base de datos")
                return False
                
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    INSERT INTO Oficinas (
                        NombreOficina, 
                        DirectorOficina, 
                        Ubicacion, 
                        EsPrincipal, 
                        Activo, 
                        FechaCreacion,
                        Email
                    ) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    "COQ",
                    "Director General",
                    "Ubicación Principal",
                    1,
                    1,
                    datetime.now(),
                    "coq@empresa.com"
                ))

                conn.commit()
                logger.info("✅ Oficina COQ creada exitosamente")

                # Verificar la creación
                oficina_verificada = OficinaModel.obtener_por_nombre("COQ")
                if oficina_verificada:
                    logger.info(f"✅ Oficina COQ verificada - ID: {oficina_verificada['id']}")
                else:
                    logger.warning("⚠️ No se pudo verificar la creación de la oficina COQ")
                    
            except pyodbc.IntegrityError as e:
                # Manejar específicamente error de integridad (duplicado)
                error_str = str(e)
                if any(keyword in error_str for keyword in ['UQ_Oficinas_Nombre', '2627', 'duplicate key']):
                    logger.info("ℹ️ Oficina COQ ya existe (evitado duplicado por constraint)")
                else:
                    logger.error(f"❌ Error de integridad en base de datos: {e}")
                    return False
                    
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
                    
        else:
            logger.info(f"✅ Oficina COQ ya existe - ID: {oficina_principal['id']}")
            
        return True
        
    except pyodbc.Error as e:
        # Manejar otros errores de pyodbc
        logger.error(f"❌ Error de base de datos: {e}")
        return False
        
    except Exception as e:
        logger.error(f"❌ Error inicializando oficina principal: {e}", exc_info=True)
        return False

def inicializar_directorios():
    """Crea los directorios necesarios para el funcionamiento de la aplicación"""
    from config.config import Config
    
    directorios = [
        Config.UPLOAD_FOLDER,
        os.path.join(Config.UPLOAD_FOLDER, 'productos'),
        os.path.join(Config.UPLOAD_FOLDER, 'documentos'),
        os.path.join(Config.UPLOAD_FOLDER, 'perfiles'),
        os.path.join(Config.UPLOAD_FOLDER, 'temp')
    ]
    
    for directorio in directorios:
        try:
            os.makedirs(directorio, exist_ok=True)
            logger.debug(f"📁 Directorio verificado/creado: {directorio}")
        except Exception as e:
            logger.error(f"❌ Error creando directorio {directorio}: {e}")
            # No retornar False aquí, continuar con otros directorios

def verificar_configuracion():
    """Valida la configuración básica del sistema"""
    from config.config import Config
    
    logger.info("🔧 Verificando configuración del sistema...")
    
    directorios_requeridos = [Config.TEMPLATE_FOLDER, Config.STATIC_FOLDER]
    for folder in directorios_requeridos:
        if not os.path.exists(folder):
            logger.error(f"❌ Directorio requerido no encontrado: {folder}")
        else:
            logger.debug(f"✅ Directorio encontrado: {folder}")
    
    if Config.SECRET_KEY == 'dev-secret-key-change-in-production':
        logger.warning("⚠️ Usando SECRET_KEY por defecto - Cambiar en producción")
    
    logger.info("✅ Verificación de configuración completada")

def inicializar_roles_permisos():
    """Verifica la configuración de roles y permisos del sistema"""
    try:
        from config.config import Config
        roles_configurados = list(Config.ROLES.keys())
        logger.info(f"👥 Roles configurados en el sistema: {len(roles_configurados)} roles")
        logger.debug(f"📋 Roles: {', '.join(roles_configurados)}")
        
    except Exception as e:
        logger.error(f"❌ Error verificando configuración de roles: {e}")

def inicializar_todo():
    """Ejecuta todas las rutinas de inicialización del sistema"""
    logger.info("🚀 Iniciando proceso de inicialización del sistema...")
    
    verificar_configuracion()
    inicializar_directorios()
    
    # Inicializar oficina principal - continuar incluso si falla
    try:
        inicializar_oficina_principal()
    except Exception as e:
        logger.error(f"❌ Error en inicialización de oficina: {e}")
        # Continuar con otras inicializaciones
    
    inicializar_roles_permisos()
    
    logger.info("✅ Proceso de inicialización completado")

# Para compatibilidad con imports existentes
if __name__ == "__main__":
    # Ejecutar inicialización si se ejecuta directamente
    inicializar_todo()