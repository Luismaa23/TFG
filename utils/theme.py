"""
MenuMatch - Tema y estilos personalizados
Constantes de colores y CSS para modo oscuro profesional
"""

# Paleta de colores principal
COLORS = {
    "background": "#0F172A",
    "secondary_bg": "#1E293B",
    "primary": "#3B82F6",
    "primary_hover": "#2563EB",
    "text": "#E2E8F0",
    "text_secondary": "#94A3B8",
    "success": "#10B981",
    "warning": "#F59E0B",
    "error": "#EF4444",
    "border": "#334155",
}

# CSS personalizado para componentes
CUSTOM_CSS = """
<style>
/* Ocultar elementos por defecto de Streamlit que ensucian la UI */
header {visibility: hidden;}
#MainMenu {visibility: hidden;}

/* Estilo global para evitar parpadeos y unificar fondo */
.stApp {
    background-color: #0F172A !important;
}

/* Estilo para las Tarjetas / Contenedores (Glassmorphism sutil) */
div[data-testid="stVerticalBlock"] > div > div > div[style*="background"] {
    background: linear-gradient(145deg, #1E293B, #0F172A) !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5), 0 2px 4px -1px rgba(0, 0, 0, 0.3) !important;
    border-radius: 8px !important; /* Menos redondeado = más serio */
    padding: 1.5rem !important;
}

/* Compatibilidad con otras tarjetas personalizadas que usan clases explícitas */
.menu-card, .metric-container {
    background: linear-gradient(145deg, #1E293B, #0F172A) !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5), 0 2px 4px -1px rgba(0, 0, 0, 0.3) !important;
    border-radius: 8px !important;
    padding: 1.5rem;
    margin-bottom: 1rem;
}

/* Texto métricas */
.metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: #3B82F6;
    margin: 0;
}
.metric-label {
    font-size: 0.875rem;
    color: #94A3B8;
    margin-top: 0.5rem;
}

/* Estilo para los Inputs y Selects */
.stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {
    background-color: #0F172A !important;
    border: 1px solid #334155 !important;
    border-radius: 6px !important;
    color: #E2E8F0 !important;
}

/* Estilo para Botones (Efecto Hover profesional) */
.stButton>button {
    background: linear-gradient(135deg, #3B82F6, #2563EB) !important;
    color: #E2E8F0 !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease-in-out !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
}
.stButton>button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
}

/* Etiquetas/Badges para alergias (Cápsulas para emojis) */
.badge {
    background: rgba(255, 255, 255, 0.05); 
    padding: 4px 6px; 
    border-radius: 12px; 
    margin-right: 6px; 
    border: 1px solid rgba(255, 255, 255, 0.1);
    font-size: 1.1rem;
    display: inline-block;
}

/* Headers */
h1, h2, h3 {
    color: #E2E8F0 !important;
}

/* Textos secundarios */
p, span {
    color: #E2E8F0;
}

/* Sidebar */
.css-1d391kg, [data-testid="stSidebar"] {
    background-color: #1E293B !important;
}

/* Dividers */
hr {
    border-color: #334155 !important;
}

/* File uploader */
.stFileUploader {
    background-color: #1E293B !important;
    border: 2px dashed #334155 !important;
    border-radius: 8px !important;
    padding: 2rem !important;
}
</style>
"""

def inject_custom_css():
    """Inyecta el CSS personalizado en la página."""
    import streamlit as st
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
