# crear_usuario_test.py
from werkzeug.security import generate_password_hash
from database import get_database_connection

def crear_usuario_test():
    conn = get_database_connection()
    cursor = conn.cursor()
    
    # Usuario de prueba
    username = 'admin'
    password = 'admin123'
    password_hash = generate_password_hash(password)
    
    try:
        cursor.execute("""
            INSERT INTO usuarios (username, nombre, email, password_hash, rol, oficina_id, activo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (username, 'Administrador Test', 'admin@test.com', password_hash, 'administrador', 1, 1))
        
        conn.commit()
        print(f"✅ Usuario creado: {username} / {password}")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("El usuario probablemente ya existe")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    crear_usuario_test()