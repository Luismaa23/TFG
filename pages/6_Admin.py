"""
MenuMatch - Panel de Administración
Gestión completa de usuarios: crear, editar rol/nombre y eliminar.
Solo accesible para usuarios con rol 'admin'.
"""

import os
import streamlit as st
import pandas as pd
from utils.theme import inject_custom_css
from utils.database import get_all_evaluaciones, get_connection
from utils.ml_pipeline import get_clean_dataset
from utils.google_sheets import get_all_data_from_sheets
from utils.ml_model import train_and_evaluate_model, load_model_and_scaler, MODEL_PATH, SCALER_PATH
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

# ─── 1. Cabecera Fija ────────────────────────────────────────────────────────
section_header(
    "Panel de Control - MenuMatch",
    f"Bienvenido, {user['nombre']} — Gestión completa del sistema"
)

# Métricas Flash
all_users = get_all_users()
total_users = len(all_users)

evaluaciones_local = get_all_evaluaciones()
total_evaluaciones = len(evaluaciones_local)

ratio_ab = "50% / 50%"

# Accuracy de la IA
model, scaler = load_model_and_scaler()
accuracy_text = "No disponible"
if model is not None:
    try:
        df_ml = get_clean_dataset()
        if not df_ml.empty:
            X = df_ml[["calorias", "price_ratio", "score"]].copy()
            y = df_ml["satisfied"].copy()
            X_scaled = scaler.transform(X)
            from sklearn.metrics import accuracy_score
            acc = accuracy_score(y, model.predict(X_scaled))
            accuracy_text = f"{acc * 100:.1f}%"
        else:
            accuracy_text = "Modelo Entrenado"
    except Exception:
        accuracy_text = "Error al calcular"

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Usuarios", total_users)
with col2:
    st.metric("Total Evaluaciones", total_evaluaciones)
with col3:
    st.metric("Ratio Test A/B", ratio_ab)
with col4:
    st.metric("Accuracy IA", accuracy_text)

st.markdown("<br>", unsafe_allow_html=True)

# ─── 2. Estructura de Pestañas ───────────────────────────────────────────────
tab_data, tab_ia, tab_config = st.tabs([
    "Gestión de Datos",
    "Inteligencia Artificial",
    "Configuración y Logs"
])

