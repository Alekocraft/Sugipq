# config/permissions.py
"""
Sistema centralizado de permisos basado en roles y oficinas
ACTUALIZADO: Incluye permisos para devoluciones, bajas y traspasos
"""

ROLE_PERMISSIONS = {
    'administrador': {   
        'modules': ['dashboard', 'material_pop', 'inventario_corporativo', 'prestamo_material', 'reportes', 'solicitudes', 'oficinas', 'novedades', 'usuarios'],  # âœ… AGREGADO 'usuarios'
        'actions': {
            'usuarios': ['view', 'manage', 'create', 'edit', 'delete'],  # âœ… AGREGADO - SOLO ADMINISTRADOR
            'materiales': ['view', 'create', 'edit', 'delete'],
            'solicitudes': ['view', 'create', 'edit', 'delete', 'approve', 'reject', 'partial_approve', 'return'],
            'oficinas': ['view', 'manage'],
            'aprobadores': ['view', 'manage'],
            'reportes': ['view_all'],  
            'inventario_corporativo': [
                'view', 'create', 'edit', 'delete', 'assign', 
                'manage_sedes', 'manage_oficinas',
                'approve_devolucion',  # âœ… NUEVO
                'approve_traspaso',    # âœ… NUEVO
                'dar_de_baja'          # âœ… NUEVO - Admin TAMBIÃ‰N puede dar de baja
            ],
            'prestamos': ['view', 'create', 'approve', 'reject', 'return', 'manage_materials'],
            'novedades': ['create', 'view', 'manage', 'approve', 'reject']
        },
        'office_filter': 'all'
    },

    'lider_inventario': {
        'modules': ['dashboard', 'material_pop', 'inventario_corporativo', 'prestamo_material', 'reportes', 'solicitudes', 'oficinas', 'novedades'],  # âŒ SIN 'usuarios'
        'actions': {
            # âŒ SIN 'usuarios'
            'materiales': ['view', 'create', 'edit', 'delete'],
            'solicitudes': ['view', 'create', 'edit', 'delete', 'approve', 'reject', 'partial_approve', 'return'],
            'oficinas': ['view'],
            'aprobadores': ['view'],
            'reportes': ['view_all'],  
            'inventario_corporativo': [
                'view', 'create', 'edit', 'delete', 'assign', 
                'manage_sedes', 'manage_oficinas',
                'approve_devolucion',  # âœ… NUEVO
                'approve_traspaso',    # âœ… NUEVO
                'dar_de_baja'          # âœ… NUEVO
            ],
            'prestamos': ['view', 'create', 'approve', 'reject', 'return', 'manage_materials'],         
            'novedades': ['create', 'view', 'manage', 'approve', 'reject']
        },
        'office_filter': 'all'
    },
    
    'aprobador': {
        'modules': ['dashboard', 'material_pop', 'inventario_corporativo', 'prestamo_material', 'reportes', 'solicitudes', 'oficinas', 'novedades'],  # âŒ SIN 'usuarios'
        'actions': {
            # âŒ SIN 'usuarios'
            'materiales': ['view'],
            'solicitudes': ['view', 'create', 'edit', 'delete', 'approve', 'reject', 'partial_approve', 'return'],
            'oficinas': ['view'],
            'aprobadores': ['view'],
            'reportes': ['view_all'],
            'inventario_corporativo': [
                'view',
                'approve_devolucion',  # âœ… NUEVO
                'approve_traspaso'     # âœ… NUEVO
            ],
            'prestamos': ['view', 'create', 'approve', 'reject', 'return'],
            'novedades': ['create', 'view', 'manage', 'approve', 'reject']
        },
        'office_filter': 'all'
    },
    
    'tesoreria': {
        'modules': ['dashboard', 'material_pop', 'inventario_corporativo', 'prestamo_material', 'reportes'],
        'actions': {
            'materiales': [],  
            'solicitudes': ['view'],  
            'oficinas': ['view'],
            'aprobadores': ['view'],
            'reportes': ['view_all'],  
            'inventario_corporativo': ['view'],  
            'prestamos': ['view'],  
            'novedades': ['view']
        },
        'office_filter': 'all'  
    },

    'oficina_coq': {
        'modules': ['dashboard', 'material_pop', 'prestamo_material', 'reportes', 'oficinas', 'solicitudes', 'novedades', 'inventario_corporativo'],  # âœ… AGREGADO
        'actions': {
            'materiales': [], 
            'solicitudes': ['view', 'create', 'return'],   
            'oficinas': ['view'],
            'aprobadores': ['view'],
            'prestamos': ['view_own', 'create'],
            'reportes': ['view_own'],
            'novedades': ['create', 'view', 'return'],
            'inventario_corporativo': [  # âœ… NUEVO
                'view',
                'solicitar_devolucion',
                'solicitar_traspaso'
            ]
        },
        'office_filter': 'COQ' 
    },

    'oficina_cali': {
        'modules': ['dashboard', 'material_pop', 'prestamo_material', 'reportes', 'oficinas', 'solicitudes', 'novedades', 'inventario_corporativo'],  # âœ… AGREGADO
        'actions': {
            'materiales': [],
            'solicitudes': ['view', 'create', 'return'],   
            'oficinas': ['view'],
            'aprobadores': ['view'],
            'prestamos': ['view_own', 'create'],
            'reportes': ['view_own'],
            'novedades': ['create', 'view', 'return'],
            'inventario_corporativo': [  # âœ… NUEVO
                'view',
                'solicitar_devolucion',
                'solicitar_traspaso'
            ]
        },
        'office_filter': 'CALI'
    },

    'oficina_pereira': {
        'modules': ['dashboard', 'material_pop', 'prestamo_material', 'reportes', 'oficinas', 'solicitudes', 'novedades', 'inventario_corporativo'],  # âœ… AGREGADO
        'actions': {
            'materiales': [],
            'solicitudes': ['view', 'create', 'return'],
            'oficinas': ['view'],
            'aprobadores': ['view'],
            'prestamos': ['view_own', 'create'],
            'reportes': ['view_own'],
            'novedades': ['create', 'view', 'return'],
            'inventario_corporativo': [  # âœ… NUEVO
                'view',
                'solicitar_devolucion',
                'solicitar_traspaso'
            ]
        },
        'office_filter': 'PEREIRA'
    },

    'oficina_neiva': {
        'modules': ['dashboard', 'material_pop', 'prestamo_material', 'reportes', 'oficinas', 'solicitudes', 'novedades', 'inventario_corporativo'],  # âœ… AGREGADO
        'actions': {
            'materiales': [],
            'solicitudes': ['view', 'create', 'return'],  
            'oficinas': ['view'],
            'aprobadores': ['view'],
            'prestamos': ['view_own', 'create'],
            'reportes': ['view_own'],
            'novedades': ['create', 'view', 'return'],
            'inventario_corporativo': [  # âœ… NUEVO
                'view',
                'solicitar_devolucion',
                'solicitar_traspaso'
            ]
        },
        'office_filter': 'NEIVA'
    },

    'oficina_kennedy': {
        'modules': ['dashboard', 'material_pop', 'prestamo_material', 'reportes', 'oficinas', 'solicitudes', 'novedades', 'inventario_corporativo'],  # âœ… AGREGADO
        'actions': {
            'materiales': [],
            'solicitudes': ['view', 'create', 'return'],  
            'oficinas': ['view'],
            'aprobadores': ['view'],
            'prestamos': ['view_own', 'create'],
            'reportes': ['view_own'],
            'novedades': ['create', 'view', 'return'],
            'inventario_corporativo': [  # âœ… NUEVO
                'view',
                'solicitar_devolucion',
                'solicitar_traspaso'
            ]
        },
        'office_filter': 'KENNEDY'
    },

    'oficina_bucaramanga': {
        'modules': ['dashboard', 'material_pop', 'prestamo_material', 'reportes', 'oficinas', 'solicitudes', 'novedades', 'inventario_corporativo'],  # âœ… AGREGADO
        'actions': {
            'materiales': [],
            'solicitudes': ['view', 'create', 'return'],  
            'oficinas': ['view'],
            'aprobadores': ['view'],
            'prestamos': ['view_own', 'create'],
            'reportes': ['view_own'],
            'novedades': ['create', 'view', 'return'],
            'inventario_corporativo': [  # âœ… NUEVO
                'view',
                'solicitar_devolucion',
                'solicitar_traspaso'
            ]
        },
        'office_filter': 'BUCARAMANGA'
    },

    'oficina_polo_club': {
        'modules': ['dashboard', 'material_pop', 'prestamo_material', 'reportes', 'oficinas', 'solicitudes', 'novedades', 'inventario_corporativo'],  # âœ… AGREGADO
        'actions': {
            'materiales': [],
            'solicitudes': ['view', 'create', 'return'],  
            'oficinas': ['view'],
            'aprobadores': ['view'],
            'prestamos': ['view_own', 'create'],
            'reportes': ['view_own'],
            'novedades': ['create', 'view', 'return'],
            'inventario_corporativo': [  # âœ… NUEVO
                'view',
                'solicitar_devolucion',
                'solicitar_traspaso'
            ]
        },
        'office_filter': 'POLO CLUB'
    },

    'oficina_nogal': {
        'modules': ['dashboard', 'material_pop', 'prestamo_material', 'reportes', 'oficinas', 'solicitudes', 'novedades', 'inventario_corporativo'],  # âœ… AGREGADO
        'actions': {
            'materiales': [],
            'solicitudes': ['view', 'create', 'return'],  
            'oficinas': ['view'],
            'aprobadores': ['view'],
            'prestamos': ['view_own', 'create'],
            'reportes': ['view_own'],
            'novedades': ['create', 'view', 'return'],
            'inventario_corporativo': [  # âœ… NUEVO
                'view',
                'solicitar_devolucion',
                'solicitar_traspaso'
            ]
        },
        'office_filter': 'NOGAL'
    },

    'oficina_tunja': {
        'modules': ['dashboard', 'material_pop', 'prestamo_material', 'reportes', 'oficinas', 'solicitudes', 'novedades', 'inventario_corporativo'],  # âœ… AGREGADO
        'actions': {
            'materiales': [],
            'solicitudes': ['view', 'create', 'return'],  
            'oficinas': ['view'],
            'aprobadores': ['view'],
            'prestamos': ['view_own', 'create'],
            'reportes': ['view_own'],
            'novedades': ['create', 'view', 'return'],
            'inventario_corporativo': [  # âœ… NUEVO
                'view',
                'solicitar_devolucion',
                'solicitar_traspaso'
            ]
        },
        'office_filter': 'TUNJA'
    },

    'oficina_cartagena': {
        'modules': ['dashboard', 'material_pop', 'prestamo_material', 'reportes', 'oficinas', 'solicitudes', 'novedades', 'inventario_corporativo'],  # âœ… AGREGADO
        'actions': {
            'materiales': [],
            'solicitudes': ['view', 'create', 'return'],  
            'oficinas': ['view'],
            'aprobadores': ['view'],
            'prestamos': ['view_own', 'create'],
            'reportes': ['view_own'],
            'novedades': ['create', 'view', 'return'],
            'inventario_corporativo': [  # âœ… NUEVO
                'view',
                'solicitar_devolucion',
                'solicitar_traspaso'
            ]
        },
        'office_filter': 'CARTAGENA'
    },

    'oficina_morato': {
        'modules': ['dashboard', 'material_pop', 'prestamo_material', 'reportes', 'oficinas', 'solicitudes', 'novedades', 'inventario_corporativo'],  # âœ… AGREGADO
        'actions': {
            'materiales': [],
            'solicitudes': ['view', 'create', 'return'],  
            'oficinas': ['view'],
            'aprobadores': ['view'],
            'prestamos': ['view_own', 'create'],
            'reportes': ['view_own'],
            'novedades': ['create', 'view', 'return'],
            'inventario_corporativo': [  # âœ… NUEVO
                'view',
                'solicitar_devolucion',
                'solicitar_traspaso'
            ]
        },
        'office_filter': 'MORATO'
    },

    'oficina_medellin': {
        'modules': ['dashboard', 'material_pop', 'prestamo_material', 'reportes', 'oficinas', 'solicitudes', 'novedades', 'inventario_corporativo'],  # âœ… AGREGADO
        'actions': {
            'materiales': [],
            'solicitudes': ['view', 'create', 'return'],  
            'oficinas': ['view'],
            'aprobadores': ['view'],
            'prestamos': ['view_own', 'create'],
            'reportes': ['view_own'],
            'novedades': ['create', 'view', 'return'],
            'inventario_corporativo': [  # âœ… NUEVO
                'view',
                'solicitar_devolucion',
                'solicitar_traspaso'
            ]
        },
        'office_filter': 'MEDELLÃN'
    },

    'oficina_cedritos': {
        'modules': ['dashboard', 'material_pop', 'prestamo_material', 'reportes', 'oficinas', 'solicitudes', 'novedades', 'inventario_corporativo'],  # âœ… AGREGADO
        'actions': {
            'materiales': [],
            'solicitudes': ['view', 'create', 'return'],   
            'oficinas': ['view'],
            'aprobadores': ['view'],
            'prestamos': ['view_own', 'create'],
            'reportes': ['view_own'],
            'novedades': ['create', 'view', 'return'],
            'inventario_corporativo': [  # âœ… NUEVO
                'view',
                'solicitar_devolucion',
                'solicitar_traspaso'
            ]
        },
        'office_filter': 'CEDRITOS'
    },

    'oficina_lourdes': {
        'modules': ['dashboard', 'material_pop', 'prestamo_material', 'reportes', 'oficinas', 'solicitudes', 'novedades', 'inventario_corporativo'],  # âœ… AGREGADO
        'actions': {
            'materiales': [],
            'solicitudes': ['view', 'create', 'return'],  
            'oficinas': ['view'],
            'aprobadores': ['view'],
            'prestamos': ['view_own', 'create'],
            'reportes': ['view_own'],
            'novedades': ['create', 'view', 'return'],
            'inventario_corporativo': [  # âœ… NUEVO
                'view',
                'solicitar_devolucion',
                'solicitar_traspaso'
            ]
        },
        'office_filter': 'LOURDES'
    },

    'oficina_regular': {
        'modules': ['dashboard', 'reportes', 'solicitudes', 'novedades', 'inventario_corporativo'],  # âœ… AGREGADO
        'actions': {
            'solicitudes': ['view', 'create', 'return'],
            'reportes': ['view_own'],
            'novedades': ['create', 'view', 'return'],
            'inventario_corporativo': [  # âœ… NUEVO (permisos limitados)
                'view'
            ]
        },
        'office_filter': 'own'
    }
}

