"""
MenuMatch - Panel de Administración
Gestión completa de usuarios: crear, editar rol/nombre y eliminar.
Solo accesible para usuarios con rol 'admin'.
"""

import streamlit as st
import pandas as pd
from utils.theme import inject_custom_css
from utils.database import get_all_evaluaciones
from utils.ml_pipeline import get_clean_dataset
from utils.google_sheets import get_all_data_from_sheets
from utils.ml_model import train_and_evaluate_model
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

# ─── Exportar Datos de Investigación ──────────────────────────────────────────
st.markdown("### Exportar Datos de Investigación")

tab_sheets, tab_local = st.tabs(["☁️ Google Sheets (nube)", "🗄️ SQLite (local)"])

# ── Pestaña 1: Google Sheets ──────────────────────────────────────────────────
with tab_sheets:
    st.markdown(
        '<p style="color:#8B949E;font-size:0.875rem;margin-bottom:1rem;">'
        'Datos históricos persistidos en la nube. Incluye todas las evaluaciones, '
        'incluso las de sesiones anteriores que SQLite ya no conserva.</p>',
        unsafe_allow_html=True,
    )
    if st.button("🔄 Cargar datos de Google Sheets", type="primary", key="btn_load_sheets"):
        try:
            with st.spinner("Conectando con Google Sheets..."):
                df_sheets = get_all_data_from_sheets()

            if df_sheets.empty:
                st.info(
                    "La hoja de Google Sheets está vacía. "
                    "Las evaluaciones aparecen aquí en tiempo real."
                )
            else:
                col_info, col_btn = st.columns([2, 1])
                with col_info:
                    st.markdown(
                        f'<div style="background:#1E293B;border-radius:8px;'
                        f'padding:0.75rem 1rem;display:inline-block;">'
                        f'<span style="color:#8B949E;">Registros en la nube: </span>'
                        f'<span style="color:#22C55E;font-weight:600;">{len(df_sheets)}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with col_btn:
                    csv_sheets = df_sheets.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="⬇️ Descargar CSV",
                        data=csv_sheets,
                        file_name="menumatch_sheets_export.csv",
                        mime="text/csv",
                        use_container_width=True,
                        type="secondary",
                        key="dl_sheets",
                    )
                st.markdown("#### Últimos registros")
                st.dataframe(df_sheets.tail(10), use_container_width=True, hide_index=True)

        except ConnectionError as e:
            st.error(
                "❌ No se pudo conectar con Google Sheets.\n\n"
                "**Causa más probable en local:** falta el archivo "
                "`.streamlit/secrets.toml` con las credenciales `GOOGLE_CREDENTIALS`.\n\n"
                f"Detalle técnico: `{e}`"
            )
        except RuntimeError as e:
            st.error(f"❌ Error de red al acceder a Google Sheets: {e}")
    else:
        st.info("Pulsa el botón para conectar con Google Sheets y ver los datos de la nube.")

