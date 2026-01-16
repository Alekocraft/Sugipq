# blueprints/inventario_corporativo.py

from flask import Blueprint, render_template, request, redirect, session, flash, jsonify, send_file
from werkzeug.utils import secure_filename
from models.inventario_corporativo_model import InventarioCorporativoModel
from utils.permissions import (
    can_access, 
    can_manage_inventario_corporativo, 
    can_view_inventario_actions,
    puede_solicitar_devolucion,    
    puede_solicitar_traspaso       
)
from utils.helpers import sanitizar_email, sanitizar_id, sanitizar_username
import os
import pandas as pd
from io import BytesIO
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

try:
    from utils.ldap_auth import ad_auth
    LDAP_AVAILABLE = True
except ImportError:
    LDAP_AVAILABLE = False
    logger.warning("LDAP no disponible - busqueda de usuarios AD deshabilitada")

try:
    from services.notification_service import NotificationService
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    logger.warning("Servicio de notificaciones no disponible")

try:
    from models.inventario_corporativo_model_extended import InventarioCorporativoModelExtended
    from models.confirmacion_asignaciones_model import ConfirmacionAsignacionesModel
    EXTENDED_MODEL_AVAILABLE = True
except ImportError:
    EXTENDED_MODEL_AVAILABLE = False
    logger.warning("Modelo extendido o de confirmaciones no disponible")

inventario_corporativo_bp = Blueprint(
    'inventario_corporativo',
    __name__,
    template_folder='templates'
)

def _require_login():
    return 'usuario_id' in session

def _handle_unauthorized():
    flash('No autorizado', 'danger')
    return redirect('/inventario-corporativo')

def _handle_not_found():
    flash('Producto no encontrado', 'danger')
    return redirect('/inventario-corporativo')

def _calculate_inventory_stats(productos):
    if not productos:
        return {
            'valor_total': 0,
            'productos_bajo_stock': 0,
            'productos_asignables': 0,
            'total_productos': 0
        }
    
    valor_total = sum(float(p.get('valor_unitario', 0)) * int(p.get('cantidad', 0)) for p in productos)
    productos_bajo_stock = len([p for p in productos if int(p.get('cantidad', 0)) <= int(p.get('cantidad_minima', 5))])
    productos_asignables = len([p for p in productos if p.get('es_asignable')])
    
    return {
        'valor_total': valor_total,
        'productos_bajo_stock': productos_bajo_stock,
        'productos_asignables': productos_asignables,
        'total_productos': len(productos)
    }

def _handle_image_upload(archivo, producto_actual=None):
    if not archivo or not archivo.filename:
        return producto_actual.get('ruta_imagen') if producto_actual else None
    
    filename = secure_filename(archivo.filename)
    upload_dir = os.path.join('static', 'uploads', 'productos')
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)
    archivo.save(filepath)
    return 'static/uploads/productos/' + filename

def _validate_product_form(categorias, proveedores):
    nombre = request.form.get('nombre', '').strip()
    categoria_id = request.form.get('categoria_id')
    proveedor_id = request.form.get('proveedor_id')
    
    errors = []
    
    if not nombre:
        errors.append('El nombre es requerido')
    
    if not categoria_id:
        errors.append('La categoria es requerida')
    
    if not proveedor_id:
        errors.append('El proveedor es requerido')
    
    return errors

@inventario_corporativo_bp.route('/')
def listar_inventario_corporativo():
    if not _require_login():
        return redirect('/login')

    if not can_access('inventario_corporativo', 'view'):
        return _handle_unauthorized()

    productos = InventarioCorporativoModel.obtener_todos_con_oficina() or []
    categorias = InventarioCorporativoModel.obtener_categorias() or []
    proveedores = InventarioCorporativoModel.obtener_proveedores() or []

    stats = _calculate_inventory_stats(productos)

    return render_template('inventario_corporativo/listar.html',
        productos=productos,
        categorias=categorias,
        proveedores=proveedores,
        total_productos=stats['total_productos'],
        valor_total_inventario=stats['valor_total'],
        productos_bajo_stock=stats['productos_bajo_stock'],
        productos_asignables=stats['productos_asignables'],
        puede_gestionar_inventario=can_manage_inventario_corporativo(),
        puede_ver_acciones_inventario=can_view_inventario_actions()
    )

@inventario_corporativo_bp.route('/sede-principal')
def listar_sede_principal():
    if not _require_login():
        return redirect('/login')

    if not can_access('inventario_corporativo', 'view'):
        return _handle_unauthorized()

    productos = InventarioCorporativoModel.obtener_por_sede_principal() or []
    categorias = InventarioCorporativoModel.obtener_categorias() or []
    proveedores = InventarioCorporativoModel.obtener_proveedores() or []

    stats = _calculate_inventory_stats(productos)

    return render_template('inventario_corporativo/listar_con_filtros.html',
        productos=productos,
        categorias=categorias,
        proveedores=proveedores,
        total_productos=stats['total_productos'],
        valor_total_inventario=stats['valor_total'],
        productos_bajo_stock=stats['productos_bajo_stock'],
        productos_asignables=stats['productos_asignables'],
        filtro_tipo='sede_principal',
        titulo='Inventario - Sede Principal (COQ)',
        puede_gestionar_inventario=can_manage_inventario_corporativo(),
        puede_ver_acciones_inventario=can_view_inventario_actions()
    )

