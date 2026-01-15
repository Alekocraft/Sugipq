import os
import shutil
import sys

def limpiar_cache_python():
    """
    Elimina todo el caché de Python (__pycache__, *.pyc, *.pyo)
    de forma recursiva desde el directorio actual.
    """
    directorio_actual = os.getcwd()
    print(f"Limpiando caché de Python en: {directorio_actual}")
    
    archivos_eliminados = 0
    directorios_eliminados = 0
    
    # Eliminar directorios __pycache__ de forma recursiva
    for root, dirs, files in os.walk(directorio_actual, topdown=False):
        # Eliminar directorios __pycache__
        if "__pycache__" in dirs:
            pycache_path = os.path.join(root, "__pycache__")
            try:
                shutil.rmtree(pycache_path)
                directorios_eliminados += 1
                print(f"✓ Eliminado: {pycache_path}")
            except Exception as e:
                print(f"✗ Error al eliminar {pycache_path}: {e}")
        
        # Eliminar archivos *.pyc y *.pyo
        for file in files:
            if file.endswith(".pyc") or file.endswith(".pyo"):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    archivos_eliminados += 1
                    print(f"✓ Eliminado: {file_path}")
                except Exception as e:
                    print(f"✗ Error al eliminar {file_path}: {e}")
    
    # Verificar que se eliminó todo
    print("\n" + "="*50)
    print("RESULTADO DE LA LIMPIEZA:")
    print(f"Directorios __pycache__ eliminados: {directorios_eliminados}")
    print(f"Archivos *.pyc/*.pyo eliminados: {archivos_eliminados}")
    
    # Verificar si quedan archivos __pycache__
    pycache_restantes = []
    for root, dirs, files in os.walk(directorio_actual):
        if "__pycache__" in dirs:
            pycache_restantes.append(os.path.join(root, "__pycache__"))
    
    if pycache_restantes:
        print("\n⚠ ¡ADVERTENCIA! Quedaron __pycache__ sin eliminar:")
        for path in pycache_restantes:
            print(f"  - {path}")
    else:
        print("\n✅ ¡Todo limpio! No hay directorios __pycache__ restantes.")

def main():
    """Función principal"""
    print("="*50)
    print("LIMPIADOR DE CACHÉ DE PYTHON")
    print("="*50)
    
    # Opcional: Cambiar al directorio específico (descomenta si lo necesitas)
    # directorio_objetivo = r"C:\Users\sinventarios\source\repos\sugipq"
    # os.chdir(directorio_objetivo)
    
    # Preguntar confirmación
    respuesta = input("\n¿Estás seguro de que quieres eliminar todo el caché de Python? (s/n): ")
    
    if respuesta.lower() in ['s', 'si', 'sí', 'y', 'yes']:
        limpiar_cache_python()
    else:
        print("\nOperación cancelada.")
    
    # Pausar antes de salir (solo en Windows)
    if sys.platform == "win32":
        input("\nPresiona Enter para salir...")

if __name__ == "__main__":
    main()