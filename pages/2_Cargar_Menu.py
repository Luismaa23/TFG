"""
MenuMatch - Página de Carga de Menús
Subida de CSV y entrada manual de platos.
Acceso restringido a roles: restaurante, admin.

Los platos se persisten en data/menus.json (compartido) para que
todos los usuarios puedan verlos (Decisión #10).

Decisión #12: Se añaden 4 nuevas restricciones alimentarias
(con_lactosa, con_frutos_secos, con_huevo, bajo_sal) requeridas
por el modelo de Machine Learning.
"""

import streamlit as st
import pandas as pd
from utils import inject_custom_css, section_header, menu_card, empty_state
from utils.auth import require_auth, ROLE_ADMIN, ROLE_RESTAURANTE
from utils.menu_storage import get_all_menus, add_menu_item, add_menu_items, clear_all_menus
from utils.database import get_all_evaluaciones

inject_custom_css()

# Guardia de autenticación — solo restaurantes y admins
user = require_auth(allowed_roles=[ROLE_RESTAURANTE, ROLE_ADMIN])

# Header
section_header(
    "Cargar Menús",
    "Sube archivos CSV o añade platos manualmente"
)

# Tabs para diferentes métodos de carga
tab_csv, tab_manual = st.tabs(["Subir CSV", "Entrada Manual"])