@inventario_corporativo_bp.route('/oficinas-servicio')
def listar_oficinas_servicio():
    if not _require_login():
        return redirect('/login')

    if not can_access('inventario_corporativo', 'view'):
        return _handle_unauthorized()

    # Obtener TODOS los productos de oficinas
    productos = InventarioCorporativoModel.obtener_por_oficinas_servicio() or []
    
    # ✅ APLICAR FILTRO POR OFICINA DEL USUARIO
    from utils.filters import filtrar_por_oficina_usuario
    productos = filtrar_por_oficina_usuario(productos, campo_oficina_id='oficina_id')
    
    categorias = InventarioCorporativoModel.obtener_categorias() or []
    proveedores = InventarioCorporativoModel.obtener_proveedores() or []

    stats = _calculate_inventory_stats(productos)

    return render_template('inventario_corporativo/listar_con_filtros.html',
        productos=productos,
        categorias=categorias,
        proveedores=proveedores,
        total_productos=stats['total_productos'],
        valor_total_inventario=stats['valor_total'],
        productos_bajo_stock=stats['productos_bajo_stock'],
        productos_asignables=stats['productos_asignables'],
        filtro_tipo='oficinas_servicio',
        titulo='Inventario - Oficinas de Servicio',
        puede_gestionar_inventario=can_manage_inventario_corporativo(),
        puede_ver_acciones_inventario=can_view_inventario_actions(),
        puede_solicitar_devolucion=puede_solicitar_devolucion(),  # ✅ NUEVO
        puede_solicitar_traspaso=puede_solicitar_traspaso()        # ✅ NUEVO
    )

@inventario_corporativo_bp.route('/<int:producto_id>')
def ver_inventario_corporativo(producto_id):
    if not _require_login():
        return redirect('/login')

    if not can_access('inventario_corporativo', 'view'):
        return _handle_unauthorized()

    producto = InventarioCorporativoModel.obtener_por_id(producto_id)
    if not producto:
        return _handle_not_found()

    try:
        historial = InventarioCorporativoModel.historial_asignaciones(producto_id) or []
    except AttributeError:
        historial = []
        logger.warning("Metodo historial_movimientos no disponible")

    return render_template('inventario_corporativo/detalle.html',
        producto=producto,
        historial=historial
    )

@inventario_corporativo_bp.route('/crear', methods=['GET', 'POST'])
def crear_inventario_corporativo():
    if not _require_login():
        return redirect('/login')

    if not can_access('inventario_corporativo', 'create'):
        return _handle_unauthorized()

    categorias = InventarioCorporativoModel.obtener_categorias() or []
    proveedores = InventarioCorporativoModel.obtener_proveedores() or []

    if request.method == 'POST':
        errors = _validate_product_form(categorias, proveedores)
        if errors:
            for error in errors:
                flash(error, 'danger')
            return redirect(request.url)

        try:
            ruta_imagen = _handle_image_upload(request.files.get('imagen'))

            codigo_unico = request.form.get('codigo_unico')
            if not codigo_unico:
                codigo_unico = InventarioCorporativoModel.generar_codigo_unico()

            nuevo_id = InventarioCorporativoModel.crear(
                codigo_unico=codigo_unico,
                nombre=request.form.get('nombre'),
                descripcion=request.form.get('descripcion'),
                categoria_id=int(request.form.get('categoria_id')),
                proveedor_id=int(request.form.get('proveedor_id')),
                valor_unitario=float(request.form.get('valor_unitario', 0)),
                cantidad=int(request.form.get('cantidad', 0)),
                cantidad_minima=int(request.form.get('cantidad_minima', 0)),
                ubicacion=request.form.get('ubicacion', ''),
                es_asignable=1 if 'es_asignable' in request.form else 0,
                usuario_creador=session.get('usuario', 'Sistema'),
                ruta_imagen=ruta_imagen
            )

            if nuevo_id:
                flash('Producto creado correctamente.', 'success')
                return redirect('/inventario-corporativo')
            else:
                flash('Error al crear producto.', 'danger')

        except Exception as e:
            logger.error(f"[ERROR CREAR] {e}")
            flash('Error al crear producto.', 'danger')

    return render_template('inventario_corporativo/crear.html',
        categorias=categorias,
        proveedores=proveedores
    )

