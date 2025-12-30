"""
Script de diagnóstico - Buscar la función real de gestión de usuarios
"""

print("=" * 70)
print("DIAGNOSTICO: Buscando función de usuarios en app.py")
print("=" * 70)
print()

# Leer app.py
print("1. Leyendo app.py...")
try:
    with open('app.py', 'r', encoding='utf-8') as f:
        lineas = f.readlines()
    print(f"   ✅ Archivo leido ({len(lineas)} lineas)")
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

print()
print("2. Buscando funciones relacionadas con usuarios...")
print()

funciones_encontradas = []
rutas_encontradas = []

for i, linea in enumerate(lineas, 1):
    # Buscar definiciones de funciones
    if 'def ' in linea and ('usuario' in linea.lower() or 'user' in linea.lower()):
        funciones_encontradas.append((i, linea.strip()))
    
    # Buscar rutas de Flask
    if "@app.route('/usuarios" in linea:
        rutas_encontradas.append((i, linea.strip()))
        # Buscar la función asociada en las siguientes líneas
        for j in range(i, min(i+5, len(lineas))):
            if 'def ' in lineas[j]:
                funciones_encontradas.append((j+1, lineas[j].strip()))
                break

if funciones_encontradas:
    print("FUNCIONES ENCONTRADAS:")
    print("━" * 70)
    for linea_num, funcion in funciones_encontradas:
        print(f"Linea {linea_num}: {funcion}")
    print()
else:
    print("⚠️  No se encontraron funciones relacionadas con usuarios")
    print()

if rutas_encontradas:
    print("RUTAS ENCONTRADAS:")
    print("━" * 70)
    for linea_num, ruta in rutas_encontradas:
        print(f"Linea {linea_num}: {ruta}")
    print()
else:
    print("⚠️  No se encontraron rutas @app.route('/usuarios')")
    print()

# Buscar render_template con usuarios/listar.html
print("3. Buscando render_template('usuarios/listar.html'...")
print()

renders_encontrados = []
for i, linea in enumerate(lineas, 1):
    if "render_template('usuarios/listar.html'" in linea:
        renders_encontrados.append((i, linea.strip()))
        # Contexto: 3 líneas antes y 3 después
        inicio = max(0, i-4)
        fin = min(len(lineas), i+3)
        print(f"ENCONTRADO en linea {i}:")
        print("─" * 70)
        for j in range(inicio, fin):
            marcador = ">>>" if j == i-1 else "   "
            print(f"{marcador} {j+1:4d}: {lineas[j].rstrip()}")
        print()

if not renders_encontrados:
    print("⚠️  No se encontró render_template('usuarios/listar.html'")
    print()

# Buscar si hay blueprint de usuarios
print("4. Buscando blueprint de usuarios...")
print()

blueprints_encontrados = []
for i, linea in enumerate(lineas, 1):
    if 'usuarios_bp' in linea or 'usuario_bp' in linea:
        blueprints_encontrados.append((i, linea.strip()))

if blueprints_encontrados:
    print("REFERENCIAS A BLUEPRINT DE USUARIOS:")
    print("━" * 70)
    for linea_num, blueprint in blueprints_encontrados:
        print(f"Linea {linea_num}: {blueprint}")
    print()
    print("⚠️  IMPORTANTE: Si hay un blueprint registrado,")
    print("   la ruta /usuarios la maneja el blueprint,")
    print("   NO la función de respaldo en app.py")
    print()
else:
    print("✅ No se encontró blueprint de usuarios")
    print("   La gestión debe estar en app.py directamente")
    print()

print("=" * 70)
print("RESUMEN DEL DIAGNOSTICO")
print("=" * 70)
print()

if funciones_encontradas:
    print(f"✅ Se encontraron {len(funciones_encontradas)} funciones relacionadas")
else:
    print("❌ No se encontraron funciones de usuarios")

if rutas_encontradas:
    print(f"✅ Se encontraron {len(rutas_encontradas)} rutas /usuarios")
else:
    print("❌ No se encontraron rutas /usuarios")

if renders_encontrados:
    print(f"✅ Se encontró render_template en linea(s): {', '.join(str(r[0]) for r in renders_encontrados)}")
else:
    print("❌ No se encontró render_template('usuarios/listar.html'")

if blueprints_encontrados:
    print(f"⚠️  Hay blueprint de usuarios registrado")
    print(f"   Probablemente la gestión está en: blueprints/usuarios.py")
else:
    print("✅ No hay blueprint de usuarios")

print()
print("=" * 70)
print("SIGUIENTE PASO:")
print("=" * 70)
print()

if renders_encontrados:
    linea_render = renders_encontrados[0][0]
    print(f"El render_template está en la linea {linea_render}")
    print()
    print("Para corregir manualmente:")
    print(f"1. Abre app.py")
    print(f"2. Ve a la linea {linea_render}")
    print(f"3. Busca la función que contiene ese render_template")
    print(f"4. Cambia:")
    print(f"   return render_template('usuarios/listar.html', usuarios=usuarios)")
    print(f"")
    print(f"   Por:")
    print(f"   return render_template('usuarios/listar.html',")
    print(f"                          usuarios=usuarios,")
    print(f"                          total_usuarios=len(usuarios),")
    print(f"                          total_activos=len([u for u in usuarios if u.get('activo', True)]),")
    print(f"                          total_ldap=len([u for u in usuarios if u.get('EsLDAP', 0) == 1]))")
elif blueprints_encontrados:
    print("Parece que hay un blueprint de usuarios.")
    print("Revisa el archivo: blueprints/usuarios.py")
    print("Y busca la función que renderiza usuarios/listar.html")
else:
    print("No se encontró donde está el render_template.")
    print("Busca manualmente en app.py:")
    print("  Ctrl+F: usuarios/listar.html")

print()
print("=" * 70)