OFFICE_MAPPING = {
    'COQ': 'COQ',
    'POLO CLUB': 'POLO CLUB',
    'NOGAL': 'NOGAL',
    'TUNJA': 'TUNJA',
    'CARTAGENA': 'CARTAGENA',
    'MORATO': 'MORATO',
    'MEDELLÃN': 'MEDELLÃN',
    'CEDRITOS': 'CEDRITOS',
    'LOURDES': 'LOURDES',
    'CALI': 'CALI',
    'PEREIRA': 'PEREIRA',
    'NEIVA': 'NEIVA',
    'KENNEDY': 'KENNEDY',
    'BUCARAMANGA': 'BUCARAMANGA'
}

def get_office_key(office_name: str) -> str:
    """Normaliza el nombre de oficina y lo mapea si existe en OFFICE_MAPPING."""
    key = office_name.upper().strip()
    return OFFICE_MAPPING.get(key, key)


def can_access(module, action=None):
    """Verifica si el usuario actual tiene acceso a un mÃ³dulo/acciÃ³n"""
    from flask import session
    
    if 'rol' not in session or 'usuario_id' not in session:
        return False
    
    rol = session.get('rol', '').lower()
    
    if rol not in ROLE_PERMISSIONS:
        return False
    
    permissions = ROLE_PERMISSIONS[rol]
    
    # Verificar acceso al mÃ³dulo
    if module not in permissions['modules']:
        return False
    
    # Si no se especifica acciÃ³n, solo verificar acceso al mÃ³dulo
    if action is None:
        return True
    
    # Verificar acceso a la acciÃ³n especÃ­fica
    module_actions = permissions['actions'].get(module, [])
    return action in module_actions


