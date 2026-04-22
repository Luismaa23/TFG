"""
MenuMatch - Página de Recomendaciones (Motor Heurístico)
Encuentra tu menú del día óptimo mediante un algoritmo basado en reglas.
Acceso restringido a roles: usuario, admin.

Decisión #13: Motor de recomendación heurístico con filtrado estricto
y puntuación ponderada. Los parámetros se introducen directamente
en el sidebar de esta página para una interacción más directa.
"""

import streamlit as st
from utils import inject_custom_css, section_header, empty_state
from utils.auth import require_auth, ROLE_ADMIN, ROLE_USUARIO
from utils.menu_storage import get_all_menus
from utils.database import create_pedido, create_evaluacion
from utils.google_sheets import save_to_google_sheets
from utils.recomendador_heuristico import (
    recomendar_menu_heuristico,
    recomendar_top_n,
    generar_combinaciones_menu,
)

inject_custom_css()

# Guardia de autenticación — solo usuarios y admins
user = require_auth(allowed_roles=[ROLE_USUARIO, ROLE_ADMIN])


# ─── Sidebar: Parámetros del usuario ─────────────────────────────────────────

# Leer defaults de session_state si existen (desde la página Restricciones)
defaults = st.session_state.get("restricciones", {})

with st.sidebar:
    st.markdown("""
        <div style="
            background: linear-gradient(135deg, #3B82F620, #2563EB20);
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
            border: 1px solid #3B82F640;
        ">
            <h3 style="color: #3B82F6; margin: 0; font-size: 1.1rem;">
                 Configura tu búsqueda
            </h3>
            <p style="color: #8B949E; margin: 0.25rem 0 0 0; font-size: 0.8rem;">
                Ajusta tus preferencias y pulsa buscar
            </p>
        </div>
    """, unsafe_allow_html=True)

    # ── Presupuesto ──
    st.markdown("#####  Presupuesto")
    presupuesto = st.slider(
        "Presupuesto máximo (€)",
        min_value=5.0,
        max_value=30.0,
        value=defaults.get("presupuesto_max", 15.0),
        step=0.50,
        format="€%.2f",
    )

    # ── Calorías ──
    st.markdown("#####  Calorías Objetivo")
    calorias_objetivo = st.number_input(
        "Calorías objetivo (kcal)",
        min_value=300,
        max_value=2000,
        value=defaults.get("calorias_max", 700),
        step=50,
        help="El algoritmo penaliza los menús que se alejen de este valor",
    )

    st.divider()

    # ── Restricciones dietéticas ──
    st.markdown("#####  Restricciones Dietéticas")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        rest_vegetariano = st.checkbox(
            " Vegetariano",
            value=defaults.get("vegetariano", False),
        )
        rest_sin_gluten = st.checkbox(
            " Sin Gluten",
            value=defaults.get("sin_gluten", False),
        )
        rest_sin_lactosa = st.checkbox(
            " Sin Lactosa",
            value=defaults.get("sin_lactosa", False),
        )
    with col_s2:
        rest_sin_frutos_secos = st.checkbox(
            " Sin Frutos Secos",
            value=defaults.get("sin_frutos_secos", False),
        )
        rest_sin_huevo = st.checkbox(
            " Sin Huevo",
            value=defaults.get("sin_huevo", False),
        )
        rest_bajo_sal = st.checkbox(
            " Bajo en Sal",
            value=defaults.get("bajo_sal", False),
        )

    st.divider()

    # ── Pesos del algoritmo (avanzado) ──
    with st.expander(" Pesos del algoritmo"):
        st.caption("Ajusta la importancia de cada factor en la puntuación")
        w1 = st.slider("Satisfacción (w₁)", 0.0, 1.0, 0.5, 0.05)
        w2 = st.slider("Precio (w₂)", 0.0, 1.0, 0.3, 0.05)
        w3 = st.slider("Calorías (w₃)", 0.0, 1.0, 0.2, 0.05)


# ─── Área principal ──────────────────────────────────────────────────────────

section_header(
    "Tu Menú del Día Óptimo",
    "Encuentra la mejor combinación según tus preferencias"
)

# Obtener platos de la BD
menus = get_all_menus()