@inventario_corporativo_bp.route('/<int:producto_id>/editar', methods=['GET', 'POST'])
def editar_inventario_corporativo(producto_id):
    if not _require_login():
        return redirect('/login')

    if not can_access('inventario_corporativo', 'edit'):
        return _handle_unauthorized()

    producto = InventarioCorporativoModel.obtener_por_id(producto_id)
    if not producto:
        return _handle_not_found()

    categorias = InventarioCorporativoModel.obtener_categorias() or []
    proveedores = InventarioCorporativoModel.obtener_proveedores() or []

    if request.method == 'POST':
        errors = _validate_product_form(categorias, proveedores)
        if errors:
            for error in errors:
                flash(error, 'danger')
            return redirect(request.url)

        try:
            ruta_imagen = _handle_image_upload(request.files.get('imagen'), producto)

            actualizado = InventarioCorporativoModel.actualizar(
                producto_id=producto_id,
                codigo_unico=request.form.get('codigo_unico'),
                nombre=request.form.get('nombre'),
                descripcion=request.form.get('descripcion'),
                categoria_id=int(request.form.get('categoria_id')),
                proveedor_id=int(request.form.get('proveedor_id')),
                valor_unitario=float(request.form.get('valor_unitario', 0)),
                cantidad=int(request.form.get('cantidad', 0)),
                cantidad_minima=int(request.form.get('cantidad_minima', 0)),
                ubicacion=request.form.get('ubicacion', producto.get('ubicacion', '')),
                es_asignable=1 if 'es_asignable' in request.form else 0,
                ruta_imagen=ruta_imagen
            )

            if actualizado:
                flash('Producto actualizado correctamente.', 'success')
                return redirect(f'/inventario-corporativo/{producto_id}')
            else:
                flash('Error al actualizar producto.', 'danger')

        except Exception as e:
            logger.error(f"[ERROR EDITAR] {e}")
            flash('Error al actualizar producto.', 'danger')

    return render_template('inventario_corporativo/editar.html',
        producto=producto,
        categorias=categorias,
        proveedores=proveedores
    )

@inventario_corporativo_bp.route('/<int:producto_id>/eliminar', methods=['POST'])
def eliminar_inventario_corporativo(producto_id):
    if not _require_login():
        return redirect('/login')

    if not can_access('inventario_corporativo', 'delete'):
        return _handle_unauthorized()

    producto = InventarioCorporativoModel.obtener_por_id(producto_id)
    if not producto:
        return _handle_not_found()

    try:
        InventarioCorporativoModel.eliminar(producto_id, session.get('usuario', 'Sistema'))
        flash('Producto eliminado correctamente.', 'success')
    except Exception as e:
        logger.error(f"[ERROR ELIMINAR] {e}")
        flash('Error al eliminar producto.', 'danger')

    return redirect('/inventario-corporativo')