def can_create_novedad():
    """Verifica si el usuario puede crear novedades"""
    return can_access('novedades', 'create')


def can_manage_novedad():
    """Verifica si el usuario puede gestionar (aceptar/rechazar) novedades"""
    return can_access('novedades', 'manage')


def can_view_novedades():
    """Verifica si el usuario puede ver novedades"""
    return can_access('novedades', 'view')


def can_approve_novedad():
    """Verifica si el usuario puede aprobar novedades"""
    return can_access('novedades', 'approve')


def can_reject_novedad():
    """Verifica si el usuario puede rechazar novedades"""
    return can_access('novedades', 'reject')


def can_approve_solicitud():
    """Verifica si el usuario puede aprobar solicitudes"""
    return can_access('solicitudes', 'approve')


def can_approve_partial_solicitud():
    """Verifica si el usuario puede aprobar parcialmente solicitudes"""
    return can_access('solicitudes', 'partial_approve')


def can_reject_solicitud():
    """Verifica si el usuario puede rechazar solicitudes"""
    return can_access('solicitudes', 'reject')


def can_return_solicitud():
    """Verifica si el usuario puede registrar devoluciones"""
    return can_access('solicitudes', 'return')


def get_accessible_modules():
    """Obtiene los mÃ³dulos accesibles para el usuario actual"""
    from flask import session
    
    if 'rol' not in session:
        return []
    
    rol = session.get('rol', '').lower()
    if rol not in ROLE_PERMISSIONS:
        return []
    
    return ROLE_PERMISSIONS[rol]['modules']


