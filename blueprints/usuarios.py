# blueprints/usuarios.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
import logging
from models.usuarios_model import UsuarioModel
from models.oficinas_model import OficinaModel
from utils.permissions import can_access
from utils.helpers import sanitizar_username, sanitizar_email

logger = logging.getLogger(__name__)

usuarios_bp = Blueprint('usuarios', __name__)

try:
    from utils.ldap_consulta import ad_consulta
    CONSULTA_AD_DISPONIBLE = True
    logger.info("Módulo de consulta AD disponible")
except ImportError as e:
    CONSULTA_AD_DISPONIBLE = False
    logger.warning(f"Módulo de consulta AD no disponible: {e}")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Debe iniciar sesión para acceder', 'warning')
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('rol') != 'administrador':
            flash('No tiene permisos para gestionar usuarios', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Lista de roles actualizada con 15 oficinas
ROLES_LISTA = [
    {'value': 'administrador', 'label': 'Administrador'},
    {'value': 'lider_inventario', 'label': 'Líder de Inventario'},
    {'value': 'tesoreria', 'label': 'Tesorería'},
    {'value': 'aprobador', 'label': 'Aprobador'},
    {'value': 'oficina_pepe_sierra', 'label': 'Oficina Pepe Sierra'},
    {'value': 'oficina_polo_club', 'label': 'Oficina Polo Club'},
    {'value': 'oficina_nogal', 'label': 'Oficina Nogal'},
    {'value': 'oficina_morato', 'label': 'Oficina Morato'},
    {'value': 'oficina_cedritos', 'label': 'Oficina Cedritos'},
    {'value': 'oficina_coq', 'label': 'Oficina COQ'},
    {'value': 'oficina_lourdes', 'label': 'Oficina Lourdes'},
    {'value': 'oficina_kennedy', 'label': 'Oficina Kennedy'},
    {'value': 'oficina_principal', 'label': 'Oficina Principal'},
    {'value': 'oficina_cali', 'label': 'Oficina Cali'},
    {'value': 'oficina_medellin', 'label': 'Oficina Medellín'},
    {'value': 'oficina_pereira', 'label': 'Oficina Pereira'},
    {'value': 'oficina_bucaramanga', 'label': 'Oficina Bucaramanga'},
    {'value': 'oficina_cartagena', 'label': 'Oficina Cartagena'},
    {'value': 'oficina_tunja', 'label': 'Oficina Tunja'},
    {'value': 'oficina_neiva', 'label': 'Oficina Neiva'}
]

@usuarios_bp.route('/')
@login_required
@admin_required
def listar():
    try:
        usuarios = UsuarioModel.obtener_todos() or []
        total_usuarios = len(usuarios)
        total_activos = len([u for u in usuarios if u.get('activo', True)])
        total_inactivos = total_usuarios - total_activos
        total_ldap = len([u for u in usuarios if u.get('es_ldap', False)])
        total_locales = total_usuarios - total_ldap
        
        logger.info(f"Listado de usuarios consultado por {sanitizar_username(session.get('usuario', 'desconocido'))}")
        
        return render_template('usuarios/listar.html',
            usuarios=usuarios,
            total_usuarios=total_usuarios,
            total_activos=total_activos,
            total_inactivos=total_inactivos,
            total_ldap=total_ldap,
            total_locales=total_locales
        )
    except Exception as e:
        logger.error(f"Error listando usuarios: {e}")
        flash('Error al cargar usuarios', 'danger')
        return redirect(url_for('auth.dashboard'))

@usuarios_bp.route('/crear', methods=['GET', 'POST'])
@login_required
@admin_required
def crear():
    if request.method == 'POST':
        try:
            nombre_usuario = request.form.get('nombre_usuario', '').strip()
            nombre_completo = request.form.get('nombre_completo', '').strip()
            email = request.form.get('email', '').strip()
            rol = request.form.get('rol', '').strip()
            oficina_id = request.form.get('oficina_id')
            contraseña = request.form.get('contraseña', '').strip()
            contraseña_confirmar = request.form.get('contraseña_confirmar', '').strip()
            
            if not all([nombre_usuario, nombre_completo, email, rol, contraseña]):
                flash('Todos los campos son requeridos', 'danger')
                return redirect(request.url)
            
            if contraseña != contraseña_confirmar:
                flash('Las contraseñas no coinciden', 'danger')
                return redirect(request.url)
            
            if len(contraseña) < 6:
                flash('La contraseña debe tener al menos 6 caracteres', 'danger')
                return redirect(request.url)
            
            usuario_data = {
                'usuario': nombre_usuario,
                'email': email,
                'password': contraseña,
                'rol': rol,
                'oficina_id': int(oficina_id) if oficina_id else None
            }
            
            success = UsuarioModel.crear_usuario_manual(usuario_data)
            
            if success:
                flash('Usuario creado exitosamente', 'success')
                logger.info(f"Usuario creado: {sanitizar_username(nombre_usuario)} por {sanitizar_username(session.get('usuario'))}")
                return redirect(url_for('usuarios.listar'))
            else:
                flash('Error al crear usuario', 'danger')
                
        except Exception as e:
            logger.error(f"Error creando usuario: {e}")
            flash('Error al crear usuario', 'danger')
    
    try:
        oficinas = OficinaModel.obtener_todas() or []
    except:
        oficinas = []
    
    return render_template('usuarios/crear.html', oficinas=oficinas, roles=ROLES_LISTA)

@usuarios_bp.route('/crear-ldap', methods=['GET', 'POST'])
@login_required
@admin_required
def crear_ldap():
    if request.method == 'POST':
        try:
            nombre_usuario = request.form.get('nombre_usuario', '').strip()
            email = request.form.get('email', '').strip()
            rol = request.form.get('rol', '').strip()
            oficina_id = request.form.get('oficina_id')
            
            if not all([nombre_usuario, rol, oficina_id]):
                flash('Usuario, rol y oficina son requeridos', 'danger')
                return redirect(request.url)
            
            info_ad = None
            if CONSULTA_AD_DISPONIBLE:
                try:
                    info_ad = ad_consulta.buscar_usuario(nombre_usuario)
                    if info_ad and info_ad.get('encontrado'):
                        logger.info(f"Usuario encontrado en AD: {nombre_usuario}")
                        if not email and info_ad.get('email'):
                            email = info_ad['email']
                            flash(f'✓ Email obtenido del AD: {email}', 'info')
                        if info_ad.get('nombre_completo'):
                            flash(f'✓ Usuario encontrado en AD: {info_ad["nombre_completo"]}', 'success')
                    elif info_ad:
                        flash('⚠️ Usuario no encontrado en Active Directory. Verifique que exista.', 'warning')
                except Exception as e:
                    logger.error(f"Error consultando AD: {e}")
                    flash('⚠️ No se pudo consultar el AD. Continuando sin verificación.', 'warning')
            
            if not email:
                dominio = "qualitascolombia.com.co"
                email = f"{nombre_usuario}@{dominio}"
                flash(f'📧 Email generado: {email}', 'info')
            
            usuario_existente = UsuarioModel.obtener_por_usuario(nombre_usuario)
            if usuario_existente:
                flash(f'❌ El usuario {nombre_usuario} ya existe en el sistema', 'danger')
                return redirect(request.url)
            
            usuario_data = {
                'usuario': nombre_usuario,
                'email': email,
                'rol': rol,
                'oficina_id': int(oficina_id) if oficina_id else None
            }
            
            if info_ad and info_ad.get('nombre_completo'):
                usuario_data['nombre_completo'] = info_ad['nombre_completo']
            
            usuario_info = UsuarioModel.crear_usuario_ldap_manual(usuario_data)
            
            if usuario_info:
                mensaje = f'✅ Usuario LDAP pre-registrado: {nombre_usuario}. '
                mensaje += 'Deberá autenticarse con sus credenciales de dominio para activar su cuenta.'
                if info_ad and info_ad.get('nombre_completo'):
                    mensaje += f' (Nombre en AD: {info_ad["nombre_completo"]})'
                flash(mensaje, 'success')
                logger.info(f"Usuario LDAP pre-registrado: {nombre_usuario}")
                return redirect(url_for('usuarios.listar'))
            else:
                flash('❌ Error al crear usuario LDAP', 'danger')
        except Exception as e:
            logger.error(f"Error creando usuario LDAP: {e}")
            flash(f'Error: {str(e)}', 'danger')
    
    try:
        oficinas = OficinaModel.obtener_todas() or []
    except:
        oficinas = []
    
    return render_template('usuarios/crear_ldap.html', oficinas=oficinas, roles=ROLES_LISTA, consulta_ad_disponible=CONSULTA_AD_DISPONIBLE)

@usuarios_bp.route('/api/consultar-ad')
@login_required
@admin_required
def api_consultar_ad():
    try:
        usuario = request.args.get('usuario', '').strip()
        if not usuario:
            return jsonify({'error': 'Usuario requerido'}), 400
        if not CONSULTA_AD_DISPONIBLE:
            return jsonify({'consulta_disponible': False, 'mensaje': 'Consulta AD no disponible'})
        info_ad = None
        try:
            info_ad = ad_consulta.buscar_usuario(usuario)
        except Exception as e:
            logger.error(f"Error consultando AD para {usuario}: {e}")
        if info_ad and info_ad.get('encontrado'):
            return jsonify({
                'consulta_disponible': True,
                'encontrado': True,
                'nombre_completo': info_ad.get('nombre_completo', ''),
                'email': info_ad.get('email', ''),
                'departamento': info_ad.get('departamento', ''),
                'cargo': info_ad.get('cargo', '')
            })
        else:
            return jsonify({'consulta_disponible': True, 'encontrado': False, 'mensaje': 'Usuario no encontrado en Active Directory'})
    except Exception as e:
        logger.error(f"Error en API consultar AD: {e}")
        return jsonify({'error': str(e)}), 500

@usuarios_bp.route('/<int:usuario_id>/editar', methods=['GET', 'POST'])
@login_required
@admin_required
def editar(usuario_id):
    usuario = UsuarioModel.obtener_por_id(usuario_id)
    if not usuario:
        flash('Usuario no encontrado', 'danger')
        return redirect(url_for('usuarios.listar'))
    if request.method == 'POST':
        try:
            nombre_usuario = request.form.get('nombre_usuario', '').strip()
            email = request.form.get('email', '').strip()
            rol = request.form.get('rol', '').strip()
            oficina_id = request.form.get('oficina_id')
            activo = request.form.get('activo') == '1'
            if not all([nombre_usuario, email, rol]):
                flash('Todos los campos son requeridos', 'danger')
                return redirect(request.url)
            success = UsuarioModel.actualizar_usuario(usuario_id=usuario_id, usuario=nombre_usuario, email=email, rol=rol, oficina_id=int(oficina_id) if oficina_id else None, activo=activo)
            if success:
                flash('Usuario actualizado exitosamente', 'success')
                logger.info(f"Usuario actualizado: ID {usuario_id} por {sanitizar_username(session.get('usuario'))}")
                return redirect(url_for('usuarios.listar'))
            else:
                flash('Error al actualizar usuario', 'danger')
        except Exception as e:
            logger.error(f"Error actualizando usuario: {e}")
            flash('Error al actualizar usuario', 'danger')
    try:
        oficinas = OficinaModel.obtener_todas() or []
    except:
        oficinas = []
    return render_template('usuarios/editar.html', usuario=usuario, oficinas=oficinas, roles=ROLES_LISTA)

@usuarios_bp.route('/<int:usuario_id>/eliminar', methods=['POST'])
@login_required
@admin_required
def eliminar(usuario_id):
    try:
        if usuario_id == session.get('usuario_id'):
            return jsonify({'success': False, 'message': 'No puede eliminar su propio usuario'})
        success = UsuarioModel.desactivar_usuario(usuario_id)
        if success:
            logger.info(f"Usuario desactivado: ID {usuario_id} por {sanitizar_username(session.get('usuario'))}")
            return jsonify({'success': True, 'message': 'Usuario desactivado exitosamente'})
        else:
            return jsonify({'success': False, 'message': 'Error al desactivar usuario'})
    except Exception as e:
        logger.error(f"Error eliminando usuario: {e}")
        return jsonify({'success': False, 'message': 'Error al desactivar usuario'})

@usuarios_bp.route('/<int:usuario_id>/activar', methods=['POST'])
@login_required
@admin_required
def activar(usuario_id):
    try:
        success = UsuarioModel.activar_usuario(usuario_id)
        if success:
            logger.info(f"Usuario activado: ID {usuario_id} por {sanitizar_username(session.get('usuario'))}")
            return jsonify({'success': True, 'message': 'Usuario activado exitosamente'})
        else:
            return jsonify({'success': False, 'message': 'Error al activar usuario'})
    except Exception as e:
        logger.error(f"Error activando usuario: {e}")
        return jsonify({'success': False, 'message': 'Error al activar usuario'})

@usuarios_bp.route('/<int:usuario_id>/cambiar-password', methods=['POST'])
@login_required
def cambiar_password(usuario_id):
    try:
        if usuario_id != session.get('usuario_id') and session.get('rol') != 'administrador':
            return jsonify({'success': False, 'message': 'No tiene permisos para cambiar esta contraseña'})
        data = request.get_json() if request.is_json else request.form
        password_actual = data.get('password_actual', '').strip()
        password_nueva = data.get('password_nueva', '').strip()
        password_confirmar = data.get('password_confirmar', '').strip()
        if not all([password_actual, password_nueva, password_confirmar]):
            return jsonify({'success': False, 'message': 'Todos los campos son requeridos'})
        if password_nueva != password_confirmar:
            return jsonify({'success': False, 'message': 'Las contraseñas nuevas no coinciden'})
        if len(password_nueva) < 6:
            return jsonify({'success': False, 'message': 'La contraseña debe tener al menos 6 caracteres'})
        success = UsuarioModel.cambiar_contraseña(usuario_id=usuario_id, contraseña_actual=password_actual, contraseña_nueva=password_nueva)
        if success:
            logger.info(f"Contraseña cambiada para usuario ID {usuario_id}")
            return jsonify({'success': True, 'message': 'Contraseña actualizada exitosamente'})
        else:
            return jsonify({'success': False, 'message': 'Contraseña actual incorrecta'})
    except Exception as e:
        logger.error(f"Error cambiando contraseña: {e}")
        return jsonify({'success': False, 'message': 'Error al cambiar contraseña'})

@usuarios_bp.route('/<int:usuario_id>/resetear-password', methods=['POST'])
@login_required
@admin_required
def resetear_password(usuario_id):
    try:
        data = request.get_json() if request.is_json else request.form
        nueva_password = data.get('nueva_password', '').strip()
        if not nueva_password:
            return jsonify({'success': False, 'message': 'Debe proporcionar una nueva contraseña'})
        if len(nueva_password) < 6:
            return jsonify({'success': False, 'message': 'La contraseña debe tener al menos 6 caracteres'})
        success = UsuarioModel.resetear_contraseña(usuario_id, nueva_password)
        if success:
            logger.info(f"Contraseña reseteada para usuario ID {usuario_id} por {sanitizar_username(session.get('usuario'))}")
            return jsonify({'success': True, 'message': 'Contraseña reseteada exitosamente'})
        else:
            return jsonify({'success': False, 'message': 'Error al resetear contraseña'})
    except Exception as e:
        logger.error(f"Error reseteando contraseña: {e}")
        return jsonify({'success': False, 'message': 'Error al resetear contraseña'})

@usuarios_bp.route('/api/buscar')
@login_required
def api_buscar():
    try:
        termino = request.args.get('q', '').strip()
        if len(termino) < 2:
            return jsonify({'usuarios': []})
        usuarios = UsuarioModel.buscar_usuarios(termino) or []
        return jsonify({'success': True, 'usuarios': usuarios})
    except Exception as e:
        logger.error(f"Error buscando usuarios: {e}")
        return jsonify({'success': False, 'error': str(e)})

@usuarios_bp.route('/api/<int:usuario_id>')
@login_required
def api_obtener(usuario_id):
    try:
        usuario = UsuarioModel.obtener_por_id(usuario_id)
        if usuario:
            return jsonify({'success': True, 'usuario': usuario})
        else:
            return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    except Exception as e:
        logger.error(f"Error obteniendo usuario: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@usuarios_bp.route('/api/estadisticas')
@login_required
@admin_required
def api_estadisticas():
    try:
        usuarios = UsuarioModel.obtener_todos() or []
        stats = {
            'total': len(usuarios),
            'activos': len([u for u in usuarios if u.get('activo', True)]),
            'inactivos': len([u for u in usuarios if not u.get('activo', True)]),
            'ldap': len([u for u in usuarios if u.get('es_ldap', False)]),
            'locales': len([u for u in usuarios if not u.get('es_ldap', False)]),
            'por_rol': {}
        }
        for usuario in usuarios:
            rol = usuario.get('rol', 'sin_rol')
            stats['por_rol'][rol] = stats['por_rol'].get(rol, 0) + 1
        return jsonify({'success': True, 'estadisticas': stats})
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500