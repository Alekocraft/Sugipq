# utils/filters.py - CORREGIDO CON FORMATO DE NÚMEROS
from flask import session

def filtrar_por_oficina_usuario(datos, campo_oficina_id='oficina_id'):
    """
    Filtra datos según la oficina del usuario actual.
    """
    if 'usuario_id' not in session:
        print("🔍 DEBUG filtrar_por_oficina_usuario: Usuario no autenticado")
        return []
    
    # Importar aquí para evitar dependencia circular
    from utils.permissions import get_office_filter, PermissionManager
    
    # Usar el sistema de permisos actualizado
    office_filter = get_office_filter()
    
    # Si office_filter es None, significa acceso total
    if office_filter is None:
        print("🔍 DEBUG filtrar_por_oficina_usuario: Usuario con acceso total")
        return datos
    
    # Para roles que filtran por oficina específica
    if office_filter == 'own':
        # Filtrar por oficina_id de sesión
        oficina_id_usuario = session.get('oficina_id')
        
        if not oficina_id_usuario:
            print("🔍 DEBUG filtrar_por_oficina_usuario: No hay ID de oficina en sesión")
            return []
        
        print(f"🔍 DEBUG filtrar_por_oficina_usuario: Oficina ID usuario: {oficina_id_usuario}")
        print(f"🔍 DEBUG filtrar_por_oficina_usuario: Total datos a filtrar: {len(datos)}")
        
        datos_filtrados = []
        for i, item in enumerate(datos):
            item_oficina_id = str(item.get(campo_oficina_id, ''))
            usuario_oficina_id = str(oficina_id_usuario)
            
            if item_oficina_id == usuario_oficina_id:
                datos_filtrados.append(item)
                print(f"🔍 DEBUG filtrar_por_oficina_usuario: Item {i} coincide - Oficina: {item_oficina_id}")
            else:
                print(f"🔍 DEBUG filtrar_por_oficina_usuario: Item {i} NO coincide - Item Oficina: {item_oficina_id}, Usuario Oficina: {usuario_oficina_id}")
        
        print(f"🔍 DEBUG filtrar_por_oficina_usuario: Filtrados {len(datos_filtrados)} de {len(datos)} items")
        return datos_filtrados
    else:
        # Si office_filter es un string específico (ej: 'COQ', 'CALI', etc.)
        # Aquí necesitarías lógica adicional para filtrar por nombre de oficina
        # Por ahora, devolvemos todos los datos ya que el filtro no es por ID numérico
        print(f"🔍 DEBUG filtrar_por_oficina_usuario: Filtro de oficina por nombre: {office_filter}")
        return datos

def verificar_acceso_oficina(oficina_id):
    """
    Verifica si el usuario actual tiene acceso a una oficina específica.
    """
    if 'usuario_id' not in session:
        return False
    
    # Importar aquí para evitar dependencia circular
    from utils.permissions import get_office_filter
    
    office_filter = get_office_filter()
    
    # Si office_filter es None, tiene acceso total
    if office_filter is None:
        return True
    
    # Si office_filter es 'own', verifica si es su oficina
    if office_filter == 'own':
        oficina_id_usuario = session.get('oficina_id')
        return str(oficina_id) == str(oficina_id_usuario)
    
    # Para otros casos (filtro por nombre de oficina), necesitarías más lógica
    # Por ahora, devolvemos False ya que no hay forma directa de comparar
    return False


# ✅ FILTROS JINJA2 PARA FORMATEO DE NÚMEROS
def formato_numero(valor, decimales=0):
    """
    Formatea un número con separador de miles (punto) y decimales (coma).
    Ejemplos:
        100000 -> 100.000
        1500000 -> 1.500.000
        1234.56 con decimales=2 -> 1.234,56
    """
    try:
        valor = float(valor) if valor else 0
        
        if decimales > 0:
            # Con decimales: usar coma como separador decimal
            formato = f"{{:,.{decimales}f}}"
            resultado = formato.format(valor)
            # Cambiar coma por punto (miles) y punto por coma (decimales)
            resultado = resultado.replace(',', 'X').replace('.', ',').replace('X', '.')
        else:
            # Sin decimales
            resultado = f"{int(valor):,}".replace(',', '.')
        
        return resultado
    except (ValueError, TypeError):
        return '0'


def formato_moneda(valor, simbolo='$', decimales=0):
    """
    Formatea un número como moneda.
    Ejemplos:
        100000 -> $100.000
        1500000.50 con decimales=2 -> $1.500.000,50
    """
    numero_formateado = formato_numero(valor, decimales)
    return f"{simbolo}{numero_formateado}"


def formato_porcentaje(valor, decimales=1):
    """
    Formatea un número como porcentaje.
    Ejemplos:
        0.25 -> 25%
        0.333 con decimales=1 -> 33,3%
    """
    try:
        valor = float(valor) if valor else 0
        porcentaje = valor * 100 if valor < 1 else valor
        
        if decimales > 0:
            return f"{porcentaje:.{decimales}f}%".replace('.', ',')
        else:
            return f"{int(porcentaje)}%"
    except (ValueError, TypeError):
        return '0%'


# Función para registrar los filtros en la aplicación Flask
def registrar_filtros_jinja(app):
    """
    Registra todos los filtros personalizados en la aplicación Flask.
    Debe llamarse desde el archivo principal de la aplicación.
    """
    app.jinja_env.filters['formato_numero'] = formato_numero
    app.jinja_env.filters['formato_moneda'] = formato_moneda
    app.jinja_env.filters['formato_porcentaje'] = formato_porcentaje