def can_view_actions(module):
    """Verifica si el usuario puede ver acciones especÃ­ficas de un mÃ³dulo"""
    from flask import session
    
    if 'rol' not in session:
        return []
    
    rol = session.get('rol', '').lower()
    if rol not in ROLE_PERMISSIONS:
        return []
    
    return ROLE_PERMISSIONS[rol]['actions'].get(module, [])


def get_user_permissions():
    """Obtiene todos los permisos del usuario actual"""
    from flask import session
    
    if 'rol' not in session:
        return {'modules': [], 'actions': {}, 'office_filter': 'none'}
    
    rol = session.get('rol', '').lower()
    if rol not in ROLE_PERMISSIONS:
        return {'modules': [], 'actions': {}, 'office_filter': 'none'}
    
    return ROLE_PERMISSIONS[rol]


# ==================== FUNCIONES HELPER NUEVAS PARA INVENTARIO CORPORATIVO ====================

def puede_aprobar_devoluciones():
    """
    Verifica si el usuario puede aprobar devoluciones.
    Solo: Administrador, LÃ­der de Inventario, Aprobador
    """
    return can_access('inventario_corporativo', 'approve_devolucion')


def puede_aprobar_traspasos():
    """
    Verifica si el usuario puede aprobar traspasos.
    Solo: Administrador, LÃ­der de Inventario, Aprobador
    """
    return can_access('inventario_corporativo', 'approve_traspaso')


