# blueprints/oficinas.py

from flask import Blueprint, render_template, request, redirect, session, flash, jsonify, url_for
from models.oficinas_model import OficinaModel
from utils.permissions import can_access
from utils.helpers import sanitizar_email, sanitizar_username, sanitizar_texto_generico
import logging

# Configurar logger especifico para este blueprint
logger = logging.getLogger(__name__)

oficinas_bp = Blueprint('oficinas', __name__, url_prefix='/oficinas')

def _require_login():
    return 'usuario_id' in session

@oficinas_bp.route('/')
def listar_oficinas():
    """Listar todas las oficinas"""
    logger.info("Accediendo a listar oficinas...")
    
    if not _require_login():
        logger.warning("Usuario no autenticado")
        return redirect('/login')
    
    if not can_access('oficinas', 'view'):
        logger.warning(f"Usuario {sanitizar_username(session.get('usuario', 'desconocido'))} sin permisos para ver oficinas")
        flash('No tienes permisos para acceder a esta seccion', 'danger')
        return redirect(url_for('auth.dashboard'))
    
    # Contexto con valores por defecto
    context = {
        'oficinas': [],
        'total_oficinas': 0,
        'oficinas_activas': 0
    }
    
    try:
        logger.info("Obteniendo oficinas desde el modelo...")
        oficinas = OficinaModel.obtener_todas()
        logger.info(f"Oficinas obtenidas: {len(oficinas) if oficinas else 0}")
        
        if oficinas:
            # Calcular estadisticas
            oficinas_activas = sum(1 for o in oficinas if o.get('activo', True))
            
            context.update({
                'oficinas': oficinas,
                'total_oficinas': len(oficinas),
                'oficinas_activas': oficinas_activas
            })
        
        logger.info("Renderizando template oficinas/listar.html")
        return render_template('oficinas/listar.html', **context)
        
    except Exception as e:
        logger.error(f"Error listando oficinas: {e}", exc_info=True)
        flash('Error al cargar las oficinas. Por favor, intente nuevamente.', 'danger')
        
        # Renderizar con valores por defecto
        return render_template('oficinas/listar.html', **context)

@oficinas_bp.route('/crear', methods=['GET', 'POST'])
def crear_oficina():
    """Crear una nueva oficina"""
    if not _require_login():
        return redirect('/login')
    
    if not can_access('oficinas', 'create'):
        flash('No tienes permisos para crear oficinas', 'danger')
        return redirect('/oficinas')
    
    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre')
            director = request.form.get('director')
            ubicacion = request.form.get('ubicacion')
            email = request.form.get('email')
            es_principal = bool(request.form.get('es_principal'))
            
            if not nombre or not director or not ubicacion:
                flash('Todos los campos obligatorios deben ser completados', 'danger')
                return render_template('oficinas/crear.html')
            
            oficina_id = OficinaModel.crear(
                nombre=nombre,
                director=director,
                ubicacion=ubicacion,
                email=email,
                es_principal=es_principal
            )
            
            if oficina_id:
                logger.info(f"Oficina creada: {sanitizar_texto_generico(nombre)} (ID: {oficina_id})")
                flash('Oficina creada exitosamente', 'success')
                return redirect('/oficinas')
            else:
                flash('Error al crear la oficina', 'danger')
                return render_template('oficinas/crear.html')
                
        except Exception as e:
            logger.error(f"Error al crear oficina: {e}", exc_info=True)
            flash('Error interno al crear la oficina', 'danger')
            return render_template('oficinas/crear.html')
    
    return render_template('oficinas/crear.html')

@oficinas_bp.route('/editar/<int:oficina_id>', methods=['GET', 'POST'])
def editar_oficina(oficina_id):
    """Editar una oficina existente"""
    if not _require_login():
        return redirect('/login')
    
    if not can_access('oficinas', 'edit'):
        flash('No tienes permisos para editar oficinas', 'danger')
        return redirect('/oficinas')
    
    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre')
            director = request.form.get('director')
            ubicacion = request.form.get('ubicacion')
            email = request.form.get('email')
            es_principal = bool(request.form.get('es_principal'))
            
            if not nombre or not director or not ubicacion:
                flash('Todos los campos obligatorios deben ser completados', 'danger')
                return redirect(f'/oficinas/editar/{oficina_id}')
            
            actualizado = OficinaModel.actualizar(
                oficina_id=oficina_id,
                nombre=nombre,
                director=director,
                ubicacion=ubicacion,
                email=email,
                es_principal=es_principal
            )
            
            if actualizado:
                logger.info(f"Oficina actualizada: ID {oficina_id}")
                flash('Oficina actualizada exitosamente', 'success')
            else:
                flash('Error al actualizar la oficina', 'danger')
                
            return redirect('/oficinas')
            
        except Exception as e:
            logger.error(f"Error al actualizar oficina {oficina_id}: {e}", exc_info=True)
            flash('Error interno al actualizar la oficina', 'danger')
            return redirect(f'/oficinas/editar/{oficina_id}')
    
    try:
        oficina = OficinaModel.obtener_por_id(oficina_id)
        if not oficina:
            flash('Oficina no encontrada', 'danger')
            return redirect('/oficinas')
        
        return render_template('oficinas/editar.html', oficina=oficina)
    except Exception as e:
        logger.error(f"Error al obtener oficina {oficina_id}: {e}", exc_info=True)
        flash('Error al cargar la oficina', 'danger')
        return redirect('/oficinas')