@inventario_corporativo_bp.route('/<int:producto_id>/asignar', methods=['GET', 'POST'])
def asignar_inventario_corporativo(producto_id):
    if not _require_login():
        return redirect('/login')

    if not can_access('inventario_corporativo', 'assign'):
        return _handle_unauthorized()

    producto = InventarioCorporativoModel.obtener_por_id(producto_id)
    if not producto:
        return _handle_not_found()

    if not producto.get('es_asignable'):
        flash('Este producto no es asignable.', 'warning')
        return redirect(f'/inventario-corporativo/{producto_id}')

    oficinas = InventarioCorporativoModel.obtener_oficinas() or []
    
    try:
        historial = InventarioCorporativoModel.historial_asignaciones(producto_id) or []
    except AttributeError:
        historial = []
        logger.warning("Metodo historial_asignaciones no disponible")

    if request.method == 'POST':
        try:
            oficina_id = int(request.form.get('oficina_id') or 0)
            cantidad_asignar = int(request.form.get('cantidad') or 0)
            
            usuario_ad_username = request.form.get('usuario_ad_username', '').strip()
            usuario_ad_nombre = request.form.get('usuario_ad_nombre', '').strip()
            usuario_ad_email = request.form.get('usuario_ad_email', '').strip()
            enviar_notificacion = request.form.get('enviar_notificacion') == 'on'

            if cantidad_asignar > producto.get('cantidad', 0):
                flash('No hay suficiente stock.', 'danger')
                return redirect(request.url)
            
            if not oficina_id:
                flash('Debe seleccionar una oficina.', 'danger')
                return redirect(request.url)

            oficina_nombre = next(
                (o['nombre'] for o in oficinas if o['id'] == oficina_id), 
                'Oficina'
            )

            usuario_ad_info = None
            if usuario_ad_username:
                usuario_ad_info = {
                    'username': usuario_ad_username,
                    'full_name': usuario_ad_nombre or usuario_ad_username,
                    'email': usuario_ad_email,
                    'department': ''
                }

            if usuario_ad_info and EXTENDED_MODEL_AVAILABLE:
                resultado = InventarioCorporativoModelExtended.asignar_a_usuario_ad_con_confirmacion(
                    producto_id=producto_id,
                    oficina_id=oficina_id,
                    cantidad=cantidad_asignar,
                    usuario_ad_info=usuario_ad_info,
                    usuario_accion=session.get('usuario', 'Sistema')
                )
                
                if resultado.get('success'):
                    flash('Producto asignado correctamente.', 'success')
                    
                    producto_info = {
                        'nombre': producto.get('nombre', 'Producto'),
                        'codigo_unico': producto.get('codigo_unico', 'N/A'),
                        'categoria': producto.get('categoria', 'N/A')
                    }
                    
                    if enviar_notificacion and usuario_ad_email and NOTIFICATIONS_AVAILABLE:
                        try:
                            base_url = os.getenv('APP_BASE_URL', request.url_root.rstrip('/'))
                            
                            exito_email = NotificationService.enviar_notificacion_asignacion_con_confirmacion(
                                destinatario_email=usuario_ad_email,
                                destinatario_nombre=usuario_ad_nombre or usuario_ad_username,
                                producto_info=producto_info,
                                cantidad=cantidad_asignar,
                                oficina_nombre=oficina_nombre,
                                asignador_nombre=session.get('usuario_nombre', session.get('usuario', 'Sistema')),
                                token_confirmacion=resultado.get('token'),
                                base_url=base_url
                            )
                            
                            if exito_email:
                                flash(f'Notificacion enviada a {usuario_ad_email}', 'info')
                                if resultado.get('token'):
                                    flash(f'Link de confirmacion generado (valido 8 dias)', 'info')
                            else:
                                flash('No se pudo enviar el email de notificacion', 'warning')
                                
                        except Exception as e:
                            logger.error(f"Error enviando notificacion: {e}")
                            flash('Producto asignado pero no se pudo enviar la notificacion.', 'warning')
                    else:
                        if not usuario_ad_email:
                            flash('No se envio notificacion: usuario sin email', 'info')
                    
                    return redirect(f'/inventario-corporativo/{producto_id}')
                else:
                    flash(resultado.get('message', 'No se pudo asignar el producto.'), 'danger')
            else:
                asignado = InventarioCorporativoModel.asignar_a_oficina(
                    producto_id=producto_id,
                    oficina_id=oficina_id,
                    cantidad=cantidad_asignar,
                    usuario_accion=session.get('usuario', 'Sistema')
                )

                if asignado:
                    flash('Producto asignado correctamente.', 'success')
                    return redirect(f'/inventario-corporativo/{producto_id}')
                else:
                    flash('No se pudo asignar el producto.', 'danger')

        except Exception as e:
            logger.error(f"[ERROR ASIGNAR] {e}")
            flash('Error al asignar producto.', 'danger')

    return render_template(
        'inventario_corporativo/asignar.html',
        producto=producto,
        oficinas=oficinas,
        historial=historial,
        ldap_disponible=LDAP_AVAILABLE
    )

@inventario_corporativo_bp.route('/api/buscar-usuarios-ad')
def api_buscar_usuarios_ad():
    if not _require_login():
        return jsonify({'error': 'No autorizado'}), 401
    
    if not LDAP_AVAILABLE:
        return jsonify({
            'error': 'Busqueda de usuarios AD no disponible',
            'usuarios': []
        }), 503

    termino = request.args.get('q', '').strip()
    
    if len(termino) < 3:
        return jsonify({
            'error': 'Ingrese al menos 3 caracteres para buscar',
            'usuarios': []
        })
    
    try:
        usuarios = ad_auth.search_user_by_name(termino)
        
        return jsonify({
            'success': True,
            'usuarios': usuarios,
            'total': len(usuarios)
        })
        
    except Exception as e:
        logger.error(f"Error buscando usuarios AD: {e}")
        return jsonify({
            'error': 'Error al buscar usuarios',
            'usuarios': []
        }), 500

@inventario_corporativo_bp.route('/api/obtener-usuario-ad/<username>')
def api_obtener_usuario_ad(username):
    if not _require_login():
        return jsonify({'error': 'No autorizado'}), 401
    
    if not LDAP_AVAILABLE:
        return jsonify({'error': 'LDAP no disponible'}), 503

    try:
        usuarios = ad_auth.search_user_by_name(username)
        
        usuario = next(
            (u for u in usuarios if u.get('usuario', '').lower() == username.lower()),
            None
        )
        
        if usuario:
            return jsonify({
                'success': True,
                'usuario': usuario
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Usuario no encontrado'
            }), 404
            
    except Exception as e:
        logger.error(f"Error obteniendo usuario AD: {e}")
        return jsonify({'error': 'Error al obtener usuario'}), 500

