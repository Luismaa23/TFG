"""
MenuMatch - Módulo de utilidades
"""

from utils.theme import COLORS, CUSTOM_CSS, inject_custom_css
from utils.components import (
    menu_card,
    metric_card,
    restriction_badge,
    section_header,
    empty_state,
    recommendation_card,
)
from utils.auth import (
    init_users_db,
    register_user,
    login_user,
    get_current_user,
    set_current_user,
    logout,
    require_auth,
    get_all_users,
    delete_user,
    update_user_role,
    admin_create_user,
    update_user_nombre,
    ROLE_ADMIN,
    ROLE_USUARIO,
    ROLE_RESTAURANTE,
    ALL_ROLES,
)
from utils.database import (
    create_pedido,
    get_pedidos_by_user,
    update_valoracion,
    get_all_pedidos,
)

__all__ = [
    "COLORS",
    "CUSTOM_CSS",
    "inject_custom_css",
    "menu_card",
    "metric_card",
    "restriction_badge",
    "section_header",
    "empty_state",
    "recommendation_card",
    "init_users_db",
    "register_user",
    "login_user",
    "get_current_user",
    "set_current_user",
    "logout",
    "require_auth",
    "get_all_users",
    "delete_user",
    "update_user_role",
    "admin_create_user",
    "update_user_nombre",
    "ROLE_ADMIN",
    "ROLE_USUARIO",
    "ROLE_RESTAURANTE",
    "ALL_ROLES",
    "create_pedido",
    "get_pedidos_by_user",
    "update_valoracion",
    "get_all_pedidos",
]
