"""
MenuMatch - Página de Historial
Historial de pedidos realizados, almacenados en SQLite.
Acceso restringido a roles: usuario, admin.
"""

import streamlit as st
from utils import inject_custom_css, section_header, empty_state
from utils.auth import require_auth, ROLE_ADMIN, ROLE_USUARIO
from utils.database import get_pedidos_by_user, update_valoracion

inject_custom_css()

# Guardia de autenticación — solo usuarios y admins
user = require_auth(allowed_roles=[ROLE_USUARIO, ROLE_ADMIN])

# Header
section_header(
    "Historial",
    "Registro de tus selecciones y valoraciones"
)

# Obtener pedidos del usuario desde la BD
pedidos = get_pedidos_by_user(user["username"])

# Contenido principal
if len(pedidos) == 0:
    empty_state(
        "Tu historial está vacío. Selecciona un menú en Recomendaciones para empezar.",
        ""
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Vista previa de cómo se vería
    st.markdown("### Vista Previa")
    st.markdown("""
        <div style="
            background: #1E293B;
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px dashed #334155;
            opacity: 0.7;
        ">
            <p style="color: #8B949E; text-align: center; margin: 0;">
                Aquí aparecerán tus menús seleccionados con:
            </p>
            <div style="display: flex; justify-content: center; gap: 2rem; margin-top: 1rem;">
                <span style="color: #3B82F6;">Fecha</span>
                <span style="color: #3B82F6;">Platos</span>
                <span style="color: #3B82F6;">Valoración</span>
                <span style="color: #3B82F6;">Precio</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
else:
    # Estadísticas
    st.markdown("### Estadísticas")

    total_selecciones = len(pedidos)
    gasto_total = sum([p.get("precio", 0) for p in pedidos])
    pedidos_valorados = [p for p in pedidos if p.get("valoracion", 0) > 0]
    valoracion_media = (
        sum([p["valoracion"] for p in pedidos_valorados]) / len(pedidos_valorados)
        if pedidos_valorados
        else 0
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
            <div class="metric-container">
                <p class="metric-value">{total_selecciones}</p>
                <p class="metric-label">Total Pedidos</p>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
            <div class="metric-container">
                <p class="metric-value">€{gasto_total:.2f}</p>
                <p class="metric-label">Gasto Total</p>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
            <div class="metric-container">
                <p class="metric-value">€{gasto_total/total_selecciones:.2f}</p>
                <p class="metric-label">Gasto Medio</p>
            </div>
        """, unsafe_allow_html=True)

    with col4:
        estrellas = "★" * round(valoracion_media) if valoracion_media > 0 else "—"
        st.markdown(f"""
            <div class="metric-container">
                <p class="metric-value">{estrellas}</p>
                <p class="metric-label">Valoración Media</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Lista de pedidos
    st.markdown("### Historial de Pedidos")

    for pedido in pedidos:
        fecha = pedido.get("fecha", "Sin fecha")
        platos = pedido.get("platos", [])
        precio = pedido.get("precio", 0)
        calorias = pedido.get("calorias", 0)
        valoracion = pedido.get("valoracion", 0)
        pedido_id = pedido.get("id", 0)

        if valoracion > 0:
            estrellas_html = f'<p style="color: #D29922; font-size: 1.5rem; margin: 0;">{"★" * valoracion}</p>'
            sub_html = f'<p style="color: #8B949E; font-size: 0.75rem; margin-top: 0.25rem;">{valoracion}/5</p>'
        else:
            estrellas_html = '<p style="color: #484F58; font-size: 1.5rem; margin: 0;">☆☆☆☆☆</p>'
            sub_html = '<p style="color: #8B949E; font-size: 0.75rem; margin-top: 0.25rem;">Sin valorar</p>'

        st.markdown(f"""
            <div class="menu-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <p style="color: #8B949E; font-size: 0.875rem; margin-bottom: 0.5rem;">
                            {fecha}
                        </p>
                        <h4 style="color: #E2E8F0; margin: 0 0 0.5rem 0;">
                            {" + ".join(platos) if platos else "Menú sin nombre"}
                        </h4>
                        <div style="display: flex; gap: 1.5rem;">
                            <span style="color: #3B82F6;">€{precio:.2f}</span>
                            <span style="color: #8B949E;">{calorias} kcal</span>
                        </div>
                    </div>
                    <div style="text-align: right;">
                        {estrellas_html}
                        {sub_html}
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Valoración interactiva si no está valorado
        if valoracion == 0:
            val_cols = st.columns([2, 1])
            with val_cols[0]:
                nueva_val = st.slider(
                    "Valorar este pedido",
                    min_value=1,
                    max_value=5,
                    value=3,
                    key=f"val_slider_{pedido_id}",
                    label_visibility="collapsed",
                )
            with val_cols[1]:
                stars_label = "\u2605" * nueva_val
                if st.button(
                    f"Valorar {stars_label}",
                    key=f"val_btn_{pedido_id}",
                    use_container_width=True,
                ):
                    update_valoracion(pedido_id, nueva_val)
                    st.success(f"Valoración guardada: {stars_label}")
                    st.rerun()

# Información sobre el sistema de feedback
st.markdown("<br>", unsafe_allow_html=True)
st.divider()
st.markdown("""
    <div style="
        background: linear-gradient(145deg, #1E293B, #0F172A);
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #334155;
    ">
        <h4 style="color: #3B82F6; margin-bottom: 1rem;">Componente de Investigación</h4>
        <p style="color: #8B949E; margin-bottom: 1rem;">
            Este historial alimenta el sistema de aprendizaje automático que mejora
            las recomendaciones basándose en tus preferencias.
        </p>
        <div style="display: flex; gap: 2rem; flex-wrap: wrap;">
            <div>
                <span style="color: #58A6FF; font-weight: 600;">Métrica: Acierto</span>
                <p style="color: #8B949E; font-size: 0.875rem; margin: 0.25rem 0 0 0;">
                    % de recomendaciones valoradas ≥4★
                </p>
            </div>
            <div>
                <span style="color: #58A6FF; font-weight: 600;">Métrica: Satisfacción</span>
                <p style="color: #8B949E; font-size: 0.875rem; margin: 0.25rem 0 0 0;">
                    Escala Likert promedio (1-5)
                </p>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)
