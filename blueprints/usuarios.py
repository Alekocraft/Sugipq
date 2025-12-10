# blueprints/usuarios.py
from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from functools import wraps
from models.usuarios_model import UsuarioModel
from database import get_database_connection
import logging

logger = logging.getLogger(__name__)

usuarios_bp = Blueprint('usuarios', __name__, url_prefix='/usuarios')

# Decorador para verificar permisos de administrador
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Debe iniciar sesión para acceder a esta página', 'danger')
            return redirect(url_for('auth.login'))
        
        if session['user'].get('rol') != 'admin':
            flash('No tiene permisos de administrador para acceder a esta página', 'danger')
            return redirect(url_for('dashboard.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

@usuarios_bp.route('/')
@admin_required
def listar_usuarios():
    """
    Lista todos los usuarios del sistema
    Solo accesible por administradores
    """
    try:
        conn = get_database_connection()
        if not conn:
            flash('Error de conexión a la base de datos', 'danger')
            return render_template('usuarios/listar.html', usuarios=[])
        
        cursor = conn.cursor()
        
        # Obtener usuarios con información de oficina
        cursor.execute("""
            SELECT 
                u.UsuarioId,
                u.NombreUsuario,
                u.CorreoElectronico,
                u.Rol,
                u.OficinaId,
                o.NombreOficina,
                u.Activo,
                u.FechaCreacion,
                u.AprobadorId,
                a.NombreAprobador
            FROM Usuarios u
            LEFT JOIN Oficinas o ON u.OficinaId = o.OficinaId
            LEFT JOIN Aprobadores a ON u.AprobadorId = a.AprobadorId
            ORDER BY u.NombreUsuario
        """)
        
        usuarios = []
        for row in cursor.fetchall():
            usuarios.append({
                'id': row[0],
                'usuario': row[1],
                'email': row[2],
                'rol': row[3],
                'oficina_id': row[4],
                'oficina_nombre': row[5],
                'activo': row[6],
                'fecha_creacion': row[7],
                'aprobador_id': row[8],
                'aprobador_nombre': row[9]
            })
        
        conn.close()
        
        # Obtener lista de oficinas para el formulario
        conn = get_database_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT OficinaId, NombreOficina FROM Oficinas WHERE Activo = 1 ORDER BY NombreOficina")
        oficinas = cursor.fetchall()
        
        # Obtener lista de aprobadores para el formulario
        cursor.execute("SELECT AprobadorId, NombreAprobador FROM Aprobadores WHERE Activo = 1 ORDER BY NombreAprobador")
        aprobadores = cursor.fetchall()
        
        conn.close()
        
        # Lista de roles disponibles
        roles_disponibles = [
            'admin',
            'tesoreria', 
            'oficina_polo_club',
            'oficina_coq',
            'aprobador',
            'usuario'
        ]
        
        return render_template('usuarios/listar.html', 
                             usuarios=usuarios,
                             oficinas=oficinas,
                             aprobadores=aprobadores,
                             roles=roles_disponibles)
        
    except Exception as e:
        logger.error(f"? Error listando usuarios: {e}")
        flash(f'Error al listar usuarios: {str(e)}', 'danger')
        return render_template('usuarios/listar.html', usuarios=[])

@usuarios_bp.route('/crear', methods=['GET', 'POST'])
@admin_required
def crear_usuario():
    """
    Crea un nuevo usuario manualmente
    """
    if request.method == 'GET':
        # Obtener datos para formulario
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Oficinas
        cursor.execute("SELECT OficinaId, NombreOficina FROM Oficinas WHERE Activo = 1 ORDER BY NombreOficina")
        oficinas = cursor.fetchall()
        
        # Aprobadores
        cursor.execute("SELECT AprobadorId, NombreAprobador FROM Aprobadores WHERE Activo = 1 ORDER BY NombreAprobador")
        aprobadores = cursor.fetchall()
        
        conn.close()
        
        # Roles disponibles
        roles_disponibles = [
            'admin',
            'tesoreria', 
            'oficina_polo_club',
            'oficina_coq',
            'aprobador',
            'usuario'
        ]
        
        return render_template('usuarios/crear.html',
                             oficinas=oficinas,
                             aprobadores=aprobadores,
                             roles=roles_disponibles)
    
    elif request.method == 'POST':
        try:
            # Obtener datos del formulario
            usuario_data = {
                'usuario': request.form.get('nombre_usuario'),
                'nombre': request.form.get('nombre_completo'),
                'email': request.form.get('email'),
                'rol': request.form.get('rol'),
                'password': request.form.get('password'),
                'oficina_id': request.form.get('oficina_id'),
                'aprobador_id': request.form.get('aprobador_id') or None,
                'activo': 1 if request.form.get('activo') == 'on' else 0
            }
            
            # Validaciones básicas
            if not usuario_data['usuario'] or not usuario_data['password']:
                flash('Usuario y contraseña son obligatorios', 'danger')
                return redirect(url_for('usuarios.crear_usuario'))
            
            # Verificar si el usuario ya existe
            conn = get_database_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM Usuarios WHERE NombreUsuario = ?", 
                          (usuario_data['usuario'],))
            if cursor.fetchone()[0] > 0:
                flash('El nombre de usuario ya existe', 'danger')
                conn.close()
                return redirect(url_for('usuarios.crear_usuario'))
            
            conn.close()
            
            # Crear usuario usando el modelo
            if UsuarioModel.crear_usuario_manual({
                'usuario': usuario_data['usuario'],
                'nombre': usuario_data['email'],  # Usar email como nombre
                'rol': usuario_data['rol'],
                'oficina_id': usuario_data['oficina_id'],
                'password': usuario_data['password']
            }):
                flash('Usuario creado exitosamente', 'success')
                # Si hay aprobador_id, actualizar la tabla
                if usuario_data['aprobador_id']:
                    conn = get_database_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE Usuarios 
                        SET AprobadorId = ?, 
                            CorreoElectronico = ?,
                            Activo = ?
                        WHERE NombreUsuario = ?
                    """, (
                        usuario_data['aprobador_id'],
                        usuario_data['email'],
                        usuario_data['activo'],
                        usuario_data['usuario']
                    ))
                    conn.commit()
                    conn.close()
                
                return redirect(url_for('usuarios.listar_usuarios'))
            else:
                flash('Error al crear el usuario', 'danger')
                return redirect(url_for('usuarios.crear_usuario'))
                
        except Exception as e:
            logger.error(f"? Error creando usuario: {e}")
            flash(f'Error al crear usuario: {str(e)}', 'danger')
            return redirect(url_for('usuarios.crear_usuario'))

@usuarios_bp.route('/editar/<int:usuario_id>', methods=['GET', 'POST'])
@admin_required
def editar_usuario(usuario_id):
    """
    Editar un usuario existente
    """
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        if request.method == 'GET':
            # Obtener datos del usuario
            cursor.execute("""
                SELECT 
                    UsuarioId,
                    NombreUsuario,
                    CorreoElectronico,
                    Rol,
                    OficinaId,
                    AprobadorId,
                    Activo
                FROM Usuarios 
                WHERE UsuarioId = ?
            """, (usuario_id,))
            
            usuario = cursor.fetchone()
            
            if not usuario:
                flash('Usuario no encontrado', 'danger')
                return redirect(url_for('usuarios.listar_usuarios'))
            
            # Obtener datos para formulario
            cursor.execute("SELECT OficinaId, NombreOficina FROM Oficinas WHERE Activo = 1 ORDER BY NombreOficina")
            oficinas = cursor.fetchall()
            
            cursor.execute("SELECT AprobadorId, NombreAprobador FROM Aprobadores WHERE Activo = 1 ORDER BY NombreAprobador")
            aprobadores = cursor.fetchall()
            
            # Roles disponibles
            roles_disponibles = [
                'admin',
                'tesoreria', 
                'oficina_polo_club',
                'oficina_coq',
                'aprobador',
                'usuario'
            ]
            
            conn.close()
            
            usuario_dict = {
                'id': usuario[0],
                'nombre_usuario': usuario[1],
                'email': usuario[2],
                'rol': usuario[3],
                'oficina_id': usuario[4],
                'aprobador_id': usuario[5],
                'activo': usuario[6]
            }
            
            return render_template('usuarios/editar.html',
                                 usuario=usuario_dict,
                                 oficinas=oficinas,
                                 aprobadores=aprobadores,
                                 roles=roles_disponibles)
        
        elif request.method == 'POST':
            # Actualizar usuario
            nuevo_rol = request.form.get('rol')
            nuevo_email = request.form.get('email')
            nueva_oficina = request.form.get('oficina_id')
            nuevo_aprobador = request.form.get('aprobador_id') or None
            nuevo_activo = 1 if request.form.get('activo') == 'on' else 0
            
            # Verificar que no estamos desactivando el último admin
            if nuevo_activo == 0 and nuevo_rol == 'admin':
                cursor.execute("""
                    SELECT COUNT(*) FROM Usuarios 
                    WHERE Rol = 'admin' AND Activo = 1 AND UsuarioId != ?
                """, (usuario_id,))
                
                if cursor.fetchone()[0] == 0:
                    flash('No se puede desactivar el último administrador activo', 'danger')
                    return redirect(url_for('usuarios.editar_usuario', usuario_id=usuario_id))
            
            # Actualizar usuario
            cursor.execute("""
                UPDATE Usuarios 
                SET Rol = ?,
                    CorreoElectronico = ?,
                    OficinaId = ?,
                    AprobadorId = ?,
                    Activo = ?
                WHERE UsuarioId = ?
            """, (
                nuevo_rol,
                nuevo_email,
                nueva_oficina,
                nuevo_aprobador,
                nuevo_activo,
                usuario_id
            ))
            
            conn.commit()
            conn.close()
            
            flash('Usuario actualizado exitosamente', 'success')
            return redirect(url_for('usuarios.listar_usuarios'))
            
    except Exception as e:
        logger.error(f"? Error editando usuario: {e}")
        flash(f'Error al editar usuario: {str(e)}', 'danger')
        return redirect(url_for('usuarios.listar_usuarios'))

@usuarios_bp.route('/cambiar-contrasena/<int:usuario_id>', methods=['POST'])
@admin_required
def cambiar_contrasena(usuario_id):
    """
    Cambiar contraseña de un usuario (solo admin)
    """
    try:
        nueva_contrasena = request.form.get('nueva_contrasena')
        confirmar_contrasena = request.form.get('confirmar_contrasena')
        
        if not nueva_contrasena:
            flash('La nueva contraseña es requerida', 'danger')
            return redirect(url_for('usuarios.editar_usuario', usuario_id=usuario_id))
        
        if nueva_contrasena != confirmar_contrasena:
            flash('Las contraseñas no coinciden', 'danger')
            return redirect(url_for('usuarios.editar_usuario', usuario_id=usuario_id))
        
        # Actualizar contraseña usando bcrypt
        import bcrypt
        password_hash = bcrypt.hashpw(
            nueva_contrasena.encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
        
        conn = get_database_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Usuarios 
            SET ContraseñaHash = ?
            WHERE UsuarioId = ?
        """, (password_hash, usuario_id))
        
        conn.commit()
        conn.close()
        
        flash('Contraseña actualizada exitosamente', 'success')
        return redirect(url_for('usuarios.listar_usuarios'))
        
    except Exception as e:
        logger.error(f"? Error cambiando contraseña: {e}")
        flash(f'Error al cambiar contraseña: {str(e)}', 'danger')
        return redirect(url_for('usuarios.editar_usuario', usuario_id=usuario_id))

