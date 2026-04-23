"""
MenuMatch - Página Carta Completa
Muestra todos los platos disponibles y permite confeccionar un pedido manualmente
sin usar el motor de recomendaciones.
Acceso restringido a roles: usuario, admin.
"""

import streamlit as st
from utils import inject_custom_css, section_header, empty_state
from utils.auth import require_auth, ROLE_ADMIN, ROLE_USUARIO
from utils.menu_storage import get_all_menus
from utils.database import create_pedido

inject_custom_css()

# Guardia de autenticación — solo usuarios y admins
user = require_auth(allowed_roles=[ROLE_USUARIO, ROLE_ADMIN])

# ─── Área principal ──────────────────────────────────────────────────────────

section_header(
    "Carta Completa",
    "Explora todos los platos disponibles y crea tu propio pedido"
)

# Obtener platos de la BD
menus = get_all_menus()

if len(menus) == 0:
    empty_state("No hay platos cargados en la carta")
    st.info("Un restaurante debe cargar platos desde la página **Cargar Menú**.")
else:
    # Estado para rastrear qué platos están seleccionados
    if "pedido_actual_ids" not in st.session_state:
        st.session_state.pedido_actual_ids = []

    # Crear layout principal
    col_menu, col_padding, col_summary = st.columns([2.5, 0.2, 1.3])

    with col_menu:
        st.markdown("### Selecciona tus platos")
        
        # Opciones de filtrado rápido
        filtro = st.text_input(" Buscar plato...", placeholder="Ej: Ensalada...")

        # Agrupar platos por categoría
        categorias = {}
        for m in menus:
            # Filtrar si hay búsqueda
            if filtro and filtro.lower() not in m.get("nombre", "").lower():
                continue
                
            cat = m.get("categoria", "Principal")
            if cat not in categorias:
                categorias[cat] = []
            categorias[cat].append(m)

        if not categorias:
            st.warning("No se encontraron platos que coincidan con la búsqueda.")

        for cat, platos in categorias.items():
            st.markdown(f"<h4 style='color: #3B82F6; margin-top: 1.5rem; border-bottom: 1px solid #334155; padding-bottom: 0.5rem;'>{cat}</h4>", unsafe_allow_html=True)
            for p in platos:
                col1, col2 = st.columns([0.1, 0.9])
                with col1:
                    is_selected = p['id'] in st.session_state.pedido_actual_ids
                    
                    def build_toggle_fn(pid):
                        def toggle():
                            if pid in st.session_state.pedido_actual_ids:
                                st.session_state.pedido_actual_ids.remove(pid)
                            else:
                                st.session_state.pedido_actual_ids.append(pid)
                        return toggle

                    st.checkbox("", value=is_selected, key=f"chk_{p['id']}", on_change=build_toggle_fn(p['id']))
                with col2:
                    # Renders properties
                    rests = []
                    if p.get("vegetariano"): rests.append("<span class='badge' title='Vegetariano'>🥬</span>")
                    if p.get("sin_gluten"): rests.append("<span class='badge' title='Sin Gluten'>🌾</span>")
                    if p.get("con_lactosa"): rests.append("<span class='badge' title='Contiene Lactosa'>🥛</span>") 
                    if p.get("con_frutos_secos"): rests.append("<span class='badge' title='Contiene Frutos Secos'>🥜</span>")
                    if p.get("con_huevo"): rests.append("<span class='badge' title='Contiene Huevo'>🥚</span>")
                    if p.get("bajo_sal"): rests.append("<span class='badge' title='Bajo en Sal'>🧂</span>")
                    
                    rests_str = "".join(rests)
                    
                    st.markdown(f"**{p.get('nombre', '')}** — <span style='color: #3B82F6; font-weight: bold;'>€{p.get('precio', 0):.2f}</span> — <span style='color: #94A3B8;'>{p.get('calorias', 0)} kcal</span> <span style='margin-left:0.5rem'>{rests_str}</span>", unsafe_allow_html=True)
                    
    with col_summary:
        st.markdown("###  Tu Pedido")
        st.markdown("""
            <div style="
                background: #1E293B;
                border-radius: 12px;
                padding: 1.25rem;
                border: 1px solid #3B82F640;
            ">
        """, unsafe_allow_html=True)
        
        platos_seleccionados = [m for m in menus if m['id'] in st.session_state.pedido_actual_ids]
        
        if not platos_seleccionados:
            st.markdown("<p style='color: #8B949E; text-align: center; margin: 1rem 0;'>Selecciona platos del menú para armar tu pedido.</p>", unsafe_allow_html=True)
        else:
            total_precio = sum(p.get("precio", 0) for p in platos_seleccionados)
            total_calorias = sum(p.get("calorias", 0) for p in platos_seleccionados)
            nombres = [p.get("nombre", "") for p in platos_seleccionados]
            
            st.markdown("<ul style='padding-left: 1.2rem; margin-bottom: 1rem;'>", unsafe_allow_html=True)
            for nombre in nombres:
                st.markdown(f"<li style='color: #E2E8F0; margin-bottom: 0.5rem;'>{nombre}</li>", unsafe_allow_html=True)
            st.markdown("</ul>", unsafe_allow_html=True)
            
            st.markdown("<hr style='border-color: #334155; margin: 1rem 0;'>", unsafe_allow_html=True)
            
            st.markdown(f"""
                <div style='display: flex; justify-content: space-between; margin-bottom: 0.5rem;'>
                    <span style='color: #8B949E;'>Total:</span>
                    <span style='color: #3B82F6; font-size: 1.25rem; font-weight: bold;'>€{total_precio:.2f}</span>
                </div>
                <div style='display: flex; justify-content: space-between; margin-bottom: 1.25rem;'>
                    <span style='color: #8B949E;'>Calorías:</span>
                    <span style='color: #E2E8F0;'>{total_calorias} kcal</span>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("Hacer Pedido", type="primary", use_container_width=True):
                pedido_id = create_pedido(
                    username=user["username"],
                    platos=nombres,
                    precio=total_precio,
                    calorias=total_calorias,
                )
                # Resetea la lista de ids después de pedir
                st.session_state.pedido_actual_ids = []
                st.success("✅ ¡Tu pedido ha sido registrado correctamente!")
        
        st.markdown("</div>", unsafe_allow_html=True)
