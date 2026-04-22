"""
MenuMatch - Página de Inicio
Dashboard principal con resumen y accesos rápidos
"""

import streamlit as st
from utils import inject_custom_css, section_header, metric_card, empty_state
from utils.auth import require_auth, ROLE_ADMIN, ROLE_USUARIO, ROLE_RESTAURANTE
from utils.menu_storage import get_all_menus

inject_custom_css()

# Guardia de autenticación (todos los roles)
user = require_auth()

# Cargar platos del almacén compartido
menus = get_all_menus()

if "restricciones" not in st.session_state:
    st.session_state.restricciones = {
        "presupuesto_max": 15.0,
        "calorias_max": 800,
        "vegetariano": False,
        "vegano": False,
        "sin_gluten": False,
        "sin_lactosa": False,
    }

# Header principal con saludo personalizado
role_greeting = {
    ROLE_ADMIN: "Panel de Administrador",
    ROLE_USUARIO: "Encuentra tu menú ideal",
    ROLE_RESTAURANTE: "Gestiona tus menús",
}
section_header(
    f"Hola, {user['nombre']}",
    role_greeting.get(user["role"], "Tu asistente inteligente para encontrar el menú del día perfecto")
)

# Métricas principales
st.markdown("### Panel de Control")

col1, col2, col3, col4 = st.columns(4)

with col1:
    metric_card(str(len(menus)), "Platos Cargados")

with col2:
    restricciones_activas = sum([
        st.session_state.restricciones["vegetariano"],
        st.session_state.restricciones["vegano"],
        st.session_state.restricciones["sin_gluten"],
        st.session_state.restricciones["sin_lactosa"],
    ])
    metric_card(str(restricciones_activas), "Restricciones Activas")

with col3:
    metric_card(f"€{st.session_state.restricciones['presupuesto_max']:.0f}", "Presupuesto Máximo")

with col4:
    metric_card(f"{st.session_state.restricciones['calorias_max']}", "Límite Calorías")

st.markdown("<br>", unsafe_allow_html=True)

# Acciones rápidas según el rol del usuario
st.markdown("### Acciones Rápidas")

quick_actions = []

# Restaurante y admin: cargar menús
if user["role"] in [ROLE_RESTAURANTE, ROLE_ADMIN]:
    quick_actions.append({
        "title": "Cargar Menús",
        "desc": "Sube archivos CSV o añade platos manualmente",
        "page": "pages/2_Cargar_Menu.py",
        "key": "btn_menu",
    })

# Usuario y admin: restricciones y recomendaciones
if user["role"] in [ROLE_USUARIO, ROLE_ADMIN]:
    quick_actions.append({
        "title": "Configurar Restricciones",
        "desc": "Define presupuesto, calorías y dietas",
        "page": "pages/3_Restricciones.py",
        "key": "btn_restricciones",
    })
    quick_actions.append({
        "title": "Ver Recomendaciones",
        "desc": "Obtén las mejores combinaciones de menú",
        "page": "pages/4_Recomendaciones.py",
        "key": "btn_recomendaciones",
    })

cols = st.columns(len(quick_actions)) if quick_actions else []
for i, action in enumerate(quick_actions):
    with cols[i]:
        st.markdown(f"""
            <div class="menu-card">
                <h3 style="color: #3B82F6; margin-bottom: 0.5rem;">{action['title']}</h3>
                <p style="color: #8B949E; margin-bottom: 1rem;">{action['desc']}</p>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Ir", key=action["key"], use_container_width=True):
            st.switch_page(action["page"])

st.markdown("<br>", unsafe_allow_html=True)

# Estado actual
if len(menus) == 0:
    st.markdown("### Estado Actual")
    empty_state(
        "No hay platos cargados todavía.",
        ""
    )
else:
    st.markdown("### Últimos Platos Añadidos")
    
    # Mostrar los últimos 3 platos
    for plato in menus[-3:]:
        st.markdown(f"""
            <div class="menu-card" style="padding: 1rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #E2E8F0; font-weight: 600;">{plato.get('nombre', 'Sin nombre')}</span>
                    <span style="color: #3B82F6;">€{plato.get('precio', 0):.2f}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

