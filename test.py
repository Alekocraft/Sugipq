import os
import re
import sys
from datetime import datetime
import msvcrt  # Para Windows, usar getch()

# Contadores globales
tests_passed = 0
tests_failed = 0
total_tests = 8

def print_header():
    """Imprime el encabezado del script"""
    print("=" * 40)
    print("🔍 VERIFICACIÓN DÍA 7 - SUGIPQ-V1")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 40)
    print()

def check_file(file_path, pattern, description, test_num):
    """Verifica si un archivo existe y contiene un patrón específico"""
    print(f"{test_num}️⃣  TEST: {description}")
    print("-" * 40)
    
    try:
        # Verificar si el archivo existe
        if not os.path.exists(file_path):
            print(f"❌ FALLIDO: Archivo no encontrado")
            print(f"   {file_path}")
            return False
        
        # Leer el contenido del archivo
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Buscar el patrón en el contenido
        matches = re.findall(pattern, content)
        
        if matches:
            print(f"✅ PASADO: {description}")
            return True
        else:
            print(f"❌ FALLIDO: {description}")
            print(f"   Archivo: {file_path}")
            print(f"   No se encontró el patrón esperado")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

def check_multiple_fields(file_path, pattern, description, test_num, min_count):
    """Verifica que haya al menos min_count ocurrencias de un patrón en un archivo"""
    print(f"{test_num}️⃣  TEST: {description}")
    print("-" * 40)
    
    try:
        # Verificar si el archivo existe
        if not os.path.exists(file_path):
            print(f"❌ FALLIDO: Archivo no encontrado")
            return False
        
        # Leer el contenido del archivo
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Contar ocurrencias del patrón
        matches = re.findall(pattern, content)
        count = len(matches)
        
        if count >= min_count:
            print(f"✅ PASADO: {description.split('-')[0]} tiene {count} campos con autocomplete")
            return True
        else:
            print(f"❌ FALLIDO: {description.split('-')[0]} solo tiene {count} campos (esperado: {min_count}+)")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

def run_test(test_func, *args):
    """Ejecuta un test y actualiza los contadores"""
    global tests_passed, tests_failed
    
    if test_func(*args):
        tests_passed += 1
    else:
        tests_failed += 1
    print()

def print_summary():
    """Imprime el resumen de los tests"""
    global tests_passed, tests_failed, total_tests
    
    print("=" * 40)
    print("📊 RESUMEN DE VERIFICACIÓN")
    print("=" * 40)
    print(f"Total de tests:  {total_tests}")
    print(f"Tests pasados:   {tests_passed}")
    print(f"Tests fallidos:  {tests_failed}")
    print()
    
    percentage = round((tests_passed / total_tests) * 100)
    color_code = "\033[92m" if percentage == 100 else "\033[93m"  # Verde o amarillo
    print(f"Porcentaje completado: {color_code}{percentage}%\033[0m")
    print()
    
    if tests_failed == 0:
        print("\033[92m🎉 ¡TODOS LOS TESTS PASARON!\033[0m")
        print()
        print("\033[96mPróximo paso:\033[0m")
        print("  git add templates/")
        print("  git commit -m '✅ Día 7 completado'")
        print("  git push")
    else:
        print("\033[93m⚠️  HAY TESTS FALLIDOS\033[0m")
        print("Revisar los tests marcados con ❌ y corregir")
        print()
        print("\033[96mConsultar:\033[0m")
        print("  - INSTRUCCIONES_DETALLADAS_DIA7.md")
        print("  - PLAN_DIA7_FORMULARIOS.md")

def wait_for_key():
    """Espera a que el usuario presione cualquier tecla"""
    print("\n\033[93mPresiona cualquier tecla para cerrar esta ventana...\033[0m")
    msvcrt.getch()  # Para Windows

def main():
    """Función principal del script"""
    global tests_passed, tests_failed
    
    print_header()
    
    # Test 1: login.html
    run_test(check_file, 
             "templates\\auth\\login.html", 
             'autocomplete="off"', 
             "login.html - autocomplete deshabilitado", 
             "1")
    
    # Test 2: test_ldap.html
    run_test(check_file, 
             "templates\\auth\\test_ldap.html", 
             'autocomplete="off"', 
             "test_ldap.html - autocomplete deshabilitado", 
             "2")
    
    # Test 3: crear.html
    run_test(check_file, 
             "templates\\usuarios\\crear.html", 
             'autocomplete="off"', 
             "crear.html - autocomplete deshabilitado", 
             "3")
    
    # Test 4: editar.html - múltiples campos
    run_test(check_multiple_fields, 
             "templates\\usuarios\\editar.html", 
             'autocomplete="off"', 
             "editar.html - múltiples campos", 
             "4", 
             2)
    
    # Test 5: gestionar.html - múltiples campos
    run_test(check_multiple_fields, 
             "templates\\usuarios\\gestionar.html", 
             'autocomplete="off"', 
             "gestionar.html - múltiples campos", 
             "5", 
             3)
    
    # Test 6: confirmar.html
    run_test(check_file, 
             "templates\\confirmacion\\confirmar.html", 
             'rel="noopener noreferrer"', 
             "confirmar.html - enlaces seguros", 
             "6")
    
    # Test 7: inventario_corporativo.html
    run_test(check_file, 
             "templates\\reportes\\inventario_corporativo.html", 
             'rel="noopener noreferrer"', 
             "inventario_corporativo.html - enlaces seguros", 
             "7")
    
    # Test 8: oficinas.html
    run_test(check_file, 
             "templates\\reportes\\oficinas.html", 
             'rel="noopener noreferrer"', 
             "oficinas.html - enlaces seguros", 
             "8")
    
    # Imprimir resumen
    print_summary()
    
    # Esperar entrada del usuario
    wait_for_key()
    
    # Salir con código apropiado
    if tests_failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()