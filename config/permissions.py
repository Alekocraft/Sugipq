# config/permissions.py
"""
Sistema centralizado de permisos basado en roles y oficinas
ACTUALIZADO: 15 oficinas con roles independientes
- Cada oficina tiene su propio rol
- Todos los roles de oficina comparten los mismos permisos
"""

import logging
from flask import session
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Permisos estándar para todas las oficinas
OFICINA_STANDARD_PERMISSIONS = {
    'modules': ['dashboard', 'material_pop', 'inventario_corporativo', 'prestamo_material', 'reportes', 'solicitudes', 'oficinas', 'novedades'],
    'actions': {
        'materiales': ['view'],
        'solicitudes': ['view', 'create'],
        'oficinas': ['view'],
        'reportes': ['view_all'],
        'inventario_corporativo': ['view', 'solicitar_devolucion', 'solicitar_traspaso'],
        'prestamos': ['view', 'create'],
        'novedades': ['create', 'view']
    },
    'office_filter': 'own'
}

ROLE_PERMISSIONS = {
    'administrador': {   
        'modules': ['dashboard', 'material_pop', 'inventario_corporativo', 'prestamo_material', 'reportes', 'solicitudes', 'oficinas', 'novedades', 'usuarios'],
        'actions': {
            'usuarios': ['view', 'manage', 'create', 'edit', 'delete'],
            'materiales': ['view', 'create', 'edit', 'delete'],
            'solicitudes': ['view', 'create', 'edit', 'delete', 'approve', 'reject', 'partial_approve', 'return'],
            'oficinas': ['view', 'manage'],
            'aprobadores': ['view', 'manage'],
            'reportes': ['view_all'],  
            'inventario_corporativo': ['view', 'create', 'edit', 'delete', 'assign', 'manage_sedes', 'manage_oficinas', 'approve_devolucion', 'approve_traspaso', 'dar_de_baja', 'solicitar_devolucion', 'solicitar_traspaso'],
            'prestamos': ['view', 'create', 'approve', 'reject', 'return', 'manage_materials'],
            'novedades': ['create', 'view', 'manage', 'approve', 'reject']
        },
        'office_filter': 'all'
    },
    'lider_inventario': {
        'modules': ['dashboard', 'material_pop', 'inventario_corporativo', 'prestamo_material', 'reportes', 'solicitudes', 'oficinas', 'novedades'],
        'actions': {
            'materiales': ['view', 'create', 'edit', 'delete'],
            'solicitudes': ['view', 'create', 'edit', 'delete', 'approve', 'reject', 'partial_approve', 'return'],
            'oficinas': ['view'],
            'aprobadores': ['view'],
            'reportes': ['view_all'],  
            'inventario_corporativo': ['view', 'create', 'edit', 'delete', 'assign', 'manage_sedes', 'manage_oficinas', 'approve_devolucion', 'approve_traspaso', 'dar_de_baja', 'solicitar_devolucion', 'solicitar_traspaso'],
            'prestamos': ['view', 'create', 'approve', 'reject', 'return', 'manage_materials'],
            'novedades': ['create', 'view', 'manage', 'approve', 'reject']
        },
        'office_filter': 'all'
    },
    'aprobador': {
        'modules': ['dashboard', 'material_pop', 'inventario_corporativo', 'prestamo_material', 'reportes', 'solicitudes', 'oficinas', 'novedades'],
        'actions': {
            'materiales': ['view', 'create', 'edit', 'delete'],
            'solicitudes': ['view', 'create', 'edit', 'delete', 'approve', 'reject', 'partial_approve', 'return'],
            'oficinas': ['view'],
            'aprobadores': ['view'],
            'reportes': ['view_all'],
            'inventario_corporativo': ['view', 'approve_devolucion', 'approve_traspaso', 'solicitar_devolucion', 'solicitar_traspaso'],
            'prestamos': ['view', 'create', 'approve', 'reject', 'return', 'manage_materials'],
            'novedades': ['create', 'view', 'manage', 'approve', 'reject']
        },
        'office_filter': 'all'
    },
    'tesoreria': {
        'modules': ['reportes'],
        'actions': {'reportes': ['view_all']},
        'office_filter': 'own'
    },
    # 15 ROLES DE OFICINAS
    'oficina_pepe_sierra': dict(OFICINA_STANDARD_PERMISSIONS),
    'oficina_polo_club': dict(OFICINA_STANDARD_PERMISSIONS),
    'oficina_nogal': dict(OFICINA_STANDARD_PERMISSIONS),
    'oficina_morato': dict(OFICINA_STANDARD_PERMISSIONS),
    'oficina_cedritos': dict(OFICINA_STANDARD_PERMISSIONS),
    'oficina_coq': dict(OFICINA_STANDARD_PERMISSIONS),
    'oficina_lourdes': dict(OFICINA_STANDARD_PERMISSIONS),
    'oficina_kennedy': dict(OFICINA_STANDARD_PERMISSIONS),
    'oficina_principal': dict(OFICINA_STANDARD_PERMISSIONS),
    'oficina_cali': dict(OFICINA_STANDARD_PERMISSIONS),
    'oficina_medellin': dict(OFICINA_STANDARD_PERMISSIONS),
    'oficina_pereira': dict(OFICINA_STANDARD_PERMISSIONS),
    'oficina_bucaramanga': dict(OFICINA_STANDARD_PERMISSIONS),
    'oficina_cartagena': dict(OFICINA_STANDARD_PERMISSIONS),
    'oficina_tunja': dict(OFICINA_STANDARD_PERMISSIONS),
    'oficina_neiva': dict(OFICINA_STANDARD_PERMISSIONS),
}