@oficinas_bp.route('/eliminar/<int:oficina_id>', methods=['POST'])
def eliminar_oficina(oficina_id):
    """Eliminar una oficina"""
    if not _require_login():
        return redirect('/login')
    
    if not can_access('oficinas', 'delete'):
        flash('No tienes permisos para eliminar oficinas', 'danger')
        return redirect('/oficinas')
    
    try:
        eliminado = OficinaModel.eliminar(oficina_id)
        if eliminado:
            logger.info(f"Oficina eliminada: ID {oficina_id}")
            flash('Oficina eliminada exitosamente', 'success')
        else:
            flash('Error al eliminar la oficina', 'danger')
    except Exception as e:
        logger.error(f"Error al eliminar oficina {oficina_id}: {e}", exc_info=True)
        flash('Error interno al eliminar la oficina', 'danger')
    
    return redirect('/oficinas')

@oficinas_bp.route('/api/oficinas')
def api_oficinas():
    """API para obtener todas las oficinas (para selectores)"""
    if not _require_login():
        return jsonify({'error': 'No autorizado'}), 401
    
    try:
        oficinas = OficinaModel.obtener_todas()
        oficinas_data = [{
            'id': oficina['id'],
            'nombre': oficina['nombre'],
            'director': oficina.get('director', ''),
            'ubicacion': oficina.get('ubicacion', '')
        } for oficina in oficinas]
        
        return jsonify(oficinas_data)
    except Exception as e:
        logger.error(f"Error en API oficinas: {e}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500

@oficinas_bp.route('/detalle/<int:oficina_id>')
def detalle_oficina(oficina_id):
    """Ver detalles de una oficina"""
    if not _require_login():
        return redirect('/login')
    
    if not can_access('oficinas', 'view'):
        flash('No tienes permisos para ver oficinas', 'danger')
        return redirect(url_for('auth.dashboard'))
    
    try:
        oficina = OficinaModel.obtener_por_id(oficina_id)
        if not oficina:
            flash('Oficina no encontrada', 'danger')
            return redirect('/oficinas')
        
        return render_template('oficinas/detalle.html', oficina=oficina)
    except Exception as e:
        logger.error(f"Error al obtener detalle de oficina {oficina_id}: {e}", exc_info=True)
        flash('Error al cargar los detalles de la oficina', 'danger')
        return redirect('/oficinas')

@oficinas_bp.route('/mi-inventario')
def mi_inventario():
    """Ver el inventario asignado a mi oficina - SOLO OFICINAS"""
    if not _require_login():
        return redirect('/login')
    
    # Solo para usuarios de oficina
    rol = session.get('rol', '').lower()
    if not rol.startswith('oficina_'):
        flash('Esta seccion es solo para oficinas', 'danger')
        return redirect(url_for('auth.dashboard'))
    
    try:
        from models.inventario_corporativo_model import InventarioCorporativoModel
        
        # Obtener la oficina del usuario
        oficina_codigo = session.get('oficina', '')
        
        # Obtener productos asignados a esta oficina
        productos = InventarioCorporativoModel.obtener_por_oficina(oficina_codigo)
        
        # Estadisticas
        total_productos = len(productos) if productos else 0
        valor_total = sum(p.get('ValorUnitario', 0) * p.get('Cantidad', 0) for p in productos) if productos else 0
        
        return render_template('oficinas/mi_inventario.html',
                             productos=productos,
                             total_productos=total_productos,
                             valor_total_inventario=valor_total,
                             oficina_codigo=oficina_codigo)
    except Exception as e:
        logger.error(f"Error al obtener inventario de oficina: {e}", exc_info=True)
        flash('Error al cargar el inventario', 'danger')
        return redirect(url_for('auth.dashboard'))