# ─── PESTAÑA 1: Gestión de Datos ──────────────────────────────────────────────
with tab_data:
    st.markdown("### Exportar Datos de Investigación")
    
    subtab_sheets, subtab_local = st.tabs(["Cloud (Google Sheets)", "Local (SQLite)"])
    
    with subtab_sheets:
        st.markdown("Datos históricos persistidos en la nube. Incluye todas las evaluaciones.")
        if st.button("Cargar datos de Google Sheets", type="primary", key="btn_load_sheets"):
            try:
                with st.spinner("Conectando con Google Sheets..."):
                    df_sheets = get_all_data_from_sheets()

                if df_sheets.empty:
                    st.info("La hoja de Google Sheets está vacía.")
                else:
                    col_info, col_btn = st.columns([2, 1])
                    with col_info:
                        st.write(f"Registros en la nube: {len(df_sheets)}")
                    with col_btn:
                        csv_sheets = df_sheets.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="Descargar CSV",
                            data=csv_sheets,
                            file_name="menumatch_sheets_export.csv",
                            mime="text/csv",
                            use_container_width=True,
                            type="secondary",
                            key="dl_sheets",
                        )
                    st.markdown("#### Últimos registros")
                    st.dataframe(df_sheets.tail(10), use_container_width=True, hide_index=True)

            except Exception as e:
                st.error(f"Error de red al acceder a Google Sheets: {e}")
        else:
            st.info("Pulsa el botón para conectar con Google Sheets.")
            
    with subtab_local:
        st.markdown("Evaluaciones registradas en la base de datos SQLite de esta sesión.")
        if not evaluaciones_local:
            st.info("No hay evaluaciones en la base de datos local todavía.")
        else:
            df_local = pd.DataFrame(evaluaciones_local)
            for col in ["platos", "restricciones"]:
                if col in df_local.columns:
                    df_local[col] = df_local[col].apply(
                        lambda x: " | ".join(x) if isinstance(x, list) else str(x)
                    )
            col_info2, col_btn2 = st.columns([2, 1])
            with col_info2:
                st.write(f"Registros locales: {len(df_local)}")
            with col_btn2:
                csv_local = df_local.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Descargar CSV",
                    data=csv_local,
                    file_name="menumatch_local_export.csv",
                    mime="text/csv",
                    use_container_width=True,
                    type="secondary",
                    key="dl_local",
                )
            st.markdown("#### Últimos registros")
            st.dataframe(df_local.tail(10), use_container_width=True, hide_index=True)
            
    st.markdown("---")
    st.markdown("### Base de Datos Principal: Menús (Últimas inserciones)")
    try:
        conn = get_connection()
        df_menus_local = pd.read_sql("SELECT * FROM menus ORDER BY id DESC LIMIT 5", conn)
        conn.close()
        st.dataframe(df_menus_local, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Error al cargar la tabla de menús: {e}")


# ─── PESTAÑA 2: Inteligencia Artificial ───────────────────────────────────────
with tab_ia:
    st.markdown("### Entrenamiento del Modelo ML")
    st.markdown(
        "Vista del DataFrame limpio generado. Columnas redundantes han sido eliminadas. "
        "Verifica la distribución de clases antes de entrenar el modelo."
    )

    try:
        df_ml = get_clean_dataset()

        if df_ml.empty:
            st.warning("No hay evaluaciones registradas. El dataset estará disponible cuando los usuarios valoren menús.")
        else:
            total_filas = len(df_ml)
            positivos = int((df_ml["satisfied"] == 1).sum())
            negativos = int((df_ml["satisfied"] == 0).sum())

            mc1, mc2, mc3 = st.columns(3)
            with mc1:
                st.metric(label="Total de filas", value=total_filas)
            with mc2:
                st.metric(label="Satisfechos (1)", value=positivos)
            with mc3:
                st.metric(label="No satisfechos (0)", value=negativos)

            st.dataframe(
                df_ml.head(10),
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("Entrenar Modelo de IA", type="primary", key="btn_train_ml", use_container_width=True):
                try:
                    with st.spinner("Entrenando modelo..."):
                        resultado = train_and_evaluate_model()

                    if resultado.get("warning"):
                        st.warning(resultado["warning"])

                    st.success("Modelo entrenado y guardado con éxito.")

                    col_res1, col_res2 = st.columns([1, 1])
                    with col_res1:
                        st.markdown("#### Métricas")
                        st.write(f"**Accuracy:** {resultado['accuracy'] * 100:.1f}%")
                        st.write(f"**Muestras train:** {resultado['n_train']}")
                        st.write(f"**Muestras test:** {resultado['n_test']}")
                        
                    with col_res2:
                        st.markdown("#### Matriz de Confusión")
                        cm_data = resultado["confusion_matrix"]
                        df_cm = pd.DataFrame(
                            cm_data,
                            index=["Real: No satisfecho (0)", "Real: Satisfecho (1)"],
                            columns=["Pred: No satisfecho (0)", "Pred: Satisfecho (1)"],
                        )
                        st.dataframe(df_cm, use_container_width=True)

                except ValueError as e:
                    st.warning(f"Advertencia: {e}")
                except Exception as e:
                    st.error(f"Error durante el entrenamiento: {e}")

    except Exception as e:
        st.error(f"Error al cargar el dataset ML: {e}")


# ─── PESTAÑA 3: Configuración y Logs ──────────────────────────────────────────
with tab_config:
    with st.container():
        st.markdown("### Gestión de Usuarios")
        
        with st.expander("Crear Nuevo Usuario", expanded=False):
            with st.form("admin_create_user_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    new_nombre = st.text_input("Nombre completo *")
                    new_username = st.text_input("Nombre de usuario *")
                with col2:
                    new_password = st.text_input("Contraseña *", type="password")
                    new_role = st.selectbox("Rol *", options=ALL_ROLES)
            
                create_submit = st.form_submit_button("Crear Usuario", type="primary", use_container_width=True)
                if create_submit:
                    success, msg = admin_create_user(new_username, new_password, new_role, new_nombre)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                        
        st.markdown("#### Usuarios Registrados")
        if not all_users:
            st.info("No hay usuarios registrados.")
        else:
            for username, data in all_users.items():
                is_self = username == user["username"]
                
                with st.container(border=True):
                    col_info, col_status = st.columns([4, 1])
                    with col_info:
                        st.markdown(f"#### {data['nombre']} {'**(Tú)**' if is_self else ''}")
                        st.markdown(f"**Usuario:** `@{username}` &nbsp;|&nbsp; **Rol:** `{data['role'].title()}`")
                    
                    with st.expander("Gestionar Usuario", expanded=False):
                        edit_col1, edit_col2, edit_col3 = st.columns([3, 2, 2])
                        with edit_col1:
                            edited_nombre = st.text_input("Modificar Nombre", value=data["nombre"], key=f"nombre_{username}")
                            if edited_nombre != data["nombre"]:
                                if st.button("Guardar Nombre", key=f"save_nombre_{username}", type="primary", use_container_width=True):
                                    success, msg = update_user_nombre(username, edited_nombre)
                                    if success:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                        with edit_col2:
                            new_role = st.selectbox("Modificar Rol", options=ALL_ROLES, index=ALL_ROLES.index(data["role"]), key=f"role_{username}")
                            if new_role != data["role"]:
                                if st.button("Guardar Rol", key=f"save_role_{username}", type="primary", use_container_width=True):
                                    success, msg = update_user_role(username, new_role)
                                    if success:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                        with edit_col3:
                            st.write("Acciones")
                            if not is_self:
                                if st.button("Eliminar Usuario", key=f"del_{username}", use_container_width=True):
                                    success, msg = delete_user(username)
                                    if success:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            else:
                                st.info("Cuenta actual")

    st.markdown("### Rutas del Sistema")
    st.code(f"Modelo: {MODEL_PATH}\nEscalador: {SCALER_PATH}", language="bash")