@inventario_corporativo_bp.route('/api/estadisticas-dashboard')
def api_estadisticas_dashboard():
    if not _require_login():
        return jsonify({'error': 'No autorizado'}), 401

    try:
        productos_todos = InventarioCorporativoModel.obtener_todos() or []
        productos_sede = InventarioCorporativoModel.obtener_por_sede_principal() or []
        productos_oficinas = InventarioCorporativoModel.obtener_por_oficinas_servicio() or []
        
        stats_todos = _calculate_inventory_stats(productos_todos)
        
        return jsonify({
            "total_productos": stats_todos['total_productos'],
            "valor_total": stats_todos['valor_total'],
            "stock_bajo": stats_todos['productos_bajo_stock'],
            "productos_sede": len(productos_sede),
            "productos_oficinas": len(productos_oficinas)
        })
        
    except Exception as e:
        logger.error(f"Error en API estadisticas dashboard: {e}")
        return jsonify({
            "total_productos": 0,
            "valor_total": 0,
            "stock_bajo": 0,
            "productos_sede": 0,
            "productos_oficinas": 0
        })

@inventario_corporativo_bp.route('/api/estadisticas')
def api_estadisticas_inventario():
    if not _require_login():
        return jsonify({'error': 'No autorizado'}), 401

    try:
        productos = InventarioCorporativoModel.obtener_todos_con_oficina() or []
        stats = _calculate_inventory_stats(productos)

        productos_sede = [p for p in productos if not p.get('oficina') or p.get('oficina') == 'Sede Principal']
        productos_oficinas = [p for p in productos if p.get('oficina') and p.get('oficina') != 'Sede Principal']
        
        return jsonify({
            "total_productos": stats['total_productos'],
            "valor_total": stats['valor_total'],
            "stock_bajo": stats['productos_bajo_stock'],
            "productos_sede": len(productos_sede),
            "productos_oficinas": len(productos_oficinas)
        })
        
    except Exception as e:
        logger.error(f"Error en API estadisticas: {e}")
        return jsonify({
            "total_productos": 0,
            "valor_total": 0,
            "stock_bajo": 0,
            "productos_sede": 0,
            "productos_oficinas": 0
        })

@inventario_corporativo_bp.route('/exportar/excel/<tipo>')
def exportar_inventario_corporativo_excel(tipo):
    if not _require_login():
        return redirect('/login')

    if not can_access('inventario_corporativo', 'view'):
        return _handle_unauthorized()

    productos = InventarioCorporativoModel.obtener_todos_con_oficina() or []
    df = pd.DataFrame(productos)

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(output, download_name='inventario_corporativo.xlsx', as_attachment=True)

# ===============================================
# Devoluciones, Bajas y Traspasos entre Oficinas  
# ===============================================

@inventario_corporativo_bp.route('/<int:producto_id>/solicitar-devolucion', methods=['GET', 'POST'])
def solicitar_devolucion_producto(producto_id):
    """
    Solicitar devoluciÃƒÂ³n de un producto asignado a una oficina.
    Disponible para: oficinas que tienen el producto asignado
    """
    if not _require_login():
        return redirect('/login')
    
    if not can_access('inventario_corporativo', 'view'):
        return _handle_unauthorized()
    
    # Obtener informaciÃ³n del producto
    producto = InventarioCorporativoModel.obtener_por_id(producto_id)
    if not producto:
        return _handle_not_found()
    
    # Obtener oficinas (para seleccionar cuÃ¡l devuelve)
    oficinas = InventarioCorporativoModel.obtener_oficinas() or []
    
    if request.method == 'POST':
        try:
            oficina_id = request.form.get('oficina_id')
            cantidad = request.form.get('cantidad')
            motivo = request.form.get('motivo', '').strip()
            
            if not all([oficina_id, cantidad, motivo]):
                flash('Todos los campos son requeridos', 'danger')
                return render_template('inventario_corporativo/solicitar_devolucion.html',
                                     producto=producto, oficinas=oficinas)
            
            # Solicitar la devoluciÃ³n
            resultado = InventarioCorporativoModel.solicitar_devolucion(
                producto_id=producto_id,
                oficina_id=int(oficina_id),
                cantidad=int(cantidad),
                motivo=motivo,
                usuario_solicita=session.get('usuario', 'Sistema')
            )
            
            if resultado.get('success'):
                flash(resultado.get('message'), 'success')
                logger.info(f"DevoluciÃƒÂ³n solicitada: Producto {sanitizar_id(str(producto_id))}, por {sanitizar_username(session.get('usuario'))}")
                return redirect(f'/inventario-corporativo/{producto_id}')
            else:
                flash(resultado.get('message'), 'danger')
                
        except Exception as e:
            logger.error(f"Error en solicitar_devolucion_producto: {e}")
            flash('Error al solicitar devoluciÃƒÂ³n', 'danger')
    
    return render_template('inventario_corporativo/solicitar_devolucion.html',
                         producto=producto, oficinas=oficinas)