if len(menus) == 0:
    empty_state("No hay platos cargados en el sistema")
    st.info(
        "Un restaurante debe cargar platos desde la página **Cargar Menú** "
        "antes de poder generar recomendaciones."
    )
else:
    # ── Resumen de filtros activos ──
    filtros_resumen = []
    filtros_resumen.append(f" Máx €{presupuesto:.0f}")
    filtros_resumen.append(f" Objetivo {calorias_objetivo} kcal")
    if rest_vegetariano:
        filtros_resumen.append(" Vegetariano")
    if rest_sin_gluten:
        filtros_resumen.append(" Sin Gluten")
    if rest_sin_lactosa:
        filtros_resumen.append(" Sin Lactosa")
    if rest_sin_frutos_secos:
        filtros_resumen.append(" Sin Frutos Secos")
    if rest_sin_huevo:
        filtros_resumen.append(" Sin Huevo")
    if rest_bajo_sal:
        filtros_resumen.append(" Bajo en Sal")

    badges_html = "".join(
        f'<span style="'
        f"background: #3B82F615; border: 1px solid #3B82F640; "
        f"color: #3B82F6; padding: 0.35rem 0.75rem; border-radius: 20px; "
        f'font-size: 0.85rem; white-space: nowrap;">{f}</span>'
        for f in filtros_resumen
    )
    st.markdown(f"""
        <div style="
            background: #1E293B;
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin-bottom: 1.5rem;
            border: 1px solid #334155;
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            align-items: center;
        ">
            <span style="color: #8B949E; margin-right: 0.5rem;">Filtros:</span>
            {badges_html}
        </div>
    """, unsafe_allow_html=True)

    # ── Botón principal ──
    buscar = st.button(
        "  Buscar Menú Óptimo",
        type="primary",
        use_container_width=True,
    )

    if buscar:
        # Construir dict de restricciones del usuario
        restricciones = {
            "vegetariano": rest_vegetariano,
            "sin_gluten": rest_sin_gluten,
            "sin_lactosa": rest_sin_lactosa,
            "sin_frutos_secos": rest_sin_frutos_secos,
            "sin_huevo": rest_sin_huevo,
            "bajo_sal": rest_bajo_sal,
        }

        # Generar combinaciones de menú a partir de los platos
        combinaciones = generar_combinaciones_menu(menus)

        # Ejecutar motor heurístico
        resultado = recomendar_menu_heuristico(
            menus_disponibles=combinaciones,
            presupuesto_usuario=presupuesto,
            calorias_objetivo=calorias_objetivo,
            restricciones_usuario=restricciones,
            w1=w1, w2=w2, w3=w3,
        )

        # Top N para alternativas
        top_n = recomendar_top_n(
            menus_disponibles=combinaciones,
            presupuesto_usuario=presupuesto,
            calorias_objetivo=calorias_objetivo,
            restricciones_usuario=restricciones,
            n=6,
            w1=w1, w2=w2, w3=w3,
        )

        # Guardar en session_state para persistir tras rerun
        st.session_state.reco_resultado = resultado
        st.session_state.reco_top = top_n
        st.session_state.reco_combinaciones_total = len(combinaciones)
        st.session_state.reco_validos = len(top_n)

    # ─── Mostrar resultados (persisten en session_state) ─────────────────
    if "reco_resultado" in st.session_state:
        resultado = st.session_state.reco_resultado
        top_n = st.session_state.get("reco_top", [])
        total_combos = st.session_state.get("reco_combinaciones_total", 0)
        validos = st.session_state.get("reco_validos", 0)

        if resultado is None:
            # ── Sin resultados ──
            st.warning(" Ningún menú cumple con tus restricciones actuales.")
            st.markdown("""
                <div style="
                    background: #1E293B;
                    border-radius: 12px;
                    padding: 1.5rem;
                    margin-top: 1rem;
                    border-left: 4px solid #D29922;
                ">
                    <h4 style="color: #D29922; margin-bottom: 1rem;">
                         Sugerencias para obtener resultados
                    </h4>
                    <ul style="color: #8B949E; margin: 0; padding-left: 1.5rem;">
                        <li style="margin-bottom: 0.5rem;">
                            Aumenta el presupuesto máximo en el sidebar
                        </li>
                        <li style="margin-bottom: 0.5rem;">
                            Desactiva algunas restricciones dietéticas
                        </li>
                        <li>
                            Pide al restaurante que cargue más platos variados
                        </li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)

        else:
            # ── Resultado principal ──
            menu_optimo, score = resultado

            st.success(" ¡Menú óptimo encontrado!")
            st.markdown("<br>", unsafe_allow_html=True)

            # ── Card hero del menú recomendado ──
            platos_list = menu_optimo.get("platos", [menu_optimo.get("nombre", "")])
            platos_html = "".join(
                f'<li style="color: #E2E8F0; padding: 0.4rem 0; '
                f'border-bottom: 1px solid #33415520; font-size: 1.05rem;">'
                f" {p}</li>"
                for p in platos_list
            )

            # Construir badges de restricciones del menú
            rests = []
            if menu_optimo.get("vegetariano"):
                rests.append("<span class='badge' title='Vegetariano'>🥬</span>")
            if menu_optimo.get("sin_gluten"):
                rests.append("<span class='badge' title='Sin Gluten'>🌾</span>")
            if not menu_optimo.get("con_lactosa"):
                rests.append("<span class='badge' title='Libre de Lactosa'>🥛</span>")
            if not menu_optimo.get("con_frutos_secos"):
                rests.append("<span class='badge' title='Libre de Frutos Secos'>🥜</span>")
            if not menu_optimo.get("con_huevo"):
                rests.append("<span class='badge' title='Libre de Huevo'>🥚</span>")
            if menu_optimo.get("bajo_sal"):
                rests.append("<span class='badge' title='Bajo en Sal'>🧂</span>")

            rests_html = "".join(rests)

            # Determinar color del score
            score_pct = max(0, min(100, score * 100 / 1.5))
            if score_pct >= 70:
                score_color = "#2EA043"
                score_label = "Excelente"
            elif score_pct >= 45:
                score_color = "#D29922"
                score_label = "Bueno"
            else:
                score_color = "#F85149"
                score_label = "Aceptable"

            st.markdown(f"""
                <div style="
                    background: linear-gradient(145deg, #1E293B, #0F172A);
                    border-radius: 16px;
                    padding: 2rem;
                    border: 2px solid #3B82F640;
                    position: relative;
                    overflow: hidden;
                ">
                    <div style="
                        position: absolute;
                        top: 0;
                        right: 0;
                        background: linear-gradient(135deg, #3B82F6, #2563EB);
                        color: #0F172A;
                        padding: 0.5rem 1.5rem;
                        border-radius: 0 16px 0 16px;
                        font-weight: 700;
                        font-size: 0.85rem;
                    "> MEJOR VALOR</div>
                    <h2 style="color: #3B82F6; margin: 0 0 1.25rem 0; font-size: 1.4rem;">
                        Menú Recomendado
                    </h2>
                    <ul style="list-style: none; padding: 0; margin: 0 0 1.5rem 0;">
                        {platos_html}
                    </ul>
                    <div style="display: flex; gap: 0.4rem; flex-wrap: wrap; margin-bottom: 1.5rem;">
                        {rests_html}
                    </div>
                    <div style="
                        display: flex;
                        gap: 2rem;
                        padding-top: 1.25rem;
                        border-top: 1px solid #334155;
                        flex-wrap: wrap;
                    ">
                        <div>
                            <span style="color: #8B949E; font-size: 0.85rem;">Precio Total</span>
                            <p style="color: #3B82F6; font-size: 1.8rem; font-weight: 700; margin: 0.25rem 0 0 0;">
                                €{menu_optimo.get('precio', 0):.2f}
                            </p>
                        </div>
                        <div>
                            <span style="color: #8B949E; font-size: 0.85rem;">Calorías</span>
                            <p style="color: #E2E8F0; font-size: 1.8rem; font-weight: 700; margin: 0.25rem 0 0 0;">
                                {menu_optimo.get('calorias', 0)} kcal
                            </p>
                        </div>
                        <div>
                            <span style="color: #8B949E; font-size: 0.85rem;">Puntuación</span>
                            <p style="color: {score_color}; font-size: 1.8rem; font-weight: 700; margin: 0.25rem 0 0 0;">
                                {score:.3f}
                            </p>
                            <span style="color: {score_color}; font-size: 0.75rem;">{score_label}</span>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Botón de seleccionar menú ──
            col_select, col_regen = st.columns([2, 1])
            with col_select:
                if st.button(
                    " Seleccionar este menú",
                    type="primary",
                    use_container_width=True,
                ):
                    pedido_id = create_pedido(
                        username=user["username"],
                        platos=platos_list,
                        precio=menu_optimo.get("precio", 0),
                        calorias=menu_optimo.get("calorias", 0),
                    )
                    st.success(f" ¡Pedido #{pedido_id} registrado correctamente!")

            with col_regen:
                if st.button(" Regenerar", use_container_width=True):
                    # Limpiar resultados previos para forzar nueva búsqueda
                    for key in ["reco_resultado", "reco_top",
                                "reco_combinaciones_total", "reco_validos"]:
                        st.session_state.pop(key, None)
                    st.rerun()

            # ── Formulario de evaluación (feedback para ML) ──
            st.divider()
            st.subheader("Ayúdanos a mejorar")
            st.write("¿Qué te parece esta recomendación principal?")

            with st.form("formulario_evaluacion"):
                satisfaccion = st.slider(
                    "1. Satisfacción general con este menú",
                    1, 5, 3,
                    help="1 = Nada satisfecho, 5 = Muy satisfecho",
                )
                calidad_precio_val = st.slider(
                    "2. Relación calidad-precio",
                    1, 5, 3,
                    help="1 = Muy cara, 5 = Excelente relación",
                )
                elegiria_real = st.radio(
                    "3. ¿Elegirías realmente este menú?",
                    ["Sí", "No"],
                    horizontal=True,
                )

                submitted_eval = st.form_submit_button(
                    "Enviar valoración", type="primary", use_container_width=True,
                )

                if submitted_eval:
                    # Construir dict de restricciones vigentes para contexto ML
                    restricciones_snapshot = {
                        "vegetariano": rest_vegetariano,
                        "sin_gluten": rest_sin_gluten,
                        "sin_lactosa": rest_sin_lactosa,
                        "sin_frutos_secos": rest_sin_frutos_secos,
                        "sin_huevo": rest_sin_huevo,
                        "bajo_sal": rest_bajo_sal,
                        "presupuesto": presupuesto,
                        "calorias_objetivo": calorias_objetivo,
                    }

                    eval_id = create_evaluacion(
                        username=user["username"],
                        platos=platos_list,
                        precio=menu_optimo.get("precio", 0),
                        calorias=menu_optimo.get("calorias", 0),
                        score=score,
                        satisfaccion=satisfaccion,
                        calidad_precio=calidad_precio_val,
                        elegiria_real=(elegiria_real == "Sí"),
                        restricciones=restricciones_snapshot,
                        recommendation_type="heuristic",
                    )

                    # Persistencia complementaria en Google Sheets
                    try:
                        save_to_google_sheets({
                            "eval_id": eval_id,
                            "username": user["username"],
                            "platos": platos_list,
                            "precio": menu_optimo.get("precio", 0),
                            "calorias": menu_optimo.get("calorias", 0),
                            "score": score,
                            "satisfaccion": satisfaccion,
                            "calidad_precio": calidad_precio_val,
                            "elegiria_real": (elegiria_real == "Sí"),
                            "restricciones": restricciones_snapshot,
                            "recommendation_type": "heuristic",
                        })
                    except Exception:
                        # Si Google Sheets falla, la app sigue con BD local
                        pass

                    st.success(
                        f"Gracias. Tu valoración #{eval_id} se ha guardado "
                        f"para el estudio."
                    )

            if len(top_n) > 1:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("### Otras opciones")

                cols = st.columns(2)
                for idx, (menu_alt, score_alt) in enumerate(top_n[1:5]):
                    with cols[idx % 2]:
                        alt_platos = menu_alt.get("platos", [menu_alt.get("nombre", "")])
                        alt_platos_html = " + ".join(alt_platos)

                        # Color del score
                        alt_pct = max(0, min(100, score_alt * 100 / 1.5))
                        if alt_pct >= 70:
                            alt_color = "#2EA043"
                        elif alt_pct >= 45:
                            alt_color = "#D29922"
                        else:
                            alt_color = "#F85149"

                        st.markdown(f"""
                            <div style="
                                background: #1E293B;
                                border-radius: 12px;
                                padding: 1.25rem;
                                margin-bottom: 1rem;
                                border: 1px solid #334155;
                                position: relative;
                            ">
                                <div style="
                                    position: absolute; top: 1rem; right: 1rem;
                                    background: {alt_color}20;
                                    color: {alt_color};
                                    padding: 0.3rem 0.75rem;
                                    border-radius: 15px;
                                    font-weight: 600;
                                    font-size: 0.85rem;
                                ">{score_alt:.3f}</div>
                                <h4 style="color: #E2E8F0; margin: 0 0 0.75rem 0; font-size: 1rem;
                                    padding-right: 4rem;">
                                    {alt_platos_html}
                                </h4>
                                <div style="display: flex; gap: 1.5rem;">
                                    <span style="color: #3B82F6; font-weight: 600;">
                                        €{menu_alt.get('precio', 0):.2f}
                                    </span>
                                    <span style="color: #8B949E;">
                                        {menu_alt.get('calorias', 0)} kcal
                                    </span>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)

            # ── Transparencia del algoritmo ──
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander(" Detalles del algoritmo (debug/transparencia)"):
                st.markdown(f"""
                    | Parámetro | Valor |
                    |:---|:---|
                    | Combinaciones generadas | **{total_combos}** |
                    | Menús que pasan filtros | **{validos}** |
                    | Peso satisfacción (w₁) | **{w1}** |
                    | Peso precio (w₂) | **{w2}** |
                    | Peso calorías (w₃) | **{w3}** |
                    | Satisfacción simulada | **3.0** (futura integración ML) |
                    | Presupuesto usuario | **€{presupuesto:.2f}** |
                    | Calorías objetivo | **{calorias_objetivo} kcal** |
                """)

                st.markdown("**Fórmula aplicada:**")
                st.code(
                    "score = (w1 × satisfacción) - (w2 × precio/presupuesto) "
                    "- (w3 × |calorías - objetivo| / objetivo)",
                    language=None,
                )

                st.markdown("**Desglose del menú ganador:**")
                precio_norm = menu_optimo.get("precio", 0) / presupuesto if presupuesto > 0 else 0
                desv_cal = (
                    abs(menu_optimo.get("calorias", 0) - calorias_objetivo) / calorias_objetivo
                    if calorias_objetivo > 0 else 0
                )
                st.markdown(f"""
                    | Componente | Valor | Contribución |
                    |:---|:---|:---|
                    | Satisfacción | 3.0 | +{w1 * 3.0:.3f} |
                    | Precio normalizado | {precio_norm:.3f} | -{w2 * precio_norm:.3f} |
                    | Desviación calórica | {desv_cal:.3f} | -{w3 * desv_cal:.3f} |
                    | **Score final** | | **{score:.3f}** |
                """)

# ── Información del algoritmo (siempre visible) ──
st.markdown("<br>", unsafe_allow_html=True)
st.divider()
st.markdown("""
    <div style="
        background: linear-gradient(145deg, #1E293B, #0F172A);
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #334155;
    ">
        <h4 style="color: #3B82F6; margin-bottom: 1rem;">
            Sobre el Motor de Recomendación
        </h4>
        <p style="color: #8B949E; margin: 0;">
            Las recomendaciones se calculan mediante un <strong style="color: #E2E8F0;">
            algoritmo heurístico basado en reglas</strong> que combina filtrado estricto
            (restricciones dietéticas y presupuesto) con una puntuación ponderada
            que optimiza satisfacción, precio y equilibrio calórico.
        </p>
        <p style="color: #8B949E; margin-top: 0.5rem; font-size: 0.875rem;">
            <em>Próximamente: Modelo de ML supervisado (k-NN / Regresión Logística)
            entrenado con las valoraciones reales de los usuarios.</em>
        </p>
    </div>
""", unsafe_allow_html=True)
