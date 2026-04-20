"""
MenuMatch - Panel de Administración
Gestión completa de usuarios: crear, editar rol/nombre y eliminar.
Solo accesible para usuarios con rol 'admin'.
"""

import streamlit as st
import pandas as pd
from utils.theme import inject_custom_css
from utils.database import get_all_evaluaciones
from utils.auth import (
    require_auth,
    get_all_users,
    delete_user,
    update_user_role,
    update_user_nombre,
    admin_create_user,
    ROLE_ADMIN,
    ROLE_USUARIO,
    ROLE_RESTAURANTE,
    ALL_ROLES,
)
from utils.components import section_header
from utils.menu_storage import get_all_menus

inject_custom_css()

# Guardia de autenticación — solo admins
user = require_auth(allowed_roles=[ROLE_ADMIN])

# Header
section_header(
    "Panel de Administración",
    f"Bienvenido, {user['nombre']} — Gestión completa del sistema"
)

# ─── Estadísticas ────────────────────────────────────────────────────────────
st.markdown("### Estadísticas del Sistema")

all_users = get_all_users()
total_users = len(all_users)
admins = sum(1 for u in all_users.values() if u["role"] == ROLE_ADMIN)
restaurantes = sum(1 for u in all_users.values() if u["role"] == ROLE_RESTAURANTE)
usuarios = sum(1 for u in all_users.values() if u["role"] == ROLE_USUARIO)
total_platos = len(get_all_menus())

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
        <div class="metric-container">
            <p class="metric-value">{total_users}</p>
            <p class="metric-label">Total Usuarios</p>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
        <div class="metric-container">
            <p class="metric-value">{restaurantes}</p>
            <p class="metric-label">Restaurantes</p>
        </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
        <div class="metric-container">
            <p class="metric-value">{usuarios}</p>
            <p class="metric-label">Usuarios</p>
        </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
        <div class="metric-container">
            <p class="metric-value">{total_platos}</p>
            <p class="metric-label">Platos Cargados</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── Crear Nuevo Usuario ─────────────────────────────────────────────────────
st.markdown("### Crear Nuevo Usuario")

st.markdown(
    '<div style="background:#1E293B;border-radius:12px;padding:1rem 1.25rem;'
    'margin-bottom:1rem;border:1px solid #334155;">'
    '<p style="color:#8B949E;margin:0;font-size:0.85rem;">'
    'Desde aquí puedes crear usuarios de cualquier tipo, incluyendo '
    'administradores. Los usuarios también pueden registrarse por su cuenta '
    'desde la pantalla de Login (excepto admins).</p></div>',
    unsafe_allow_html=True,
)