@inventario_corporativo_bp.route('/devoluciones-pendientes')
def listar_devoluciones_pendientes():
    """
    Ver todas las devoluciones pendientes de aprobaciÃƒÂ³n.
    Solo para: LÃƒÂ­der de Inventario, Administrador, Aprobador
    """
    if not _require_login():
        return redirect('/login')
    
    # Verificar permisos
    rol = session.get('rol', '').lower()
    if rol not in ['administrador', 'lider_inventario', 'aprobador']:
        flash('No tiene permisos para ver devoluciones pendientes', 'danger')
        return redirect('/inventario-corporativo')
    
    try:
        devoluciones = InventarioCorporativoModel.obtener_devoluciones_pendientes()
        logger.info(f"Devoluciones pendientes consultadas por {sanitizar_username(session.get('usuario'))}")
        
        return render_template('inventario_corporativo/devoluciones_pendientes.html',
                             devoluciones=devoluciones)
    except Exception as e:
        logger.error(f"Error en listar_devoluciones_pendientes: {e}")
        flash('Error al cargar devoluciones', 'danger')
        return redirect('/inventario-corporativo')


@inventario_corporativo_bp.route('/devolucion/<int:devolucion_id>/aprobar', methods=['POST'])
def aprobar_devolucion(devolucion_id):
    """
    Aprobar una devoluciÃƒÂ³n y devolver el stock al inventario.
    Solo: LÃƒÂ­der de Inventario, Administrador, Aprobador
    """
    if not _require_login():
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    # Verificar permisos
    rol = session.get('rol', '').lower()
    if rol not in ['administrador', 'lider_inventario', 'aprobador']:
        return jsonify({'success': False, 'message': 'Sin permisos para aprobar devoluciones'}), 403
    
    try:
        observaciones = request.form.get('observaciones', '')
        usuario_aprueba = session.get('usuario', 'Sistema')
        
        resultado = InventarioCorporativoModel.aprobar_devolucion(
            devolucion_id=devolucion_id,
            usuario_aprueba=usuario_aprueba,
            observaciones=observaciones
        )
        
        if resultado.get('success'):
            logger.info(f"DevoluciÃƒÂ³n aprobada: ID {sanitizar_id(str(devolucion_id))}, por {sanitizar_username(usuario_aprueba)}")
            
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en aprobar_devolucion: {e}")
        return jsonify({'success': False, 'message': 'Error al aprobar devoluciÃƒÂ³n'}), 500


@inventario_corporativo_bp.route('/devolucion/<int:devolucion_id>/rechazar', methods=['POST'])
def rechazar_devolucion(devolucion_id):
    """
    Rechazar una devoluciÃƒÂ³n.
    Solo: LÃƒÂ­der de Inventario, Administrador, Aprobador
    """
    if not _require_login():
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    # Verificar permisos
    rol = session.get('rol', '').lower()
    if rol not in ['administrador', 'lider_inventario', 'aprobador']:
        return jsonify({'success': False, 'message': 'Sin permisos para rechazar devoluciones'}), 403
    
    try:
        motivo_rechazo = request.form.get('motivo_rechazo', '').strip()
        usuario_rechaza = session.get('usuario', 'Sistema')
        
        if not motivo_rechazo:
            return jsonify({'success': False, 'message': 'El motivo de rechazo es requerido'}), 400
        
        resultado = InventarioCorporativoModel.rechazar_devolucion(
            devolucion_id=devolucion_id,
            usuario_rechaza=usuario_rechaza,
            motivo_rechazo=motivo_rechazo
        )
        
        if resultado.get('success'):
            logger.info(f"DevoluciÃƒÂ³n rechazada: ID {sanitizar_id(str(devolucion_id))}, por {sanitizar_username(usuario_rechaza)}")
            
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en rechazar_devolucion: {e}")
        return jsonify({'success': False, 'message': 'Error al rechazar devoluciÃƒÂ³n'}), 500

# ==================== BAJAS DE PRODUCTOS ====================


@inventario_corporativo_bp.route('/productos-devueltos')
def listar_productos_devueltos():
    """
    Ver productos en estado DEVUELTO que pueden ser dados de baja.
    Solo para: LÃƒÂ­der de Inventario
    """
    if not _require_login():
        return redirect('/login')
    
     
    if session.get('rol', '').lower() != 'lider_inventario':
        flash('Solo el LÃƒÂ­der de Inventario puede dar de baja productos', 'danger')
        return redirect('/inventario-corporativo')
    
    try:
        productos_devueltos = InventarioCorporativoModel.obtener_productos_devueltos()
        logger.info(f"Productos devueltos consultados por {sanitizar_username(session.get('usuario'))}")
        
        return render_template('inventario_corporativo/productos_devueltos.html',
                             productos=productos_devueltos)
    except Exception as e:
        logger.error(f"Error en listar_productos_devueltos: {e}")
        flash('Error al cargar productos devueltos', 'danger')
        return redirect('/inventario-corporativo')


