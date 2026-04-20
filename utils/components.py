"""
MenuMatch - Componentes reutilizables
Cards, métricas, badges y otros elementos de UI
"""

import streamlit as st
from utils.theme import COLORS


def menu_card(nombre: str, precio: float, calorias: int, restricciones: list = None):
    """
    Renderiza una card de plato del menú.
    
    Args:
        nombre: Nombre del plato
        precio: Precio en euros
        calorias: Calorías del plato
        restricciones: Lista de restricciones (vegetariano, sin_gluten, etc.)
    """
    badges_html = ""
    if restricciones:
        badge_classes = {
            "vegetariano": "badge",
            "sin_gluten": "badge",
            "con_lactosa": "badge",
            "con_frutos_secos": "badge",
            "con_huevo": "badge",
            "bajo_sal": "badge",
            "bajo_cal": "badge",
        }
        badge_emojis = {
            "vegetariano": ("🥬", "Vegetariano"),
            "sin_gluten": ("🌾", "Sin Gluten"),
            "con_lactosa": ("🥛", "Contiene Lactosa"),
            "con_frutos_secos": ("🥜", "Contiene Frutos Secos"),
            "con_huevo": ("🥚", "Contiene Huevo"),
            "bajo_sal": ("🧂", "Bajo en Sal"),
            "bajo_cal": ("🥗", "Bajo en Calorías"),
        }
        for r in restricciones:
            if r in badge_emojis:
                emoji, label = badge_emojis[r]
                badges_html += f'<span class="badge" title="{label}">{emoji}</span>'
    
    st.markdown(f"""
        <div class="menu-card">
            <h3 style="margin: 0 0 0.5rem 0; color: #E2E8F0;">{nombre}</h3>
            <div style="display: flex; gap: 1.5rem; margin-bottom: 0.75rem;">
                <span style="color: #3B82F6; font-size: 1.25rem; font-weight: 600;">€{precio:.2f}</span>
                <span style="color: #94A3B8;">{calorias} kcal</span>
            </div>
            <div>{badges_html}</div>
        </div>
    """, unsafe_allow_html=True)


def metric_card(valor: str, etiqueta: str, icono: str = ""):
    """
    Renderiza una card de métrica sin emojis.
    
    Args:
        valor: Valor principal a mostrar
        etiqueta: Descripción de la métrica
        icono: Ignorado para eliminar emojis
    """
    st.markdown(f"""
        <div class="metric-container">
            <p class="metric-value">{valor}</p>
            <p class="metric-label">{etiqueta}</p>
        </div>
    """, unsafe_allow_html=True)


def restriction_badge(tipo: str, activo: bool = False):
    """
    Renderiza un badge de restricción dietética estilo enterprise.
    
    Args:
        tipo: Tipo de restricción
        activo: Si está activa o no
    """
    etiquetas = {
        "vegetariano": ("🥬", "Vegetariano"),
        "vegano": ("🌱", "Vegano"),
        "sin_gluten": ("🌾", "Sin Gluten"),
        "sin_lactosa": ("🥛", "Sin Lactosa"),
        "bajo_cal": ("🥗", "Bajo en Calorías"),
    }
    
    emoji, full_label = etiquetas.get(tipo, ("🏷️", tipo.replace('_', ' ').title()))
    opacity = "1" if activo else "0.4"
    color = "#3B82F6" if activo else "#94A3B8"
    bg_color = "rgba(59, 130, 246, 0.1)" if activo else "rgba(148, 163, 184, 0.1)"
    
    return f"""
        <span title="{full_label}" style="
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            background: {bg_color};
            border: 1px solid {color};
            border-radius: 50%;
            font-size: 1.2rem;
            opacity: {opacity};
            transition: all 0.2s ease;
            cursor: help;
        ">
            {emoji}
        </span>
    """


def section_header(titulo: str, subtitulo: str = ""):
    """
    Renderiza un header de sección estilizado sin colores exagerados.
    
    Args:
        titulo: Título principal
        subtitulo: Descripción opcional
    """
    st.markdown(f"""
        <div style="margin-bottom: 2rem;">
            <h1 style="
                color: #E2E8F0;
                font-size: 2rem;
                font-weight: 700;
                margin-bottom: 0.5rem;
            ">{titulo}</h1>
            <p style="color: #94A3B8; font-size: 1.1rem;">{subtitulo}</p>
        </div>
    """, unsafe_allow_html=True)


def empty_state(mensaje: str, icono: str = ""):
    """
    Renderiza un estado vacío sin emoji gigante (aspecto profesional).
    
    Args:
        mensaje: Mensaje a mostrar
        icono: Ignorado
    """
    st.markdown(f"""
        <div style="
            text-align: center;
            padding: 4rem 2rem;
            background: #1E293B;
            border-radius: 8px;
            border: 1px dashed #334155;
        ">
            <h3 style="color: #E2E8F0; margin-bottom: 0.5rem;">Sin resultados</h3>
            <p style="color: #94A3B8; font-size: 1rem;">{mensaje}</p>
        </div>
    """, unsafe_allow_html=True)


def recommendation_card(platos: list, precio_total: float, calorias_total: int, puntuacion: float):
    """
    Renderiza una card de recomendación de menú.
    
    Args:
        platos: Lista de nombres de platos
        precio_total: Precio total del menú
        calorias_total: Calorías totales
        puntuacion: Puntuación de "mejor valor" (0-100)
    """
    platos_html = "".join([f"<li style='color: #E2E8F0; margin-bottom: 0.5rem;'>{p}</li>" for p in platos])
    
    # Color de puntuación según valor
    if puntuacion >= 80:
        score_color = "#10B981"
    elif puntuacion >= 60:
        score_color = "#F59E0B"
    else:
        score_color = "#EF4444"
    
    st.markdown(f"""
        <div class="menu-card" style="position: relative;">
            <div style="
                position: absolute;
                top: 1rem;
                right: 1rem;
                background: {score_color};
                color: white;
                padding: 0.25rem 0.75rem;
                border-radius: 4px;
                font-weight: 700;
                font-size: 0.9em;
            ">{puntuacion:.0f} PTS</div>
            <h3 style="color: #3B82F6; margin-bottom: 1rem;">Menú Recomendado</h3>
            <ul style="list-style: none; padding: 0; margin-bottom: 1rem;">
                {platos_html}
            </ul>
            <div style="display: flex; gap: 2rem; padding-top: 1rem; border-top: 1px solid #334155;">
                <div>
                    <span style="color: #94A3B8; font-size: 0.875rem;">Total</span>
                    <p style="color: #3B82F6; font-size: 1.5rem; font-weight: 700; margin: 0;">€{precio_total:.2f}</p>
                </div>
                <div>
                    <span style="color: #94A3B8; font-size: 0.875rem;">Calorías</span>
                    <p style="color: #E2E8F0; font-size: 1.5rem; font-weight: 700; margin: 0;">{calorias_total} kcal</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