with tab_csv:
    st.markdown("""
        <div style="
            background: #1E293B;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border: 1px solid #334155;
        ">
            <h4 style="color: #3B82F6; margin-bottom: 0.5rem;">Formato esperado del CSV</h4>
            <p style="color: #8B949E; margin-bottom: 1rem;">
                El archivo debe contener las siguientes columnas:
            </p>
            <code style="
                background: #0F172A;
                padding: 0.5rem 1rem;
                border-radius: 6px;
                color: #3B82F6;
            ">nombre, precio, calorias, vegetariano, sin_gluten, con_lactosa, con_frutos_secos, con_huevo, bajo_sal, categoria</code>
        </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Arrastra tu archivo CSV aquí",
        type=["csv"],
        help="Formato: nombre, precio, calorias, vegetariano, sin_gluten, con_lactosa, con_frutos_secos, con_huevo, bajo_sal, categoria"
    )

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)

            st.markdown("### Vista Previa")
            st.dataframe(
                df.head(10),
                use_container_width=True,
                hide_index=True,
            )

            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("Importar Platos", type="primary", use_container_width=True):
                    nuevos_platos = df.to_dict('records')
                    count = add_menu_items(nuevos_platos, uploaded_by=user["username"])
                    st.success(f"{count} platos importados correctamente")
                    st.rerun()

            with col2:
                st.markdown(f"""
                    <div style="
                        background: #1E293B;
                        border-radius: 8px;
                        padding: 0.75rem 1rem;
                        display: inline-block;
                    ">
                        <span style="color: #8B949E;">Platos encontrados: </span>
                        <span style="color: #3B82F6; font-weight: 600;">{len(df)}</span>
                    </div>
                """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error al leer el archivo: {str(e)}")

with tab_manual:
    st.markdown("### Añadir Nuevo Plato")

    with st.form("nuevo_plato", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            nombre = st.text_input("Nombre del plato *", placeholder="Ej: Ensalada César")
            precio = st.number_input("Precio (€) *", min_value=0.0, max_value=100.0, value=8.50, step=0.50)
            calorias = st.number_input("Calorías *", min_value=0, max_value=2000, value=350, step=10)

        with col2:
            categoria = st.selectbox(
                "Categoría",
                ["Primero", "Segundo", "Postre", "Bebida", "Entrante", "Principal"]
            )
            st.markdown("<br>", unsafe_allow_html=True)
            # Fila 1: 3 restricciones
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                vegetariano = st.checkbox("Vegetariano")
            with col_r2:
                sin_gluten = st.checkbox("Sin Gluten")
            with col_r3:
                con_lactosa = st.checkbox("Contiene Lactosa")
            # Fila 2: 3 restricciones
            col_r4, col_r5, col_r6 = st.columns(3)
            with col_r4:
                con_frutos_secos = st.checkbox("Contiene Frutos Secos")
            with col_r5:
                con_huevo = st.checkbox("Contiene Huevo")
            with col_r6:
                bajo_sal = st.checkbox("Bajo en Sal")

        submitted = st.form_submit_button("Añadir Plato", type="primary", use_container_width=True)

        if submitted:
            if nombre:
                nuevo_plato = {
                    "nombre": nombre,
                    "precio": precio,
                    "calorias": calorias,
                    "categoria": categoria,
                    "vegetariano": vegetariano,
                    "sin_gluten": sin_gluten,
                    "con_lactosa": con_lactosa,
                    "con_frutos_secos": con_frutos_secos,
                    "con_huevo": con_huevo,
                    "bajo_sal": bajo_sal,
                }
                add_menu_item(nuevo_plato, uploaded_by=user["username"])
                st.success(f"'{nombre}' añadido correctamente")
                st.rerun()
            else:
                st.error("El nombre del plato es obligatorio")

# Mostrar platos cargados
st.markdown("<br>", unsafe_allow_html=True)
st.divider()
st.markdown("### Platos Cargados")

# Leer platos del almacén compartido
all_menus = get_all_menus()

if len(all_menus) == 0:
    empty_state("No hay platos cargados todavía")
else:
    # Filtros
    col_filter1, col_filter2, col_filter3 = st.columns([2, 1, 1])

    with col_filter1:
        busqueda = st.text_input("Buscar plato", placeholder="Escribe para filtrar...")

    with col_filter2:
        filtro_categoria = st.selectbox(
            "Categoría",
            ["Todas"] + list(set([p.get("categoria", "Sin categoría") for p in all_menus]))
        )

    with col_filter3:
        if st.button("Limpiar Todo", type="secondary", use_container_width=True):
            clear_all_menus()
            st.rerun()

    # Filtrar platos
    platos_filtrados = all_menus

    if busqueda:
        platos_filtrados = [p for p in platos_filtrados if busqueda.lower() in p.get("nombre", "").lower()]

    if filtro_categoria != "Todas":
        platos_filtrados = [p for p in platos_filtrados if p.get("categoria") == filtro_categoria]

    # Mostrar platos en grid
    cols = st.columns(3)
    for idx, plato in enumerate(platos_filtrados):
        with cols[idx % 3]:
            restricciones = []
            if plato.get("vegetariano"):
                restricciones.append("vegetariano")
            if plato.get("sin_gluten"):
                restricciones.append("sin_gluten")
            if plato.get("con_lactosa"):
                restricciones.append("con_lactosa")
            if plato.get("con_frutos_secos"):
                restricciones.append("con_frutos_secos")
            if plato.get("con_huevo"):
                restricciones.append("con_huevo")
            if plato.get("bajo_sal"):
                restricciones.append("bajo_sal")

            menu_card(
                nombre=plato.get("nombre", "Sin nombre"),
                precio=plato.get("precio", 0),
                calorias=plato.get("calorias", 0),
                restricciones=restricciones if restricciones else None
            )

    st.markdown(f"""
        <div style="
            text-align: center;
            padding: 1rem;
            color: #8B949E;
        ">
            Mostrando {len(platos_filtrados)} de {len(all_menus)} platos
        </div>
    """, unsafe_allow_html=True)


# ─── Exportar Datos de Investigación (solo admin) ────────────────────────────
if user["role"] == ROLE_ADMIN:
    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    section_header(
        "Exportar Datos de Investigación",
        "Descarga las valoraciones de los usuarios como CSV para análisis offline"
    )

    st.markdown("""
<div style="
    background: #1E293B;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    border: 1px solid #334155;
">
    <h4 style="color: #F59E0B; margin-bottom: 0.5rem;">Sistema de archivos efímero</h4>
    <p style="color: #8B949E; margin: 0;">
        Streamlit Community Cloud reinicia los contenedores periódicamente.
        Las evaluaciones almacenadas en SQLite se perderán tras cada reinicio.
        Usa este botón para exportar los datos de investigación antes de que eso ocurra.
    </p>
</div>
    """, unsafe_allow_html=True)

    evaluaciones = get_all_evaluaciones()

    if len(evaluaciones) == 0:
        empty_state("No hay evaluaciones registradas todavía")
    else:
        df_eval = pd.DataFrame(evaluaciones)

        # Convertir la columna 'platos' (lista) a texto separado por ' | '
        if "platos" in df_eval.columns:
            df_eval["platos"] = df_eval["platos"].apply(
                lambda x: " | ".join(x) if isinstance(x, list) else str(x)
            )

        # Convertir la columna 'restricciones' (dict) a JSON string
        if "restricciones" in df_eval.columns:
            df_eval["restricciones"] = df_eval["restricciones"].apply(
                lambda x: str(x) if not isinstance(x, str) else x
            )

        col_info, col_btn = st.columns([2, 1])

        with col_info:
            st.markdown(f"""
<div style="
    background: #1E293B;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    display: inline-block;
">
    <span style="color: #8B949E;">Registros disponibles: </span>
    <span style="color: #3B82F6; font-weight: 600;">{len(df_eval)}</span>
</div>
            """, unsafe_allow_html=True)

        with col_btn:
            csv_data = df_eval.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Descargar CSV",
                data=csv_data,
                file_name="dataset_evaluaciones.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary",
            )

        # Vista previa de los datos
        st.markdown("### Vista Previa")
        st.dataframe(
            df_eval.head(10),
            use_container_width=True,
            hide_index=True,
        )

