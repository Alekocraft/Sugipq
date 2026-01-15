# config/__init__.py

# Importaciones desde el módulo permissions
from .permissions import (
    can_access,
    puede_gestionar_usuarios,
    puede_crear_usuarios,
    puede_editar_usuarios,
    puede_eliminar_usuarios,
    puede_ver_usuarios,
    get_accessible_modules
)

# Importaciones desde el módulo config
from .config import Config, DevelopmentConfig, ProductionConfig, TestingConfig, config

# Lista de lo que se exporta cuando se usa "from config import *"
__all__ = [
    # Funciones de permissions
    'can_access',
    'puede_gestionar_usuarios',
    'puede_crear_usuarios',
    'puede_editar_usuarios',
    'puede_eliminar_usuarios',
    'puede_ver_usuarios',
    'get_accessible_modules',
    
    # Clases y objetos de config
    'Config',
    'DevelopmentConfig',
    'ProductionConfig',
    'TestingConfig',
    'config'
]