@inventario_corporativo_bp.route('/producto/<int:producto_id>/dar-de-baja', methods=['POST'])
def dar_de_baja_producto(producto_id):
    """
    Dar de baja un producto que estÃƒÂ¡ en estado DEVUELTO.
    Solo: LÃƒÂ­der de Inventario
    """
    if not _require_login():
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    
    if session.get('rol', '').lower() != 'lider_inventario':
        return jsonify({'success': False, 'message': 'Solo el LÃƒÂ­der de Inventario puede dar de baja productos'}), 403
    
    try:
        asignacion_id = request.form.get('asignacion_id')
        motivo = request.form.get('motivo', '').strip()
        usuario_accion = session.get('usuario', 'Sistema')
        
        if not all([asignacion_id, motivo]):
            return jsonify({'success': False, 'message': 'AsignaciÃƒÂ³n ID y motivo son requeridos'}), 400
        
        resultado = InventarioCorporativoModel.dar_de_baja_producto(
            producto_id=producto_id,
            asignacion_id=int(asignacion_id),
            motivo=motivo,
            usuario_accion=usuario_accion
        )
        
        if resultado.get('success'):
            logger.info(f"Producto dado de baja: ID {sanitizar_id(str(producto_id))}, por {sanitizar_username(usuario_accion)}")
            
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en dar_de_baja_producto: {e}")
        return jsonify({'success': False, 'message': 'Error al dar de baja el producto'}), 500

# ==================== TRASPASOS ENTRE OFICINAS ====================


@inventario_corporativo_bp.route('/<int:producto_id>/solicitar-traspaso', methods=['GET', 'POST'])
def solicitar_traspaso_producto(producto_id):
    """
    Solicitar traspaso de un producto de una oficina a otra.
    Disponible para: oficinas que tienen el producto asignado
    """
    if not _require_login():
        return redirect('/login')
    
    if not can_access('inventario_corporativo', 'view'):
        return _handle_unauthorized()
    
    # Obtener informaciÃ³n del producto
    producto = InventarioCorporativoModel.obtener_por_id(producto_id)
    if not producto:
        return _handle_not_found()
    
    # Obtener todas las oficinas
    oficinas = InventarioCorporativoModel.obtener_oficinas() or []
    
    if request.method == 'POST':
        try:
            oficina_origen_id = request.form.get('oficina_origen_id')
            oficina_destino_id = request.form.get('oficina_destino_id')
            cantidad = request.form.get('cantidad')
            motivo = request.form.get('motivo', '').strip()
            
            if not all([oficina_origen_id, oficina_destino_id, cantidad, motivo]):
                flash('Todos los campos son requeridos', 'danger')
                return render_template('inventario_corporativo/solicitar_traspaso.html',
                                     producto=producto, oficinas=oficinas)
            
            if oficina_origen_id == oficina_destino_id:
                flash('La oficina de origen y destino no pueden ser la misma', 'danger')
                return render_template('inventario_corporativo/solicitar_traspaso.html',
                                     producto=producto, oficinas=oficinas)
            
            # Solicitar el traspaso
            resultado = InventarioCorporativoModel.solicitar_traspaso(
                producto_id=producto_id,
                oficina_origen_id=int(oficina_origen_id),
                oficina_destino_id=int(oficina_destino_id),
                cantidad=int(cantidad),
                motivo=motivo,
                usuario_solicita=session.get('usuario', 'Sistema')
            )
            
            if resultado.get('success'):
                flash(resultado.get('message'), 'success')
                logger.info(f"Traspaso solicitado: Producto {sanitizar_id(str(producto_id))}, por {sanitizar_username(session.get('usuario'))}")
                return redirect(f'/inventario-corporativo/{producto_id}')
            else:
                flash(resultado.get('message'), 'danger')
                
        except Exception as e:
            logger.error(f"Error en solicitar_traspaso_producto: {e}")
            flash('Error al solicitar traspaso', 'danger')
    
    return render_template('inventario_corporativo/solicitar_traspaso.html',
                         producto=producto, oficinas=oficinas)


@inventario_corporativo_bp.route('/traspasos-pendientes')
def listar_traspasos_pendientes():
    """
    Ver todos los traspasos pendientes de aprobaciÃƒÂ³n.
    Solo para: LÃƒÂ­der de Inventario, Administrador, Aprobador
    """
    if not _require_login():
        return redirect('/login')
    
    # Verificar permisos
    rol = session.get('rol', '').lower()
    if rol not in ['administrador', 'lider_inventario', 'aprobador']:
        flash('No tiene permisos para ver traspasos pendientes', 'danger')
        return redirect('/inventario-corporativo')
    
    try:
        traspasos = InventarioCorporativoModel.obtener_traspasos_pendientes()
        logger.info(f"Traspasos pendientes consultados por {sanitizar_username(session.get('usuario'))}")
        
        return render_template('inventario_corporativo/traspasos_pendientes.html',
                             traspasos=traspasos)
    except Exception as e:
        logger.error(f"Error en listar_traspasos_pendientes: {e}")
        flash('Error al cargar traspasos', 'danger')
        return redirect('/inventario-corporativo')