OFFICE_ROLES = {
    'pepe_sierra': 'oficina_pepe_sierra', 'pepesierra': 'oficina_pepe_sierra', 'pepe sierra': 'oficina_pepe_sierra',
    'polo_club': 'oficina_polo_club', 'poloclub': 'oficina_polo_club', 'polo club': 'oficina_polo_club',
    'nogal': 'oficina_nogal',
    'morato': 'oficina_morato',
    'cedritos': 'oficina_cedritos',
    'coq': 'oficina_coq',
    'lourdes': 'oficina_lourdes',
    'kennedy': 'oficina_kennedy',
    'principal': 'oficina_principal', 'bogota': 'oficina_principal', 'bogotá': 'oficina_principal',
    'cali': 'oficina_cali',
    'medellin': 'oficina_medellin', 'medellín': 'oficina_medellin',
    'pereira': 'oficina_pereira',
    'bucaramanga': 'oficina_bucaramanga',
    'cartagena': 'oficina_cartagena',
    'tunja': 'oficina_tunja',
    'neiva': 'oficina_neiva'
}

def get_office_key(office_name):
    if not office_name:
        return ''
    office_lower = office_name.lower().strip()
    office_normalized = office_lower.replace('_', ' ')
    if office_normalized in OFFICE_ROLES:
        return OFFICE_ROLES[office_normalized]
    if office_lower in OFFICE_ROLES:
        return OFFICE_ROLES[office_lower]
    return ''

class PermissionManager:
    @staticmethod
    def normalize_role_key(role_raw: str) -> str:
        if not role_raw:
            return ''
        role = role_raw.strip().lower()
        replacements = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ü': 'u', 'ñ': 'n'}
        for old, new in replacements.items():
            role = role.replace(old, new)
        role_normalized = role.replace(' ', '_')
        if role_normalized in ROLE_PERMISSIONS:
            return role_normalized
        if 'admin' in role_normalized:
            return 'administrador'
        if 'lider' in role_normalized and 'invent' in role_normalized:
            return 'lider_inventario'
        if 'tesorer' in role_normalized:
            return 'tesoreria'
        if role_normalized.startswith('oficina_'):
            if role_normalized in ROLE_PERMISSIONS:
                return role_normalized
        return role_normalized
    
    @staticmethod
    def get_user_permissions() -> Dict[str, Any]:
        role_raw = session.get('rol', '')
        role_key = PermissionManager.normalize_role_key(role_raw)
        office_name = session.get('oficina_nombre', '')
        office_key = get_office_key(office_name)
        role_perms = ROLE_PERMISSIONS.get(role_key, {})
        return {
            'role_key': role_key,
            'role': role_perms,
            'office_key': office_key,
            'office_filter': role_perms.get('office_filter', 'own'),
        }
    
    @staticmethod
    def has_module_access(module_name: str) -> bool:
        perms = PermissionManager.get_user_permissions()
        return module_name in perms['role'].get('modules', [])
    
    @staticmethod
    def has_action_permission(module: str, action: str) -> bool:
        perms = PermissionManager.get_user_permissions()
        return action in perms['role'].get('actions', {}).get(module, [])

