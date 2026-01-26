# -*- coding: utf-8 -*-
from flask import Blueprint, request, session, flash, redirect
from models.solicitudes_model import SolicitudModel
from utils.filters import verificar_acceso_oficina
import logging
from utils.helpers import sanitizar_log_text
# Importar servicio de notificaciones
try:
    from services.notification_service import NotificationService
    NOTIFICACIONES_ACTIVAS = True
except Exception:
    NOTIFICACIONES_ACTIVAS = False
    logging.getLogger(__name__).warning("⚠️ Servicio de notificaciones no disponible", exc_info=True)

from database import get_database_connection

def _obtener_info_solicitud_completa(solicitud_id: int):
    """Info completa para notificaciones (misma query que solicitudes.py)."""
    conn = get_database_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 
                sm.SolicitudId,
                m.NombreElemento as material_nombre,
                sm.CantidadSolicitada,
                sm.CantidadEntregada,
                o.NombreOficina as oficina_nombre,
                sm.UsuarioSolicitante,
                u.CorreoElectronico as email_solicitante,
                es.NombreEstado as estado
            FROM SolicitudesMaterial sm
            INNER JOIN Materiales m ON sm.MaterialId = m.MaterialId
            INNER JOIN Oficinas o ON sm.OficinaSolicitanteId = o.OficinaId
            LEFT JOIN Usuarios u ON sm.UsuarioSolicitante = u.NombreUsuario
            INNER JOIN EstadosSolicitud es ON sm.EstadoId = es.EstadoId
            WHERE sm.SolicitudId = ?
            """,
            (solicitud_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "material_nombre": row[1],
            "cantidad_solicitada": row[2],
            "cantidad_entregada": row[3],
            "oficina_nombre": row[4],
            "usuario_solicitante": row[5],
            "email_solicitante": row[6],
            "estado": row[7],
        }
    except Exception:
        logger.error("❌ Error obteniendo info solicitud para notificaciones: %s", sanitizar_log_text("Error interno"))
        return None
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


logger = logging.getLogger(__name__)

aprobacion_bp = Blueprint('aprobacion', __name__)

@aprobacion_bp.route('/solicitudes/aprobar/<int:solicitud_id>', methods=['POST'])
def aprobar_solicitud(solicitud_id):
    if 'usuario_id' not in session:
        return redirect('/login')

    rol = session.get('rol', '')
    if rol == 'tesorería':
        flash('No tiene permisos para acceder a esta sección.', 'danger')
        return redirect('/reportes')

    try:
        solicitud = SolicitudModel.obtener_por_id(solicitud_id)
        if not solicitud or not verificar_acceso_oficina(solicitud.get('oficina_id')):
            flash('No tiene permisos para aprobar esta solicitud.', 'danger')
            return redirect('/solicitudes')

        usuario_id = session['usuario_id']
        info_antes = _obtener_info_solicitud_completa(solicitud_id)
        estado_anterior = (info_antes or {}).get('estado', 'Pendiente')

        success, message = SolicitudModel.aprobar(solicitud_id, usuario_id)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')

        # Notificaciones
        if success and NOTIFICACIONES_ACTIVAS:
            try:
                info_despues = _obtener_info_solicitud_completa(solicitud_id) or info_antes
                estado_nuevo = (info_despues or {}).get('estado', 'Aprobada')
                NotificationService.notificar_cambio_estado_solicitud(
                    info_despues or {},
                    estado_anterior,
                    estado_nuevo,
                    usuario_gestion=session.get('usuario_nombre', session.get('usuario', 'Aprobador')),
                )
            except Exception:
                logger.warning('⚠️ No se pudo enviar notificación de aprobación', exc_info=True)
    except Exception as e:
        logger.error("❌ Error aprobando solicitud: %s", sanitizar_log_text('Error interno'))
        flash('Error al aprobar la solicitud.', 'danger')
    return redirect('/solicitudes')

@aprobacion_bp.route('/solicitudes/aprobar_parcial/<int:solicitud_id>', methods=['POST'])
def aprobar_parcial_solicitud(solicitud_id):
    if 'usuario_id' not in session:
        return redirect('/login')

    rol = session.get('rol', '')
    if rol == 'tesorería':
        flash('No tiene permisos para acceder a esta sección.', 'danger')
        return redirect('/reportes')

    try:
        solicitud = SolicitudModel.obtener_por_id(solicitud_id)
        if not solicitud or not verificar_acceso_oficina(solicitud.get('oficina_id')):
            flash('No tiene permisos para aprobar esta solicitud.', 'danger')
            return redirect('/solicitudes')

        usuario_id = session['usuario_id']
        cantidad_aprobada = int(request.form.get('cantidad_aprobada', 0))

        if cantidad_aprobada <= 0:
            flash('La cantidad aprobada debe ser mayor que 0.', 'danger')
            return redirect('/solicitudes')

        info_antes = _obtener_info_solicitud_completa(solicitud_id)
        estado_anterior = (info_antes or {}).get('estado', 'Pendiente')

        success, message = SolicitudModel.aprobar_parcial(solicitud_id, usuario_id, cantidad_aprobada)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')

        # Notificaciones
        if success and NOTIFICACIONES_ACTIVAS:
            try:
                info_despues = _obtener_info_solicitud_completa(solicitud_id) or info_antes
                estado_nuevo = (info_despues or {}).get('estado', 'Aprobación parcial')
                NotificationService.notificar_cambio_estado_solicitud(
                    info_despues or {},
                    estado_anterior,
                    estado_nuevo,
                    usuario_gestion=session.get('usuario_nombre', session.get('usuario', 'Aprobador')),
                    observaciones=f'Cantidad aprobada: {cantidad_aprobada}',
                )
            except Exception:
                logger.warning('⚠️ No se pudo enviar notificación de aprobación parcial', exc_info=True)
    except ValueError:
        flash('La cantidad aprobada debe ser un número válido.', 'danger')
    except Exception as e:
        logger.error("❌ Error aprobando parcialmente la solicitud: %s", sanitizar_log_text('Error interno'))
        flash('Error al aprobar parcialmente la solicitud.', 'danger')
    return redirect('/solicitudes')

@aprobacion_bp.route('/solicitudes/rechazar/<int:solicitud_id>', methods=['POST'])
def rechazar_solicitud(solicitud_id):
    if 'usuario_id' not in session:
        return redirect('/login')

    rol = session.get('rol', '')
    if rol == 'tesorería':
        flash('No tiene permisos para acceder a esta sección.', 'danger')
        return redirect('/reportes')

    try:
        solicitud = SolicitudModel.obtener_por_id(solicitud_id)
        if not solicitud or not verificar_acceso_oficina(solicitud.get('oficina_id')):
            flash('No tiene permisos para rechazar esta solicitud.', 'danger')
            return redirect('/solicitudes')

        usuario_id = session['usuario_id']
        info_antes = _obtener_info_solicitud_completa(solicitud_id)
        estado_anterior = (info_antes or {}).get('estado', 'Pendiente')
        observación = request.form.get('observación', '')
        rechazado = SolicitudModel.rechazar(solicitud_id, usuario_id, observación)
        if rechazado:
            flash('Solicitud rechazada exitosamente.', 'success')
        else:
            flash('Error al rechazar la solicitud.', 'danger')

        # Notificaciones
        if NOTIFICACIONES_ACTIVAS:
            try:
                info_despues = _obtener_info_solicitud_completa(solicitud_id) or info_antes
                # Si el modelo ya actualizó el estado, usamos ese; si no, forzamos 'Rechazada'
                estado_nuevo = (info_despues or {}).get('estado') or 'Rechazada'
                # Solo enviar notificación si realmente se rechazó
                if rechazado:
                    NotificationService.notificar_cambio_estado_solicitud(
                        info_despues or {},
                        estado_anterior,
                        estado_nuevo,
                        usuario_gestion=session.get('usuario_nombre', session.get('usuario', 'Aprobador')),
                        observaciones=observación or None,
                    )
            except Exception:
                logger.warning('⚠️ No se pudo enviar notificación de rechazo', exc_info=True)

    except Exception as e:
        logger.error("❌ Error rechazando solicitud: %s", sanitizar_log_text('Error interno'))
        flash('Error al rechazar la solicitud.', 'danger')
    return redirect('/solicitudes')