@inventario_corporativo_bp.route('/traspaso/<int:traspaso_id>/aprobar', methods=['POST'])
def aprobar_traspaso(traspaso_id):
    """
    Aprobar un traspaso y realizar el cambio de oficina.
    Solo: LÃƒÂ­der de Inventario, Administrador, Aprobador
    """
    if not _require_login():
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    # Verificar permisos
    rol = session.get('rol', '').lower()
    if rol not in ['administrador', 'lider_inventario', 'aprobador']:
        return jsonify({'success': False, 'message': 'Sin permisos para aprobar traspasos'}), 403
    
    try:
        observaciones = request.form.get('observaciones', '')
        usuario_aprueba = session.get('usuario', 'Sistema')
        
        resultado = InventarioCorporativoModel.aprobar_traspaso(
            traspaso_id=traspaso_id,
            usuario_aprueba=usuario_aprueba,
            observaciones=observaciones
        )
        
        if resultado.get('success'):
            logger.info(f"Traspaso aprobado: ID {sanitizar_id(str(traspaso_id))}, por {sanitizar_username(usuario_aprueba)}")
            
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en aprobar_traspaso: {e}")
        return jsonify({'success': False, 'message': 'Error al aprobar traspaso'}), 500


@inventario_corporativo_bp.route('/traspaso/<int:traspaso_id>/rechazar', methods=['POST'])
def rechazar_traspaso(traspaso_id):
    """
    Rechazar un traspaso.
    Solo: LÃƒÂ­der de Inventario, Administrador, Aprobador
    """
    if not _require_login():
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    # Verificar permisos
    rol = session.get('rol', '').lower()
    if rol not in ['administrador', 'lider_inventario', 'aprobador']:
        return jsonify({'success': False, 'message': 'Sin permisos para rechazar traspasos'}), 403
    
    try:
        motivo_rechazo = request.form.get('motivo_rechazo', '').strip()
        usuario_rechaza = session.get('usuario', 'Sistema')
        
        if not motivo_rechazo:
            return jsonify({'success': False, 'message': 'El motivo de rechazo es requerido'}), 400
        
        resultado = InventarioCorporativoModel.rechazar_traspaso(
            traspaso_id=traspaso_id,
            usuario_rechaza=usuario_rechaza,
            motivo_rechazo=motivo_rechazo
        )
        
        if resultado.get('success'):
            logger.info(f"Traspaso rechazado: ID {sanitizar_id(str(traspaso_id))}, por {sanitizar_username(usuario_rechaza)}")
            
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en rechazar_traspaso: {e}")
        return jsonify({'success': False, 'message': 'Error al rechazar traspaso'}), 500

# ==================== VISTAS PARA OFICINAS ====================


@inventario_corporativo_bp.route('/mis-devoluciones')
def mis_devoluciones():
    """
    Ver las devoluciones de la oficina del usuario actual
    """
    if not _require_login():
        return redirect('/login')
    
    # Obtener la oficina del usuario
    oficina_id = session.get('oficina_id')
    if not oficina_id:
        flash('No se pudo determinar su oficina', 'danger')
        return redirect('/inventario-corporativo')
    
    try:
        devoluciones = InventarioCorporativoModel.obtener_devoluciones_por_oficina(oficina_id)
        logger.info(f"Devoluciones consultadas por oficina {sanitizar_id(str(oficina_id))}")
        
        return render_template('inventario_corporativo/mis_devoluciones.html',
                             devoluciones=devoluciones)
    except Exception as e:
        logger.error(f"Error en mis_devoluciones: {e}")
        flash('Error al cargar devoluciones', 'danger')
        return redirect('/inventario-corporativo')


@inventario_corporativo_bp.route('/mis-traspasos')
def mis_traspasos():
    """
    Ver los traspasos relacionados con la oficina del usuario actual
    """
    if not _require_login():
        return redirect('/login')
    
    # Obtener la oficina del usuario
    oficina_id = session.get('oficina_id')
    if not oficina_id:
        flash('No se pudo determinar su oficina', 'danger')
        return redirect('/inventario-corporativo')
    
    try:
        traspasos = InventarioCorporativoModel.obtener_traspasos_por_oficina(oficina_id)
        logger.info(f"Traspasos consultados por oficina {sanitizar_id(str(oficina_id))}")
        
        return render_template('inventario_corporativo/mis_traspasos.html',
                             traspasos=traspasos)
    except Exception as e:
        logger.error(f"Error en mis_traspasos: {e}")
        flash('Error al cargar traspasos', 'danger')
        return redirect('/inventario-corporativo')