def puede_dar_de_baja():
    """
    Verifica si el usuario puede dar de baja productos.
    Solo: Administrador y LÃ­der de Inventario
    """
    return can_access('inventario_corporativo', 'dar_de_baja')


def puede_solicitar_devolucion():
    """
    Verifica si el usuario puede solicitar devoluciones.
    Oficinas y roles con permisos de gestiÃ³n
    """
    return can_access('inventario_corporativo', 'solicitar_devolucion')


def puede_solicitar_traspaso():
    """
    Verifica si el usuario puede solicitar traspasos.
    Oficinas y roles con permisos de gestiÃ³n
    """
    return can_access('inventario_corporativo', 'solicitar_traspaso')


def can_manage_inventario_corporativo():
    """
    Verifica si el usuario puede gestionar el inventario corporativo.
    (crear, editar, eliminar, asignar)
    """
    from flask import session
    rol = session.get('rol', '').lower()
    return rol in ['administrador', 'lider_inventario']


def can_view_inventario_actions():
    """
    Verifica si el usuario puede ver las acciones del inventario corporativo.
    """
    return can_access('inventario_corporativo', 'view')


# ==================== FUNCIONES PARA GESTIÃ“N DE USUARIOS ====================

def puede_gestionar_usuarios():
    """
    Verifica si el usuario puede gestionar usuarios.
    SOLO: Administrador
    """
    from flask import session
    rol = session.get('rol', '').lower()
    # Solo administrador puede gestionar usuarios
    return rol == 'administrador' and can_access('usuarios', 'manage')

def puede_crear_usuarios():
    """
    Verifica si el usuario puede crear usuarios.
    SOLO: Administrador
    """
    return can_access('usuarios', 'create')

def puede_editar_usuarios():
    """
    Verifica si el usuario puede editar usuarios.
    SOLO: Administrador
    """
    return can_access('usuarios', 'edit')

def puede_eliminar_usuarios():
    """
    Verifica si el usuario puede eliminar usuarios.
    SOLO: Administrador
    """
    return can_access('usuarios', 'delete')

def puede_ver_usuarios():
    """
    Verifica si el usuario puede ver usuarios.
    SOLO: Administrador (por ahora)
    """
    return can_access('usuarios', 'view')