# ── Pestaña 2: SQLite local ───────────────────────────────────────────────────
with tab_local:
    st.markdown(
        '<p style="color:#8B949E;font-size:0.875rem;margin-bottom:1rem;">'
        'Evaluaciones registradas en la base de datos SQLite de esta sesión. '
        'Se pierden al reiniciar el servidor en Streamlit Cloud.</p>',
        unsafe_allow_html=True,
    )
    evaluaciones_local = get_all_evaluaciones()
    if not evaluaciones_local:
        st.info("No hay evaluaciones en la base de datos local todavía.")
    else:
        df_local = pd.DataFrame(evaluaciones_local)
        # Serializar columnas complejas para el CSV
        for col in ["platos", "restricciones"]:
            if col in df_local.columns:
                df_local[col] = df_local[col].apply(
                    lambda x: " | ".join(x) if isinstance(x, list) else str(x)
                )
        col_info2, col_btn2 = st.columns([2, 1])
        with col_info2:
            st.markdown(
                f'<div style="background:#1E293B;border-radius:8px;'
                f'padding:0.75rem 1rem;display:inline-block;">'
                f'<span style="color:#8B949E;">Registros locales: </span>'
                f'<span style="color:#3B82F6;font-weight:600;">{len(df_local)}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_btn2:
            csv_local = df_local.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Descargar CSV",
                data=csv_local,
                file_name="menumatch_local_export.csv",
                mime="text/csv",
                use_container_width=True,
                type="secondary",
                key="dl_local",
            )
        st.markdown("#### Últimos registros")
        st.dataframe(df_local.tail(10), use_container_width=True, hide_index=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── Datos Preprocesados para Machine Learning ────────────────────────────────
with st.expander("Datos Preprocesados para Machine Learning", expanded=False):
    st.markdown(
        '<p style="color:#8B949E;font-size:0.875rem;margin-bottom:1rem;">'
        'Vista del DataFrame limpio generado por <code>get_clean_dataset()</code>. '
        'Columnas redundantes y no predictivas han sido eliminadas. '
        'Verifica la distribución de clases antes de entrenar el modelo.</p>',
        unsafe_allow_html=True,
    )

    try:
        df_ml = get_clean_dataset()

        if df_ml.empty:
            st.warning(
                "No hay evaluaciones registradas todavía. "
                "El dataset estará disponible cuando los usuarios valoren menús."
            )
        else:
            # ── Métricas de distribución ──────────────────────────────────────
            total_filas = len(df_ml)
            positivos = int((df_ml["satisfied"] == 1).sum())
            negativos = int((df_ml["satisfied"] == 0).sum())

            mc1, mc2, mc3 = st.columns(3)
            with mc1:
                st.metric(
                    label="Total de filas",
                    value=total_filas,
                    help="Número total de evaluaciones procesadas.",
                )
            with mc2:
                st.metric(
                    label="Satisfechos (satisfied = 1)",
                    value=positivos,
                    delta=f"{positivos / total_filas * 100:.1f}%" if total_filas else None,
                    help="Evaluaciones con satisfacción ≥ 4.",
                )
            with mc3:
                st.metric(
                    label="No satisfechos (satisfied = 0)",
                    value=negativos,
                    delta=f"-{negativos / total_filas * 100:.1f}%" if total_filas else None,
                    delta_color="inverse",
                    help="Evaluaciones con satisfacción ≤ 3.",
                )

            st.markdown("<br>", unsafe_allow_html=True)

            # ── DataFrame limpio ──────────────────────────────────────────────
            st.dataframe(
                df_ml,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", width="small"),
                    "calorias": st.column_config.NumberColumn("Calorías", format="%d kcal"),
                    "precio": st.column_config.NumberColumn("Precio", format="%.2f €"),
                    "presupuesto_max": st.column_config.NumberColumn("Presupuesto Máx.", format="%.2f €"),
                    "price_ratio": st.column_config.NumberColumn("Price Ratio", format="%.3f"),
                    "score": st.column_config.NumberColumn("Score Heurístico", format="%.3f"),
                    "recommendation_type": st.column_config.TextColumn("Tipo Recomendación"),
                    "satisfied": st.column_config.NumberColumn("Satisfied", width="small"),
                },
            )

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Botón de entrenamiento ───────────────────────────────────────────
            if st.button("🧠 Entrenar Modelo de IA", type="primary", key="btn_train_ml", use_container_width=True):
                try:
                    with st.spinner("Entrenando modelo..."):
                        resultado = train_and_evaluate_model()

                    if resultado.get("warning"):
                        st.warning(resultado["warning"])

                    st.success("✅ ¡Modelo entrenado y guardado con éxito!")

                    col_acc, col_n, col_train, col_test = st.columns(4)
                    with col_acc:
                        st.metric(
                            label="Accuracy",
                            value=f"{resultado['accuracy'] * 100:.1f}%",
                            help="Porcentaje de predicciones correctas sobre el conjunto de test.",
                        )
                    with col_n:
                        st.metric(
                            label="Dataset total",
                            value=resultado["n_total"],
                            help="Número total de evaluaciones usadas.",
                        )
                    with col_train:
                        st.metric(
                            label="Muestras train",
                            value=resultado["n_train"],
                            help="Registros usados para entrenar el modelo (80%).",
                        )
                    with col_test:
                        st.metric(
                            label="Muestras test",
                            value=resultado["n_test"],
                            help="Registros usados para evaluar el modelo (20%).",
                        )

                    st.markdown("#### Matriz de Confusión")
                    cm_data = resultado["confusion_matrix"]
                    df_cm = pd.DataFrame(
                        cm_data,
                        index=["Real: No satisfecho (0)", "Real: Satisfecho (1)"],
                        columns=["Pred: No satisfecho (0)", "Pred: Satisfecho (1)"],
                    )
                    st.dataframe(df_cm, use_container_width=True)
                    st.markdown(
                        '<p style="color:#8B949E;font-size:0.8rem;margin-top:0.5rem;">'
                        "Diagonal principal = predicciones correctas. "
                        "Fuera de la diagonal = errores del modelo.</p>",
                        unsafe_allow_html=True,
                    )

                    with st.expander("📁 Archivos del modelo guardados"):
                        st.code(
                            f"Modelo:    {resultado['model_path']}\n"
                            f"Escalador: {resultado['scaler_path']}",
                            language="bash",
                        )

                except ValueError as e:
                    st.warning(f"⚠️ {e}")
                except Exception as e:
                    st.error(f"❌ Error durante el entrenamiento: {e}")

    except FileNotFoundError as e:
        st.error(f"Base de datos no encontrada: {e}")
    except Exception as e:
        st.error(f"Error al cargar el dataset ML: {e}")

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
