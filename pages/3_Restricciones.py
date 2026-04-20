"""
MenuMatch - Página de Restricciones
Configuración de presupuesto, calorías y restricciones dietéticas.
Acceso restringido a roles: usuario, admin.
"""

import streamlit as st
from utils import inject_custom_css, section_header
from utils.auth import require_auth, ROLE_ADMIN, ROLE_USUARIO

inject_custom_css()

# Guardia de autenticación — solo usuarios y admins
user = require_auth(allowed_roles=[ROLE_USUARIO, ROLE_ADMIN])

# Inicializar estado
if "restricciones" not in st.session_state:
    st.session_state.restricciones = {
        "presupuesto_max": 15.0,
        "calorias_max": 800,
        "vegetariano": False,
        "vegano": False,
        "sin_gluten": False,
        "sin_lactosa": False,
    }

# Header
section_header(
    "Configurar Restricciones",
    "Define tus preferencias de presupuesto, calorías y dietas"
)

# Contenedor principal
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown("""
        <div class="menu-card">
            <h3 style="color: #3B82F6; margin-bottom: 1.5rem;">Presupuesto</h3>
        </div>
    """, unsafe_allow_html=True)
    
    presupuesto = st.slider(
        "Presupuesto máximo (€)",
        min_value=5.0,
        max_value=30.0,
        value=st.session_state.restricciones["presupuesto_max"],
        step=0.5,
        format="€%.2f"
    )
    st.session_state.restricciones["presupuesto_max"] = presupuesto
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("""
        <div class="menu-card">
            <h3 style="color: #3B82F6; margin-bottom: 1.5rem;">Calorías</h3>
        </div>
    """, unsafe_allow_html=True)
    
    calorias = st.slider(
        "Límite de calorías (kcal)",
        min_value=300,
        max_value=1500,
        value=st.session_state.restricciones["calorias_max"],
        step=50,
        format="%d kcal"
    )
    st.session_state.restricciones["calorias_max"] = calorias

with col_right:
    st.markdown("""
        <div class="menu-card">
            <h3 style="color: #3B82F6; margin-bottom: 1.5rem;">Restricciones Dietéticas</h3>
        </div>
    """, unsafe_allow_html=True)
    
    # Grid de restricciones
    col1, col2 = st.columns(2)
    
    with col1:
        vegetariano = st.checkbox(
            "Vegetariano",
            value=st.session_state.restricciones["vegetariano"],
            help="Excluir platos con carne"
        )
        st.session_state.restricciones["vegetariano"] = vegetariano
        
        sin_gluten = st.checkbox(
            "Sin Gluten",
            value=st.session_state.restricciones["sin_gluten"],
            help="Solo platos aptos para celíacos"
        )
        st.session_state.restricciones["sin_gluten"] = sin_gluten
    
    with col2:
        vegano = st.checkbox(
            "Vegano",
            value=st.session_state.restricciones["vegano"],
            help="Excluir todos los productos de origen animal"
        )
        st.session_state.restricciones["vegano"] = vegano
        
        sin_lactosa = st.checkbox(
            "Sin Lactosa",
            value=st.session_state.restricciones["sin_lactosa"],
            help="Excluir productos lácteos"
        )
        st.session_state.restricciones["sin_lactosa"] = sin_lactosa
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Resumen de restricciones activas
    restricciones_activas = []
    if vegetariano:
        restricciones_activas.append("Vegetariano")
    if vegano:
        restricciones_activas.append("Vegano")
    if sin_gluten:
        restricciones_activas.append("Sin Gluten")
    if sin_lactosa:
        restricciones_activas.append("Sin Lactosa")
    
    if restricciones_activas:
        st.markdown(f"""
            <div style="
                background: #1E293B;
                border-radius: 12px;
                padding: 1rem;
                border-left: 4px solid #3B82F6;
            ">
                <p style="color: #8B949E; margin-bottom: 0.5rem; font-size: 0.875rem;">
                    Restricciones activas:
                </p>
                <p style="color: #E2E8F0; margin: 0;">
                    {" • ".join(restricciones_activas)}
                </p>
            </div>
        """, unsafe_allow_html=True)

# Divider y resumen
st.markdown("<br>", unsafe_allow_html=True)
st.divider()

# Resumen visual
st.markdown("### Resumen de Configuración")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
        <div class="metric-container">
            <p class="metric-value">€{presupuesto:.0f}</p>
            <p class="metric-label">Presupuesto Máximo</p>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
        <div class="metric-container">
            <p class="metric-value">{calorias}</p>
            <p class="metric-label">Calorías Máximas</p>
        </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
        <div class="metric-container">
            <p class="metric-value">{len(restricciones_activas)}</p>
            <p class="metric-label">Filtros Activos</p>
        </div>
    """, unsafe_allow_html=True)

with col4:
    if st.button("Ver Recomendaciones", type="primary", use_container_width=True):
        st.switch_page("pages/4_Recomendaciones.py")

# Información adicional
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
    <div style="
        background: linear-gradient(145deg, #1E293B, #0F172A);
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #334155;
    ">
        <h4 style="color: #3B82F6; margin-bottom: 1rem;">Consejos</h4>
        <ul style="color: #8B949E; margin: 0; padding-left: 1.5rem;">
            <li style="margin-bottom: 0.5rem;">Un presupuesto entre €8-12 suele ofrecer buenas opciones</li>
            <li style="margin-bottom: 0.5rem;">Para una comida equilibrada, considera 600-800 kcal</li>
            <li>Combina restricciones solo cuando sea necesario para más opciones</li>
        </ul>
    </div>
""", unsafe_allow_html=True)