with st.form("admin_create_user_form", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
        new_nombre = st.text_input(
            "Nombre completo *",
            placeholder="Ej: María García",
        )
        new_username = st.text_input(
            "Nombre de usuario *",
            placeholder="mínimo 3 caracteres",
        )

    with col2:
        new_password = st.text_input(
            "Contraseña *",
            type="password",
            placeholder="mínimo 4 caracteres",
        )
        role_labels = {
            ROLE_USUARIO: "Usuario — Buscar y pedir menús",
            ROLE_RESTAURANTE: "Restaurante — Publicar menús",
            ROLE_ADMIN: "Administrador — Gestión total",
        }
        new_role = st.selectbox(
            "Rol *",
            options=ALL_ROLES,
            format_func=lambda x: role_labels.get(x, x),
        )

    create_submit = st.form_submit_button(
        "Crear Usuario",
        type="primary",
        use_container_width=True,
    )

    if create_submit:
        success, msg = admin_create_user(new_username, new_password, new_role, new_nombre)
        if success:
            st.success(f"{msg}")
            st.rerun()
        else:
            st.error(f"{msg}")

st.markdown("<br>", unsafe_allow_html=True)

# ─── Gestión de Usuarios Existentes ──────────────────────────────────────────
st.markdown("### Usuarios Registrados")

if not all_users:
    st.info("No hay usuarios registrados.")
else:
    for username, data in all_users.items():
        role_emoji = {"admin": "", "restaurante": "", "usuario": ""}
        role_color = {"admin": "#F85149", "restaurante": "#D29922", "usuario": "#3B82F6"}
        is_self = username == user["username"]

        # Badge "(Tú)" condicional
        tu_badge = (
            ' <span style="color:#3B82F6;font-size:0.75rem;'
            'margin-left:0.5rem;">(Tú)</span>'
            if is_self else ""
        )

        emoji = role_emoji.get(data["role"], "")
        color = role_color.get(data["role"], "#8B949E")

        st.markdown(
            f'<div style="background:#1E293B;border-radius:10px;'
            f'padding:0.75rem 1rem;border-left:4px solid {color};'
            f'margin-bottom:0.25rem;">'
            f'<p style="margin:0;color:#E2E8F0;font-weight:600;">'
            f'{emoji} {data["nombre"]}{tu_badge}</p>'
            f'<p style="margin:0.25rem 0 0 0;color:#8B949E;font-size:0.8rem;">'
            f'@{username} · {data["role"].title()}</p></div>',
            unsafe_allow_html=True,
        )

        col_nombre, col_role, col_actions = st.columns([3, 2, 2])

        with col_nombre:
            edited_nombre = st.text_input(
                "Nombre",
                value=data["nombre"],
                key=f"nombre_{username}",
                label_visibility="collapsed",
            )
            if edited_nombre != data["nombre"]:
                if st.button("Guardar nombre", key=f"save_nombre_{username}", use_container_width=True):
                    success, msg = update_user_nombre(username, edited_nombre)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        with col_role:
            new_role = st.selectbox(
                "Rol",
                options=ALL_ROLES,
                index=ALL_ROLES.index(data["role"]),
                key=f"role_{username}",
                label_visibility="collapsed",
            )
            if new_role != data["role"]:
                if st.button("Guardar rol", key=f"save_role_{username}", use_container_width=True):
                    success, msg = update_user_role(username, new_role)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        with col_actions:
            if not is_self:
                if st.button("Eliminar", key=f"del_{username}", type="secondary", use_container_width=True):
                    success, msg = delete_user(username)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
            else:
                st.markdown(
                    '<div style="padding:0.5rem;text-align:center;'
                    'color:#8B949E;font-size:0.8rem;">No puedes eliminarte</div>',
                    unsafe_allow_html=True,
                )

        st.divider()

# ─── Exportar Datos de Investigación ─────────────────────────────────────────
st.markdown("### Exportar Datos de Investigación")

st.markdown(
    '<div style="background:#1E293B;border-radius:12px;padding:1.5rem;'
    'margin-bottom:1.5rem;border:1px solid #334155;">'
    '<h4 style="color:#F59E0B;margin-bottom:0.5rem;">'
    'Sistema de archivos efímero</h4>'
    '<p style="color:#8B949E;margin:0;">'
    'Streamlit Community Cloud reinicia los contenedores periódicamente. '
    'Las evaluaciones almacenadas en SQLite se perderán tras cada reinicio. '
    'Usa este botón para exportar los datos de investigación antes de que '
    'eso ocurra.</p></div>',
    unsafe_allow_html=True,
)

evaluaciones = get_all_evaluaciones()

if len(evaluaciones) == 0:
    st.info("No hay evaluaciones registradas todavía.")
else:
    df_eval = pd.DataFrame(evaluaciones)

    # Convertir listas y dicts a texto plano para CSV
    if "platos" in df_eval.columns:
        df_eval["platos"] = df_eval["platos"].apply(
            lambda x: " | ".join(x) if isinstance(x, list) else str(x)
        )
    if "restricciones" in df_eval.columns:
        df_eval["restricciones"] = df_eval["restricciones"].apply(
            lambda x: str(x) if not isinstance(x, str) else x
        )

    col_info, col_btn = st.columns([2, 1])

    with col_info:
        st.markdown(
            f'<div style="background:#1E293B;border-radius:8px;'
            f'padding:0.75rem 1rem;display:inline-block;">'
            f'<span style="color:#8B949E;">Registros disponibles: </span>'
            f'<span style="color:#3B82F6;font-weight:600;">{len(df_eval)}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_btn:
        csv_data = df_eval.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Descargar CSV",
            data=csv_data,
            file_name="resultados_tfg_menumatch.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary",
        )

    st.markdown("#### Vista Previa")
    st.dataframe(df_eval.head(10), use_container_width=True, hide_index=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── Info de seguridad ───────────────────────────────────────────────────────
st.markdown(
    '<div style="background:linear-gradient(145deg,#1E293B,#0F172A);'
    'border-radius:12px;padding:1.5rem;border:1px solid #334155;">'
    '<h4 style="color:#3B82F6;margin-bottom:1rem;">Información de Seguridad</h4>'
    '<ul style="color:#8B949E;margin:0;padding-left:1.5rem;">'
    '<li style="margin-bottom:0.5rem;">Las contraseñas se almacenan con hash bcrypt</li>'
    '<li style="margin-bottom:0.5rem;">Solo los administradores pueden crear otros administradores</li>'
    '<li style="margin-bottom:0.5rem;">No se puede eliminar ni cambiar el rol del último administrador</li>'
    '<li>Los usuarios y restaurantes pueden registrarse desde la pantalla de Login</li>'
    '</ul></div>',
    unsafe_allow_html=True,
)
