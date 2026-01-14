"""
Servicio unificado de notificaciones por email para:
- Inventario Corporativo (asignaciones)
- Material POP (solicitudes y novedades)
- Préstamos

Versión segura - Cumple con reporte de vulnerabilidades
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from database import get_database_connection
from utils.helpers import sanitizar_email, sanitizar_identificacion, sanitizar_username, sanitizar_ip
import os
import re

logger = logging.getLogger(__name__)

# ============================================================================
# FUNCIONES DE SANITIZACIÓN PARA LOGS SEGUROS (compatibilidad)
# ============================================================================
def _sanitizar_email_compatibilidad(email):
    """Función de compatibilidad que usa la función de helpers.py"""
    return sanitizar_email(email)


def _sanitizar_lista_emails_compatibilidad(emails):
    """Función de compatibilidad para listas de emails"""
    if not emails:
        return []
    return [sanitizar_email(email) for email in emails]


# ============================================================================
# CONFIGURACIÓN DE EMAIL - Cargada desde variables de entorno
# ============================================================================
def _load_email_config():
    """Carga configuración de email desde variables de entorno"""
    try:
        smtp_server = os.getenv('SMTP_SERVER')
        smtp_port = os.getenv('SMTP_PORT', '25')
        use_tls = os.getenv('SMTP_USE_TLS', 'False').lower() == 'true'
        from_email = os.getenv('SMTP_FROM_EMAIL', 'noreply@qualitascolombia.com.co')
        
        # DEPURACIÓN: Mostrar lo que se está cargando (con sanitización)
        logger.info(f"=== CONFIGURACIÓN SMTP CARGADA ===")
        logger.info(f"SMTP_SERVER: {smtp_server}")
        logger.info(f"SMTP_PORT: {smtp_port}")
        logger.info(f"SMTP_USE_TLS: {use_tls}")
        logger.info(f"SMTP_FROM_EMAIL: {sanitizar_email(from_email)}")
        logger.info("================================")
        
        if not smtp_server:
            logger.warning("⚠️ CRÍTICO: SMTP_SERVER no configurado en variables de entorno")
            # Configuración de fallback (usar variables de entorno)
            return {
                'smtp_server': os.getenv('SMTP_SERVER', 'localhost'),
                'smtp_port': int(os.getenv('SMTP_PORT', 25)),
                'use_tls': os.getenv('SMTP_USE_TLS', 'false').lower() == 'true',
                'smtp_user': os.getenv('SMTP_USER', ''),
                'smtp_password': os.getenv('SMTP_PASSWORD', ''),
                'from_email': os.getenv('SMTP_FROM_EMAIL', 'noreply@qualitascolombia.com.co'),
                'from_name': 'Sistema de Gestión de Inventarios'
            }
            
        config = {
            'smtp_server': smtp_server,
            'smtp_port': int(smtp_port),
            'use_tls': use_tls,
            'smtp_user': os.getenv('SMTP_USER', ''),
            'smtp_password': os.getenv('SMTP_PASSWORD', ''),
            'from_email': from_email,
            'from_name': 'Sistema de Gestión de Inventarios'
        }
        
        logger.info("✅ Configuración SMTP cargada exitosamente")
        return config
        
    except Exception as e:
        logger.error(f"❌ Error cargando configuración de email: {str(e)}")
        # Configuración de fallback (usar variables de entorno)
        return {
            'smtp_server': os.getenv('SMTP_SERVER', 'localhost'),
            'smtp_port': int(os.getenv('SMTP_PORT', 25)),
            'use_tls': os.getenv('SMTP_USE_TLS', 'false').lower() == 'true',
            'smtp_user': os.getenv('SMTP_USER', ''),
            'smtp_password': os.getenv('SMTP_PASSWORD', ''),
            'from_email': os.getenv('SMTP_FROM_EMAIL', 'noreply@qualitascolombia.com.co'),
            'from_name': 'Sistema de Gestión de Inventarios'
        }

EMAIL_CONFIG = _load_email_config()

# ============================================================================
# COLORES Y ESTILOS COMPARTIDOS
# ============================================================================
ESTILOS = {
    'colores': {
        'primario': '#0d6efd',
        'primario_oscuro': '#0a58ca',
        'exito': '#198754',
        'peligro': '#dc3545',
        'advertencia': '#ffc107',
        'info': '#0dcaf0',
        'secundario': '#6c757d',
        'claro': '#f8f9fa',
        'oscuro': '#212529'
    },
    'estados_solicitud': {
        'Pendiente': {'color': '#ffc107', 'icono': '⏳', 'bg': '#fff3cd'},
        'Aprobada': {'color': '#198754', 'icono': '✅', 'bg': '#d1e7dd'},
        'Rechazada': {'color': '#dc3545', 'icono': '❌', 'bg': '#f8d7da'},
        'Entregada Parcial': {'color': '#0dcaf0', 'icono': '📦', 'bg': '#cff4fc'},
        'Completada': {'color': '#198754', 'icono': '✔️', 'bg': '#d1e7dd'},
        'Devuelta': {'color': '#6c757d', 'icono': '↩️', 'bg': '#e9ecef'},
        'Novedad Registrada': {'color': '#fd7e14', 'icono': '⚠️', 'bg': '#ffe5d0'},
        'Novedad Aceptada': {'color': '#198754', 'icono': '✅', 'bg': '#d1e7dd'},
        'Novedad Rechazada': {'color': '#dc3545', 'icono': '❌', 'bg': '#f8d7da'}
    },
    'estados_prestamo': {
        'PRESTADO': {'color': '#ffc107', 'icono': '📋', 'bg': '#fff3cd'},
        'APROBADO': {'color': '#198754', 'icono': '✅', 'bg': '#d1e7dd'},
        'APROBADO_PARCIAL': {'color': '#0dcaf0', 'icono': '📦', 'bg': '#cff4fc'},
        'RECHAZADO': {'color': '#dc3545', 'icono': '❌', 'bg': '#f8d7da'},
        'DEVUELTO': {'color': '#6c757d', 'icono': '↩️', 'bg': '#e9ecef'}
    }
}

# ============================================================================
# CLASE PRINCIPAL DE NOTIFICACIONES
# ============================================================================
class NotificationService:
    """Servicio unificado para enviar notificaciones por email"""
    
    # ========================================================================
    # MÉTODOS AUXILIARES SEGUROS
    # ========================================================================
    
    @staticmethod
    def _obtener_email_usuario(usuario_id):
        """Obtiene el email de un usuario por su ID de forma segura"""
        conn = get_database_connection()
        if not conn:
            return None
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT CorreoElectronico FROM Usuarios WHERE UsuarioId = ? AND Activo = 1",
                (usuario_id,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
        except Exception as e:
            # Log seguro usando sanitización
            logger.warning(f"No se pudo obtener email del usuario ID: {usuario_id}. Error: {type(e).__name__}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def _obtener_emails_aprobadores():
        """Obtiene los emails de todos los aprobadores activos de forma segura"""
        conn = get_database_connection()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT u.CorreoElectronico 
                FROM Aprobadores a
                INNER JOIN Usuarios u ON a.UsuarioId = u.UsuarioId
                WHERE a.Activo = 1 AND u.Activo = 1 AND u.CorreoElectronico IS NOT NULL
            """)
            emails = [row[0] for row in cursor.fetchall() if row[0]]
            # Log sanitizado
            logger.info(f"Se obtuvieron {len(emails)} emails de aprobadores")
            return emails
        except Exception as e:
            logger.warning(f"Error obteniendo emails de aprobadores: {type(e).__name__}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def _obtener_emails_gestores():
        """Obtiene emails de administradores y líderes de inventario de forma segura"""
        conn = get_database_connection()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT CorreoElectronico 
                FROM Usuarios 
                WHERE Activo = 1 
                AND CorreoElectronico IS NOT NULL
                AND Rol IN ('administrador', 'lider_inventario', 'Administrador', 'Lider_inventario')
            """)
            emails = [row[0] for row in cursor.fetchall() if row[0]]
            # Log sanitizado
            logger.info(f"Se obtuvieron {len(emails)} emails de gestores")
            return emails
        except Exception as e:
            logger.warning(f"Error obteniendo emails de gestores: {type(e).__name__}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def _generar_estilos_base():
        """Genera los estilos CSS base para todos los emails"""
        return f'''
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }}
            .header {{
                background: linear-gradient(135deg, {ESTILOS['colores']['primario']} 0%, {ESTILOS['colores']['primario_oscuro']} 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
            }}
            .content {{
                padding: 30px;
            }}
            .card {{
                background: {ESTILOS['colores']['claro']};
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
                border-left: 4px solid {ESTILOS['colores']['primario']};
            }}
            .detail-row {{
                display: flex;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid #eee;
            }}
            .detail-label {{
                color: #666;
                font-weight: 500;
            }}
            .detail-value {{
                font-weight: bold;
                color: #333;
            }}
            .badge {{
                display: inline-block;
                padding: 5px 15px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 14px;
            }}
            .footer {{
                background: #e9ecef;
                padding: 20px;
                text-align: center;
                font-size: 12px;
                color: #666;
            }}
            .btn {{
                display: inline-block;
                background: {ESTILOS['colores']['primario']};
                color: white;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 5px;
                margin-top: 20px;
                font-weight: bold;
            }}
        '''
    
    @staticmethod
    def _enviar_email(destinatario_email, asunto, contenido_html, contenido_texto):
        """Envía el email usando SMTP de forma segura"""
        if not EMAIL_CONFIG:
            logger.warning("⚠️ Configuración de email no disponible")
            return False
            
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = asunto
            msg['From'] = f'{EMAIL_CONFIG["from_name"]} <{EMAIL_CONFIG["from_email"]}>'
            msg['To'] = destinatario_email
            
            part1 = MIMEText(contenido_texto, 'plain', 'utf-8')
            part2 = MIMEText(contenido_html, 'html', 'utf-8')
            msg.attach(part1)
            msg.attach(part2)
            
            try:
                server = smtplib.SMTP_SSL(
                    EMAIL_CONFIG['smtp_server'], 
                    EMAIL_CONFIG['smtp_port'], 
                    timeout=30
                )
                
                # Autenticación si hay credenciales configuradas
                if EMAIL_CONFIG['smtp_user'] and EMAIL_CONFIG['smtp_password']:
                    server.login(EMAIL_CONFIG['smtp_user'], EMAIL_CONFIG['smtp_password'])
                    
            except smtplib.SMTPAuthenticationError:
                logger.warning("❌ Error de autenticación SMTP")
                # Fallback a SMTP normal
                server = smtplib.SMTP(
                    EMAIL_CONFIG['smtp_server'], 
                    EMAIL_CONFIG['smtp_port'], 
                    timeout=30
                )
                
                if EMAIL_CONFIG.get('use_tls', False):
                    try:
                        server.starttls()
                    except:
                        pass
                
                if EMAIL_CONFIG['smtp_user'] and EMAIL_CONFIG['smtp_password']:
                    server.login(EMAIL_CONFIG['smtp_user'], EMAIL_CONFIG['smtp_password'])
                    
            except smtplib.SMTPException as e:
                logger.error(f"❌ Error SMTP general: {type(e).__name__}")
                raise
                
            except Exception as e:
                logger.error(f"❌ Error inesperado en SMTP: {type(e).__name__}")
                raise
            
            server.sendmail(EMAIL_CONFIG['from_email'], destinatario_email, msg.as_string())
            server.quit()
            
            # Log seguro usando sanitización de helpers.py
            logger.info(f"✅ Email enviado a {sanitizar_email(destinatario_email)}")
            return True
            
        except Exception as e:
            # Log seguro usando sanitización
            error_type = type(e).__name__
            logger.warning(f"❌ Error enviando email a {sanitizar_email(destinatario_email)} ({error_type})")
            return False

    # ========================================================================
    # NOTIFICACIONES - INVENTARIO CORPORATIVO
    # ========================================================================
    
    @staticmethod
    def enviar_notificacion_asignacion(destinatario_email, destinatario_nombre, 
                                        producto_info, cantidad, oficina_nombre,
                                        asignador_nombre):
        """Envía notificación de asignación de producto del inventario corporativo"""
        fecha_actual = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        asunto = f'📦 Asignación de Inventario - {producto_info.get("nombre", "Producto")}'
        
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>{NotificationService._generar_estilos_base()}</style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📦 Nueva Asignación de Inventario</h1>
                </div>
                <div class="content">
                    <p>Hola <strong>{destinatario_nombre}</strong>,</p>
                    <p>Se te ha asignado el siguiente elemento del inventario corporativo:</p>
                    
                    <div class="card">
                        <h3 style="color: {ESTILOS['colores']['primario']}; margin-top: 0;">
                            {producto_info.get('nombre', 'Producto')}
                        </h3>
                        <div class="detail-row">
                            <span class="detail-label">Código:</span>
                            <span class="detail-value">{producto_info.get('codigo_unico', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Categoría:</span>
                            <span class="detail-value">{producto_info.get('categoria', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Cantidad Asignada:</span>
                            <span class="badge" style="background: {ESTILOS['colores']['exito']}; color: white;">
                                {cantidad} unidad(es)
                            </span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Oficina Destino:</span>
                            <span class="detail-value">{oficina_nombre}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Asignado por:</span>
                            <span class="detail-value">{asignador_nombre}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Fecha:</span>
                            <span class="detail-value">{fecha_actual}</span>
                        </div>
                    </div>
                    
                    <p style="color: #666;">
                        Por favor, confirma la recepción de este elemento con el área de inventario.
                    </p>
                </div>
                <div class="footer">
                    <p>Este es un mensaje automático del Sistema de Gestión de Inventarios.</p>
                    <p>Qualitas Colombia - {datetime.now().year}</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        texto = f'''
NUEVA ASIGNACIÓN DE INVENTARIO CORPORATIVO
==========================================

Hola {destinatario_nombre},

Se te ha asignado: {producto_info.get('nombre', 'Producto')}
Código: {producto_info.get('codigo_unico', 'N/A')}
Cantidad: {cantidad} unidad(es)
Oficina: {oficina_nombre}
Asignado por: {asignador_nombre}
Fecha: {fecha_actual}

---
Sistema de Gestión de Inventarios - Qualitas Colombia
        '''
        
        # Log seguro antes de enviar
        logger.info(f"Enviando notificación de asignación a {sanitizar_email(destinatario_email)}")
        
        return NotificationService._enviar_email(destinatario_email, asunto, html, texto)
    
    @staticmethod
    def enviar_notificacion_asignacion_con_confirmacion(destinatario_email, destinatario_nombre, 
                                                        producto_info, cantidad, oficina_nombre,
                                                        asignador_nombre, token_confirmacion=None,
                                                        base_url='http://localhost:5000'):
        """
        Envía notificación de asignación de producto con link de confirmación.
        """
        fecha_actual = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        # Generar link de confirmación si hay token
        link_confirmacion = None
        if token_confirmacion:
            link_confirmacion = f"{base_url}/confirmacion/confirmar-asignacion/{token_confirmacion}"
        
        asunto = f'📦 Asignación de Inventario - {producto_info.get("nombre", "Producto")}'
        
        # Construir el bloque de confirmación por separado
        bloque_confirmacion = ''
        if token_confirmacion and link_confirmacion:
            bloque_confirmacion = f'''
                    <div class="card" style="background: #fff3cd; border-left-color: #ffc107;">
                        <h4 style="color: #856404; margin-top: 0;">⚠️ ACCIÓN REQUERIDA</h4>
                        <p style="color: #856404; margin-bottom: 15px;">
                            Debe confirmar la recepción de este elemento dentro de los próximos <strong>8 días</strong>.
                        </p>
                        <center>
                            <a href="{link_confirmacion}" class="btn" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                                ✅ CONFIRMAR RECEPCIÓN
                            </a>
                        </center>
                        <p style="font-size: 12px; color: #666; margin-top: 15px; margin-bottom: 0;">
                            Si el botón no funciona, copie y pegue este enlace en su navegador:<br>
                            <a href="{link_confirmacion}" style="word-break: break-all;">{link_confirmacion}</a>
                        </p>
                    </div>
            '''
        else:
            bloque_confirmacion = '<p style="color: #666;">Por favor, confirma la recepción de este elemento con el área de inventario.</p>'
        
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>{NotificationService._generar_estilos_base()}</style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📦 Nueva Asignación de Inventario</h1>
                </div>
                <div class="content">
                    <p>Hola <strong>{destinatario_nombre}</strong>,</p>
                    <p>Se te ha asignado el siguiente elemento del inventario corporativo:</p>
                    
                    <div class="card">
                        <h3 style="color: {ESTILOS['colores']['primario']}; margin-top: 0;">
                            {producto_info.get('nombre', 'Producto')}
                        </h3>
                        <div class="detail-row">
                            <span class="detail-label">Código:</span>
                            <span class="detail-value">{producto_info.get('codigo_unico', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Categoría:</span>
                            <span class="detail-value">{producto_info.get('categoria', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Cantidad Asignada:</span>
                            <span class="badge" style="background: {ESTILOS['colores']['exito']}; color: white;">
                                {cantidad} unidad(es)
                            </span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Oficina Destino:</span>
                            <span class="detail-value">{oficina_nombre}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Asignado por:</span>
                            <span class="detail-value">{asignador_nombre}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Fecha:</span>
                            <span class="detail-value">{fecha_actual}</span>
                        </div>
                    </div>
                    
                    {bloque_confirmacion}
                    
                    <p style="color: #666; font-size: 14px; margin-top: 20px;">
                        Si tiene alguna pregunta o problema con esta asignación, 
                        por favor contacte al departamento de inventario.
                    </p>
                </div>
                <div class="footer">
                    <p>Este es un mensaje automático del Sistema de Gestión de Inventarios.</p>
                    <p>Qualitas Colombia - {datetime.now().year}</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        texto_confirmacion = ''
        if token_confirmacion and link_confirmacion:
            texto_confirmacion = f'''
IMPORTANTE: Debe confirmar la recepción dentro de los próximos 8 días.
Link de confirmación: {link_confirmacion}
'''
        
        texto = f'''
NUEVA ASIGNACIÓN DE INVENTARIO CORPORATIVO
==========================================

Hola {destinatario_nombre},

Se te ha asignado: {producto_info.get('nombre', 'Producto')}
Código: {producto_info.get('codigo_unico', 'N/A')}
Cantidad: {cantidad} unidad(es)
Oficina: {oficina_nombre}
Asignado por: {asignador_nombre}
Fecha: {fecha_actual}

{texto_confirmacion}
---
Sistema de Gestión de Inventarios - Qualitas Colombia
        '''
        
        # Log seguro antes de enviar
        logger.info(f"Enviando notificación de asignación con confirmación a {sanitizar_email(destinatario_email)}")
        
        return NotificationService._enviar_email(destinatario_email, asunto, html, texto)
    
    @staticmethod
    def enviar_notificacion_confirmacion_asignacion(asignacion_id, producto_nombre, 
                                                     usuario_nombre, usuario_email):
        """
        Envía notificación a los gestores cuando el usuario confirma la recepción.
        """
        emails_gestores = NotificationService._obtener_emails_gestores()
        
        if not emails_gestores:
            logger.warning("No hay gestores configurados para notificar confirmación")
            return False
        
        fecha_actual = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        asunto = f"✅ Confirmación de Recepción: {producto_nombre}"
        
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>{NotificationService._generar_estilos_base()}</style>
        </head>
        <body>
            <div class="container">
                <div class="header" style="background: linear-gradient(135deg, {ESTILOS['colores']['exito']} 0%, #146c43 100%);">
                    <h1>✅ Recepción Confirmada</h1>
                </div>
                <div class="content">
                    <p>Se ha confirmado la recepción del siguiente producto:</p>
                    
                    <div class="card" style="border-left-color: {ESTILOS['colores']['exito']};">
                        <div class="detail-row">
                            <span class="detail-label">Producto:</span>
                            <span class="detail-value">{producto_nombre}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Usuario:</span>
                            <span class="detail-value">{usuario_nombre}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Email:</span>
                            <span class="detail-value">{sanitizar_email(usuario_email)}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">ID Asignación:</span>
                            <span class="detail-value">#{asignacion_id}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Fecha de confirmación:</span>
                            <span class="badge" style="background: {ESTILOS['colores']['exito']}; color: white;">
                                {fecha_actual}
                            </span>
                        </div>
                    </div>
                    
                    <p style="color: #666;">
                        El usuario ha confirmado exitosamente la recepción del elemento asignado.
                    </p>
                </div>
                <div class="footer">
                    <p>Sistema de Gestión de Inventarios - Qualitas Colombia</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        texto = f'''
CONFIRMACIÓN DE RECEPCIÓN
=========================

Producto: {producto_nombre}
Usuario: {usuario_nombre}
Email: {sanitizar_email(usuario_email)}
ID Asignación: #{asignacion_id}
Fecha de confirmación: {fecha_actual}

El usuario ha confirmado exitosamente la recepción del elemento.

---
Sistema de Gestión de Inventarios - Qualitas Colombia
        '''
        
        exitos = 0
        # Log seguro del proceso
        logger.info(f"Enviando notificación de confirmación a {len(emails_gestores)} gestor(es)")
        
        for email in emails_gestores:
            if NotificationService._enviar_email(email, asunto, html, texto):
                exitos += 1
        
        # Log sanitizado del total de emails enviados
        logger.info(f"Notificación de confirmación enviada a {exitos} gestor(es)")
        return exitos > 0

    # ========================================================================
    # NOTIFICACIONES - MATERIAL POP (SOLICITUDES)
    # ========================================================================
    
    @staticmethod
    def notificar_solicitud_creada(solicitud_info):
        """Notifica a los aprobadores cuando se crea una nueva solicitud"""
        emails_aprobadores = NotificationService._obtener_emails_aprobadores()
        
        if not emails_aprobadores:
            logger.warning("No hay aprobadores configurados para notificar")
            return False
        
        fecha_actual = datetime.now().strftime('%d/%m/%Y %H:%M')
        estado_config = ESTILOS['estados_solicitud'].get('Pendiente', {})
        
        asunto = f'📋 Nueva Solicitud de Material - {solicitud_info.get("material_nombre", "Material")}'
        
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>{NotificationService._generar_estilos_base()}</style>
        </head>
        <body>
            <div class="container">
                <div class="header" style="background: linear-gradient(135deg, {estado_config.get('color', '#ffc107')} 0%, #e0a800 100%);">
                    <h1>📋 Nueva Solicitud de Material</h1>
                </div>
                <div class="content">
                    <p>Se ha creado una nueva solicitud que requiere su aprobación:</p>
                    
                    <div class="card" style="border-left-color: {estado_config.get('color', '#ffc107')};">
                        <div class="detail-row">
                            <span class="detail-label">Material:</span>
                            <span class="detail-value">{solicitud_info.get('material_nombre', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Cantidad Solicitada:</span>
                            <span class="badge" style="background: {ESTILOS['colores']['primario']}; color: white;">
                                {solicitud_info.get('cantidad_solicitada', 0)} unidades
                            </span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Oficina Solicitante:</span>
                            <span class="detail-value">{solicitud_info.get('oficina_nombre', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Solicitante:</span>
                            <span class="detail-value">{solicitud_info.get('usuario_solicitante', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Estado:</span>
                            <span class="badge" style="background: {estado_config.get('bg', '#fff3cd')}; color: {estado_config.get('color', '#856404')};">
                                ⏳ Pendiente de Aprobación
                            </span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Fecha:</span>
                            <span class="detail-value">{fecha_actual}</span>
                        </div>
                    </div>
                    
                    <p style="color: #666;">
                        Por favor, revise y procese esta solicitud a la brevedad.
                    </p>
                </div>
                <div class="footer">
                    <p>Sistema de Gestión de Inventarios - Qualitas Colombia</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        texto = f'''
NUEVA SOLICITUD DE MATERIAL
===========================

Material: {solicitud_info.get('material_nombre', 'N/A')}
Cantidad: {solicitud_info.get('cantidad_solicitada', 0)} unidades
Oficina: {solicitud_info.get('oficina_nombre', 'N/A')}
Solicitante: {solicitud_info.get('usuario_solicitante', 'N/A')}
Estado: Pendiente de Aprobación
Fecha: {fecha_actual}

---
Sistema de Gestión de Inventarios - Qualitas Colombia
        '''
        
        exitos = 0
        # Log seguro del proceso
        logger.info(f"Enviando notificación de nueva solicitud a {len(emails_aprobadores)} aprobador(es)")
        
        for email in emails_aprobadores:
            if NotificationService._enviar_email(email, asunto, html, texto):
                exitos += 1
        
        # Log sanitizado
        logger.info(f"Notificación de nueva solicitud enviada a {exitos} aprobador(es)")
        return exitos > 0

    @staticmethod
    def notificar_cambio_estado_solicitud(solicitud_info, estado_anterior, estado_nuevo, 
                                           usuario_accion, observacion=''):
        """Notifica al solicitante cuando cambia el estado de su solicitud"""
        
        email_destino = solicitud_info.get('email_solicitante')
        
        if not email_destino:
            logger.warning(f"No se encontró email para notificar solicitud {solicitud_info.get('id')}")
            return False
        
        fecha_actual = datetime.now().strftime('%d/%m/%Y %H:%M')
        estado_config = ESTILOS['estados_solicitud'].get(estado_nuevo, {})
        
        asunto = f'{estado_config.get("icono", "📋")} Solicitud {estado_nuevo} - {solicitud_info.get("material_nombre", "Material")}'
        
        observacion_html = f'<div class="detail-row"><span class="detail-label">Observación:</span><span class="detail-value">{observacion}</span></div>' if observacion else ''
        
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>{NotificationService._generar_estilos_base()}</style>
        </head>
        <body>
            <div class="container">
                <div class="header" style="background: linear-gradient(135deg, {estado_config.get('color', ESTILOS['colores']['primario'])} 0%, {ESTILOS['colores']['primario_oscuro']} 100%);">
                    <h1>{estado_config.get('icono', '📋')} Solicitud {estado_nuevo}</h1>
                </div>
                <div class="content">
                    <p>Hola <strong>{solicitud_info.get('usuario_solicitante', '')}</strong>,</p>
                    <p>Tu solicitud de material ha cambiado de estado:</p>
                    
                    <div class="card" style="border-left-color: {estado_config.get('color', ESTILOS['colores']['primario'])};">
                        <div class="detail-row">
                            <span class="detail-label">Material:</span>
                            <span class="detail-value">{solicitud_info.get('material_nombre', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Cantidad:</span>
                            <span class="detail-value">{solicitud_info.get('cantidad_solicitada', 0)} unidades</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Estado Anterior:</span>
                            <span class="detail-value">{estado_anterior}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Nuevo Estado:</span>
                            <span class="badge" style="background: {estado_config.get('bg', '#e9ecef')}; color: {estado_config.get('color', '#333')};">
                                {estado_config.get('icono', '')} {estado_nuevo}
                            </span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Procesado por:</span>
                            <span class="detail-value">{usuario_accion}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Fecha:</span>
                            <span class="detail-value">{fecha_actual}</span>
                        </div>
                        {observacion_html}
                    </div>
                </div>
                <div class="footer">
                    <p>Sistema de Gestión de Inventarios - Qualitas Colombia</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        texto_observacion = f'\nObservación: {observacion}' if observacion else ''
        
        texto = f'''
ACTUALIZACIÓN DE SOLICITUD
==========================

Material: {solicitud_info.get('material_nombre', 'N/A')}
Cantidad: {solicitud_info.get('cantidad_solicitada', 0)} unidades
Estado Anterior: {estado_anterior}
Nuevo Estado: {estado_nuevo}
Procesado por: {usuario_accion}
Fecha: {fecha_actual}{texto_observacion}

---
Sistema de Gestión de Inventarios - Qualitas Colombia
        '''
        
        # Log seguro antes de enviar
        logger.info(f"Enviando notificación de cambio de estado a {sanitizar_email(email_destino)}")
        
        return NotificationService._enviar_email(email_destino, asunto, html, texto)

    @staticmethod
    def notificar_novedad_registrada(solicitud_info, novedad_info):
        """Notifica a los gestores cuando se registra una novedad"""
        emails_gestores = NotificationService._obtener_emails_gestores()
        
        if not emails_gestores:
            logger.warning("No hay gestores configurados para notificar novedad")
            return False
        
        fecha_actual = datetime.now().strftime('%d/%m/%Y %H:%M')
        
        asunto = f'⚠️ Nueva Novedad Registrada - Solicitud #{solicitud_info.get("id", "N/A")}'
        
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>{NotificationService._generar_estilos_base()}</style>
        </head>
        <body>
            <div class="container">
                <div class="header" style="background: linear-gradient(135deg, #fd7e14 0%, #e65c00 100%);">
                    <h1>⚠️ Nueva Novedad Registrada</h1>
                </div>
                <div class="content">
                    <p>Se ha registrado una novedad que requiere su atención:</p>
                    
                    <div class="card" style="border-left-color: #fd7e14;">
                        <div class="detail-row">
                            <span class="detail-label">Solicitud #:</span>
                            <span class="detail-value">{solicitud_info.get('id', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Material:</span>
                            <span class="detail-value">{solicitud_info.get('material_nombre', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Tipo de Novedad:</span>
                            <span class="badge" style="background: #ffe5d0; color: #fd7e14;">
                                {novedad_info.get('tipo', 'N/A')}
                            </span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Descripción:</span>
                            <span class="detail-value">{novedad_info.get('descripcion', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Cantidad Afectada:</span>
                            <span class="detail-value">{novedad_info.get('cantidad_afectada', 0)}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Registrado por:</span>
                            <span class="detail-value">{novedad_info.get('usuario_registra', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Fecha:</span>
                            <span class="detail-value">{fecha_actual}</span>
                        </div>
                    </div>
                    
                    <p style="color: #666;">
                        Por favor, revise y gestione esta novedad.
                    </p>
                </div>
                <div class="footer">
                    <p>Sistema de Gestión de Inventarios - Qualitas Colombia</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        texto = f'''
NUEVA NOVEDAD REGISTRADA
========================

Solicitud #: {solicitud_info.get('id', 'N/A')}
Material: {solicitud_info.get('material_nombre', 'N/A')}
Tipo: {novedad_info.get('tipo', 'N/A')}
Descripción: {novedad_info.get('descripcion', 'N/A')}
Cantidad Afectada: {novedad_info.get('cantidad_afectada', 0)}
Registrado por: {novedad_info.get('usuario_registra', 'N/A')}

---
Sistema de Gestión de Inventarios - Qualitas Colombia
        '''
        
        exitos = 0
        # Log seguro del proceso
        logger.info(f"Enviando notificación de novedad a {len(emails_gestores)} gestor(es)")
        
        for email in emails_gestores:
            if NotificationService._enviar_email(email, asunto, html, texto):
                exitos += 1
        
        # Log sanitizado
        logger.info(f"Notificación de novedad enviada a {exitos} gestor(es)")
        return exitos > 0

    # ========================================================================
    # NOTIFICACIONES - PRÉSTAMOS
    # ========================================================================
    
    @staticmethod
    def notificar_prestamo_creado(prestamo_info):
        """Notifica a los gestores cuando se crea un nuevo préstamo"""
        emails_gestores = NotificationService._obtener_emails_gestores()
        
        if not emails_gestores:
            logger.warning("No hay gestores configurados para notificar préstamo")
            return False
        
        fecha_actual = datetime.now().strftime('%d/%m/%Y %H:%M')
        estado_config = ESTILOS['estados_prestamo'].get('PRESTADO', {})
        
        asunto = f'📋 Nuevo Préstamo Solicitado - {prestamo_info.get("material", "Material")}'
        
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>{NotificationService._generar_estilos_base()}</style>
        </head>
        <body>
            <div class="container">
                <div class="header" style="background: linear-gradient(135deg, {estado_config.get('color', '#ffc107')} 0%, #e0a800 100%);">
                    <h1>📋 Nuevo Préstamo Solicitado</h1>
                </div>
                <div class="content">
                    <p>Se ha registrado un nuevo préstamo que requiere aprobación:</p>
                    
                    <div class="card" style="border-left-color: {estado_config.get('color', '#ffc107')};">
                        <div class="detail-row">
                            <span class="detail-label">Elemento:</span>
                            <span class="detail-value">{prestamo_info.get('material', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Cantidad:</span>
                            <span class="badge" style="background: {ESTILOS['colores']['primario']}; color: white;">
                                {prestamo_info.get('cantidad', 0)} unidades
                            </span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Solicitante:</span>
                            <span class="detail-value">{prestamo_info.get('solicitante_nombre', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Oficina:</span>
                            <span class="detail-value">{prestamo_info.get('oficina_nombre', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Evento:</span>
                            <span class="detail-value">{prestamo_info.get('evento', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Fecha Devolución Prevista:</span>
                            <span class="detail-value">{prestamo_info.get('fecha_prevista', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Estado:</span>
                            <span class="badge" style="background: {estado_config.get('bg', '#fff3cd')}; color: {estado_config.get('color', '#856404')};">
                                📋 Pendiente de Aprobación
                            </span>
                        </div>
                    </div>
                </div>
                <div class="footer">
                    <p>Sistema de Gestión de Inventarios - Qualitas Colombia</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        texto = f'''
NUEVO PRÉSTAMO SOLICITADO
=========================

Elemento: {prestamo_info.get('material', 'N/A')}
Cantidad: {prestamo_info.get('cantidad', 0)} unidades
Solicitante: {prestamo_info.get('solicitante_nombre', 'N/A')}
Oficina: {prestamo_info.get('oficina_nombre', 'N/A')}
Evento: {prestamo_info.get('evento', 'N/A')}
Fecha Devolución Prevista: {prestamo_info.get('fecha_prevista', 'N/A')}

---
Sistema de Gestión de Inventarios - Qualitas Colombia
        '''
        
        exitos = 0
        # Log seguro del proceso
        logger.info(f"Enviando notificación de nuevo préstamo a {len(emails_gestores)} gestor(es)")
        
        for email in emails_gestores:
            if NotificationService._enviar_email(email, asunto, html, texto):
                exitos += 1
        
        # Log sanitizado
        logger.info(f"Notificación de nuevo préstamo enviada a {exitos} gestor(es)")
        return exitos > 0

    @staticmethod
    def notificar_cambio_estado_prestamo(prestamo_info, estado_nuevo, usuario_accion, observacion=''):
        """Notifica al solicitante cuando cambia el estado de su préstamo"""
        
        email_destino = prestamo_info.get('email_solicitante')
        
        if not email_destino:
            logger.warning(f"No se encontró email para notificar préstamo {prestamo_info.get('id')}")
            return False
        
        fecha_actual = datetime.now().strftime('%d/%m/%Y %H:%M')
        estado_config = ESTILOS['estados_prestamo'].get(estado_nuevo, {})
        
        asunto = f'{estado_config.get("icono", "📋")} Préstamo {estado_nuevo} - {prestamo_info.get("material", "Material")}'
        
        observacion_html = f'<div class="detail-row"><span class="detail-label">Observación:</span><span class="detail-value">{observacion}</span></div>' if observacion else ''
        
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>{NotificationService._generar_estilos_base()}</style>
        </head>
        <body>
            <div class="container">
                <div class="header" style="background: linear-gradient(135deg, {estado_config.get('color', ESTILOS['colores']['primario'])} 0%, {ESTILOS['colores']['primario_oscuro']} 100%);">
                    <h1>{estado_config.get('icono', '📋')} Préstamo {estado_nuevo}</h1>
                </div>
                <div class="content">
                    <p>Hola <strong>{prestamo_info.get('solicitante_nombre', '')}</strong>,</p>
                    <p>Tu préstamo ha sido actualizado:</p>
                    
                    <div class="card" style="border-left-color: {estado_config.get('color', ESTILOS['colores']['primario'])};">
                        <div class="detail-row">
                            <span class="detail-label">Elemento:</span>
                            <span class="detail-value">{prestamo_info.get('material', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Cantidad:</span>
                            <span class="detail-value">{prestamo_info.get('cantidad', 0)} unidades</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Nuevo Estado:</span>
                            <span class="badge" style="background: {estado_config.get('bg', '#e9ecef')}; color: {estado_config.get('color', '#333')};">
                                {estado_config.get('icono', '')} {estado_nuevo}
                            </span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Procesado por:</span>
                            <span class="detail-value">{usuario_accion}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Fecha:</span>
                            <span class="detail-value">{fecha_actual}</span>
                        </div>
                        {observacion_html}
                    </div>
                </div>
                <div class="footer">
                    <p>Sistema de Gestión de Inventarios - Qualitas Colombia</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        texto_observacion = f'\nObservación: {observacion}' if observacion else ''
        
        texto = f'''
ACTUALIZACIÓN DE PRÉSTAMO
=========================

Elemento: {prestamo_info.get('material', 'N/A')}
Cantidad: {prestamo_info.get('cantidad', 0)} unidades
Nuevo Estado: {estado_nuevo}
Procesado por: {usuario_accion}
Fecha: {fecha_actual}{texto_observacion}

---
Sistema de Gestión de Inventarios - Qualitas Colombia
        '''
        
        # Log seguro antes de enviar
        logger.info(f"Enviando notificación de cambio de estado de préstamo a {sanitizar_email(email_destino)}")
        
        return NotificationService._enviar_email(email_destino, asunto, html, texto)


# ============================================================================
# FUNCIONES DE CONVENIENCIA (compatibilidad con código existente)
# ============================================================================

def notificar_asignacion_inventario(destinatario_email, destinatario_nombre, 
                                     producto_info, cantidad, oficina_nombre, asignador_nombre):
    """Wrapper para compatibilidad con código existente"""
    return NotificationService.enviar_notificacion_asignacion(
        destinatario_email, destinatario_nombre, producto_info, 
        cantidad, oficina_nombre, asignador_nombre
    )

def notificar_solicitud(solicitud_info, tipo_notificacion, **kwargs):
    """
    Función genérica para notificar sobre solicitudes
    """
    if tipo_notificacion == 'creada':
        return NotificationService.notificar_solicitud_creada(solicitud_info)
    elif tipo_notificacion in ['aprobada', 'rechazada', 'entregada', 'devuelta']:
        return NotificationService.notificar_cambio_estado_solicitud(
            solicitud_info, 
            kwargs.get('estado_anterior', 'Pendiente'),
            tipo_notificacion.capitalize(),
            kwargs.get('usuario_accion', 'Sistema'),
            kwargs.get('observacion', '')
        )
    elif tipo_notificacion == 'novedad':
        return NotificationService.notificar_novedad_registrada(
            solicitud_info, 
            kwargs.get('novedad_info', {})
        )
    return False

def notificar_prestamo(prestamo_info, tipo_notificacion, **kwargs):
    """
    Función genérica para notificar sobre préstamos
    """
    if tipo_notificacion == 'creado':
        return NotificationService.notificar_prestamo_creado(prestamo_info)
    else:
        estado_map = {
            'aprobado': 'APROBADO',
            'aprobado_parcial': 'APROBADO_PARCIAL',
            'rechazado': 'RECHAZADO',
            'devuelto': 'DEVUELTO'
        }
        return NotificationService.notificar_cambio_estado_prestamo(
            prestamo_info,
            estado_map.get(tipo_notificacion, tipo_notificacion.upper()),
            kwargs.get('usuario_accion', 'Sistema'),
            kwargs.get('observacion', '')
        )


# ============================================================================
# FUNCIÓN PARA VERIFICAR DISPONIBILIDAD DEL SERVICIO
# ============================================================================

def servicio_notificaciones_disponible():
    """Verifica si el servicio de notificaciones está configurado correctamente"""
    return EMAIL_CONFIG is not None