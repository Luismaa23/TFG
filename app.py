"""
MenuMatch - Tu menú del día óptimo
Punto de entrada: configuración global, autenticación y navegación por roles.

Decisión #9: Se usa st.navigation() para controlar qué páginas ve cada rol
en el sidebar. Esto reemplaza el enfoque anterior de mostrar todas las páginas
y bloquear con require_auth().
"""

import streamlit as st

# Configuración de la página — debe ser la PRIMERA llamada de Streamlit
st.set_page_config(
    page_title="MenuMatch Enterprise",
    page_icon="assets/logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Importar utilidades
from utils.theme import inject_custom_css
from utils.auth import (
    init_users_db,
    get_current_user,
    logout,
    ROLE_ADMIN,
    ROLE_RESTAURANTE,
    ROLE_USUARIO,
)

inject_custom_css()

# Inicializar base de datos de usuarios
init_users_db()

# Inicializar estado de sesión
if "menus" not in st.session_state:
    st.session_state.menus = []

if "restricciones" not in st.session_state:
    st.session_state.restricciones = {
        "presupuesto_max": 15.0,
        "calorias_max": 800,
        "vegetariano": False,
        "vegano": False,
        "sin_gluten": False,
        "sin_lactosa": False,
    }



# ─── Comprobar autenticación y construir navegación por rol ──────────────────
user = get_current_user()

if user is None:
    # ─── No autenticado: solo mostrar Login ──────────────────────────────
    login_page = st.Page("pages/0_Login.py", title="Login", icon=":material/lock:")
    pg = st.navigation([login_page], position="hidden")
    pg.run()

else:
    # ─── Autenticado: navegación filtrada por rol ────────────────────────
    pages = []

    # Inicio — visible para todos los roles
    pages.append(st.Page("pages/1_Inicio.py", title="Inicio", icon=":material/home:"))

    # Cargar Menú — solo restaurante y admin
    if user["role"] in [ROLE_RESTAURANTE, ROLE_ADMIN]:
        pages.append(st.Page(
            "pages/2_Cargar_Menu.py", title="Cargar Menú", icon=":material/restaurant_menu:"
        ))

    # Restricciones, Recomendaciones, Carta, Historial — solo usuario y admin
    if user["role"] in [ROLE_USUARIO, ROLE_ADMIN]:
        pages.append(st.Page(
            "pages/3_Restricciones.py", title="Restricciones", icon=":material/tune:"
        ))
        pages.append(st.Page(
            "pages/4_Recomendaciones.py", title="Recomendaciones", icon=":material/target:"
        ))
        pages.append(st.Page(
            "pages/7_Carta_Completa.py", title="Carta Completa", icon=":material/menu_book:"
        ))
        pages.append(st.Page(
            "pages/5_Historial.py", title="Historial", icon=":material/bar_chart:"
        ))

    # Panel Admin — solo admin
    if user["role"] == ROLE_ADMIN:
        pages.append(st.Page(
            "pages/6_Admin.py", title="Admin", icon=":material/shield_person:"
        ))

    pg = st.navigation(pages)

    # ─── Sidebar: Info del usuario + logout ──────────────────────────────
    role_icon = {"admin": "[ADM]", "restaurante": "[RST]", "usuario": "[USR]"}
    role_label = {
        "admin": "Administrador",
        "restaurante": "Restaurante",
        "usuario": "Usuario",
    }

    with st.sidebar:
        st.divider()

        st.markdown(f"""
            <div style="
                background: #1E293B;
                border-radius: 8px;
                padding: 1rem;
                margin-bottom: 1rem;
                border: 1px solid #334155;
            ">
                <p style="color: #E2E8F0; font-weight: 600; margin: 0 0 0.25rem 0;">
                    {role_icon.get(user['role'], '[USR]')} {user['nombre']}
                </p>
                <p style="color: #94A3B8; font-size: 0.8rem; margin: 0;">
                    @{user['username']} | {role_label.get(user['role'], user['role'])}
                </p>
            </div>
        """, unsafe_allow_html=True)

        if st.button("Cerrar Sesión", use_container_width=True):
            logout()
            st.rerun()

    pg.run()