@usuarios_bp.route('/eliminar/<int:usuario_id>', methods=['POST'])
@admin_required
def eliminar_usuario(usuario_id):
    """
    Eliminar usuario (desactivar)
    """
    try:
        # Verificar que no estamos eliminando el último admin
        conn = get_database_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT Rol FROM Usuarios WHERE UsuarioId = ?", (usuario_id,))
        usuario = cursor.fetchone()
        
        if usuario and usuario[0] == 'admin':
            cursor.execute("""
                SELECT COUNT(*) FROM Usuarios 
                WHERE Rol = 'admin' AND Activo = 1 AND UsuarioId != ?
            """, (usuario_id,))
            
            if cursor.fetchone()[0] == 0:
                flash('No se puede eliminar el último administrador activo', 'danger')
                return redirect(url_for('usuarios.listar_usuarios'))
        
        # Desactivar usuario (eliminación lógica)
        cursor.execute("""
            UPDATE Usuarios 
            SET Activo = 0
            WHERE UsuarioId = ?
        """, (usuario_id,))
        
        conn.commit()
        conn.close()
        
        flash('Usuario desactivado exitosamente', 'success')
        return redirect(url_for('usuarios.listar_usuarios'))
        
    except Exception as e:
        logger.error(f"? Error eliminando usuario: {e}")
        flash(f'Error al eliminar usuario: {str(e)}', 'danger')
        return redirect(url_for('usuarios.listar_usuarios'))

@usuarios_bp.route('/reactivar/<int:usuario_id>', methods=['POST'])
@admin_required
def reactivar_usuario(usuario_id):
    """
    Reactivar un usuario desactivado
    """
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Usuarios 
            SET Activo = 1
            WHERE UsuarioId = ?
        """, (usuario_id,))
        
        conn.commit()
        conn.close()
        
        flash('Usuario reactivado exitosamente', 'success')
        return redirect(url_for('usuarios.listar_usuarios'))
        
    except Exception as e:
        logger.error(f"? Error reactivando usuario: {e}")
        flash(f'Error al reactivar usuario: {str(e)}', 'danger')
        return redirect(url_for('usuarios.listar_usuarios'))