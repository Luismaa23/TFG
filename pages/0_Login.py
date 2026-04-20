"""
MenuMatch - Página de Login y Registro
Autenticación de usuarios con soporte para 3 roles.
"""

import streamlit as st
from utils.theme import inject_custom_css
from utils.auth import (
    init_users_db,
    login_user,
    register_user,
    get_current_user,
    set_current_user,
    ROLE_USUARIO,
    ROLE_RESTAURANTE,
)

# Configuración de página se gestiona desde app.py con st.navigation()

inject_custom_css()

# Inicializar DB de usuarios
init_users_db()

# ─── CSS adicional para la página de login ────────────────────────────────────
st.markdown("""
<style>
    /* Ocultar sidebar en login */
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    
    .login-container {
        max-width: 480px;
        margin: 0 auto;
        padding: 2rem;
    }
    
    .login-header {
        text-align: center;
        padding: 2rem 0 1rem 0;
    }
    
    .login-header h1 {
        background: linear-gradient(135deg, #3B82F6, #2563EB);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
    
    .login-header p {
        color: #8B949E;
        font-size: 1rem;
    }
    
    .role-card {
        background: linear-gradient(145deg, #1E293B, #0F172A);
        border-radius: 12px;
        padding: 1rem 1.25rem;
        border: 1px solid #334155;
        margin-bottom: 0.5rem;
        transition: all 0.2s ease;
    }
    
    .role-card:hover {
        border-color: #3B82F6;
    }
    
    .divider-text {
        text-align: center;
        color: #8B949E;
        margin: 1.5rem 0;
        font-size: 0.875rem;
    }
</style>
""", unsafe_allow_html=True)

# ─── Header ──────────────────────────────────────────────────────────────────
# --- Header ---
# Usamos columnas para que el logo quede perfectamente centrado
col1, col2, col3 = st.columns([1, 0.5, 1])
with col2:
    st.image("assets/logo.png", use_container_width=True)

st.markdown("""
<div class="login-header" style="text-align: center; margin-top: -1rem;">
    <h1>MenuMatch</h1>
    <p>Tu menú del día óptimo</p>
</div>
""", unsafe_allow_html=True)

# ─── Tabs Login / Registro ───────────────────────────────────────────────────
tab_login, tab_register = st.tabs(["Iniciar Sesión", "Registrarse"])

with tab_login:
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        st.markdown("#### Accede a tu cuenta")
        
        login_username = st.text_input(
            "Usuario",
            placeholder="Tu nombre de usuario",
            key="login_user_input",
        )
        login_password = st.text_input(
            "Contraseña",
            type="password",
            placeholder="Tu contraseña",
            key="login_pass_input",
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        login_submit = st.form_submit_button(
            "Iniciar Sesión",
            type="primary",
            use_container_width=True,
        )
        
        if login_submit:
            success, message, user_data = login_user(login_username, login_password)
            if success:
                set_current_user(user_data)
                st.switch_page("pages/1_Inicio.py")
            else:
                st.error(f"{message}")

with tab_register:
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.form("register_form"):
        st.markdown("#### Crea tu cuenta")
        
        reg_nombre = st.text_input(
            "Nombre completo",
            placeholder="Ej: María García",
            key="reg_nombre_input",
        )
        reg_username = st.text_input(
            "Usuario",
            placeholder="Elige un nombre de usuario",
            key="reg_user_input",
        )
        reg_password = st.text_input(
            "Contraseña",
            type="password",
            placeholder="Mínimo 4 caracteres",
            key="reg_pass_input",
        )
        reg_password_confirm = st.text_input(
            "Confirmar contraseña",
            type="password",
            placeholder="Repite tu contraseña",
            key="reg_pass_confirm_input",
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### ¿Qué tipo de cuenta necesitas?")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
                <div class="role-card">
                    <p style="margin: 0; color: #E2E8F0; font-weight: 600;">Usuario</p>
                    <p style="margin: 0.25rem 0 0 0; color: #8B949E; font-size: 0.8rem;">
                        Busca y pide menús
                    </p>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
                <div class="role-card">
                    <p style="margin: 0; color: #E2E8F0; font-weight: 600;">Restaurante</p>
                    <p style="margin: 0.25rem 0 0 0; color: #8B949E; font-size: 0.8rem;">
                        Publica tus menús
                    </p>
                </div>
            """, unsafe_allow_html=True)
        
        reg_role = st.selectbox(
            "Tipo de cuenta",
            options=[ROLE_USUARIO, ROLE_RESTAURANTE],
            format_func=lambda x: "Usuario — Buscar y pedir menús" if x == ROLE_USUARIO else "Restaurante — Publicar menús",
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        reg_submit = st.form_submit_button(
            "Crear Cuenta",
            type="primary",
            use_container_width=True,
        )
        
        if reg_submit:
            if reg_password != reg_password_confirm:
                st.error("Las contraseñas no coinciden")
            else:
                success, message = register_user(
                    reg_username, reg_password, reg_role, reg_nombre
                )
                if success:
                    # Auto-login tras registro
                    _, _, user_data = login_user(reg_username, reg_password)
                    if user_data:
                        set_current_user(user_data)
                    st.switch_page("pages/1_Inicio.py")
                else:
                    st.error(f"{message}")

# ─── Footer ──────────────────────────────────────────────────────────────────
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
    <div style="
        text-align: center;
        padding: 1.5rem;
        background: #1E293B;
        border-radius: 12px;
        border: 1px solid #334155;
    ">
        <p style="color: #8B949E; margin: 0; font-size: 0.85rem;">
            Las contraseñas se almacenan de forma segura con hash bcrypt
        </p>
    </div>
""", unsafe_allow_html=True)