def can_access(module: str, action: Optional[str] = None) -> bool:
    return PermissionManager.has_action_permission(module, action) if action else PermissionManager.has_module_access(module)

def get_accessible_modules():
    if 'rol' not in session:
        return []
    rol = session.get('rol', '').lower()
    return ROLE_PERMISSIONS.get(rol, {}).get('modules', [])

def can_view_actions(module):
    if 'rol' not in session:
        return []
    rol = session.get('rol', '').lower()
    return ROLE_PERMISSIONS.get(rol, {}).get('actions', {}).get(module, [])

def get_user_permissions():
    if 'rol' not in session:
        return {'modules': [], 'actions': {}, 'office_filter': 'none'}
    rol = session.get('rol', '').lower()
    return ROLE_PERMISSIONS.get(rol, {'modules': [], 'actions': {}, 'office_filter': 'none'})

def puede_aprobar_devoluciones():
    return can_access('inventario_corporativo', 'approve_devolucion')

def puede_aprobar_traspasos():
    return can_access('inventario_corporativo', 'approve_traspaso')

def puede_dar_de_baja():
    return can_access('inventario_corporativo', 'dar_de_baja')

def puede_solicitar_devolucion():
    return can_access('inventario_corporativo', 'solicitar_devolucion')

def puede_solicitar_traspaso():
    return can_access('inventario_corporativo', 'solicitar_traspaso')

def can_manage_inventario_corporativo():
    rol = session.get('rol', '').lower()
    return rol in ['administrador', 'lider_inventario']

def can_view_inventario_actions():
    return can_access('inventario_corporativo', 'view')

def puede_gestionar_usuarios():
    rol = session.get('rol', '').lower()
    return rol == 'administrador' and can_access('usuarios', 'manage')

def puede_crear_usuarios():
    return can_access('usuarios', 'create')

def puede_editar_usuarios():
    return can_access('usuarios', 'edit')

def puede_eliminar_usuarios():
    return can_access('usuarios', 'delete')

def puede_ver_usuarios():
    return can_access('usuarios', 'view')

def can_view_all_offices() -> bool:
    perms = PermissionManager.get_user_permissions()
    return perms.get('office_filter') == 'all'

def can_create_solicitud() -> bool:
    return PermissionManager.has_action_permission('solicitudes', 'create')

def can_create_novedad() -> bool:
    return PermissionManager.has_action_permission('novedades', 'create') or PermissionManager.has_module_access('novedades')

def can_manage_novedad() -> bool:
    perms = PermissionManager.get_user_permissions()
    role_key = perms.get('role_key', '')
    if role_key in ['administrador', 'lider_inventario', 'aprobador']:
        return True
    return PermissionManager.has_action_permission('novedades', 'approve') or PermissionManager.has_action_permission('novedades', 'reject')

def can_approve_solicitud() -> bool:
    return PermissionManager.has_action_permission('solicitudes', 'approve')

def can_manage_oficinas() -> bool:
    return PermissionManager.has_action_permission('oficinas', 'manage')

def can_generate_reports() -> bool:
    return PermissionManager.has_action_permission('reportes', 'view_all')

def can_manage_usuarios() -> bool:
    rol = session.get('rol', '').lower()
    return rol == 'administrador' and PermissionManager.has_action_permission('usuarios', 'manage')

def can_view_dashboard() -> bool:
    return PermissionManager.has_module_access('dashboard')

def get_user_role() -> str:
    perms = PermissionManager.get_user_permissions()
    return perms.get('role_key', '')

def get_user_modules() -> list:
    perms = PermissionManager.get_user_permissions()
    return perms.get('role', {}).get('modules', [])

def has_module_access(module_name: str) -> bool:
    return module_name in get_user_modules()

def check_permission(module: str, action: str) -> bool:
    return PermissionManager.has_action_permission(module, action)

def check_permissions(permissions_list: list) -> bool:
    for module, action in permissions_list:
        if not check_permission(module, action):
            return False
    return True