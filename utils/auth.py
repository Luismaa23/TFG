"""
MenuMatch - Módulo de Autenticación
Gestión de usuarios, roles y sesiones.

Roles disponibles:
    - admin: Acceso total + panel de administración
    - restaurante: Carga y gestión de menús
    - usuario: Ver menús, restricciones, recomendaciones, historial

Decisión #11: Migrado de JSON local a SQLite (data/menumatch.db).
Las contraseñas se mantienen hasheadas con bcrypt.
"""

import streamlit as st
import bcrypt

from utils.database import get_connection, init_db

# ─── Constantes de roles ───────────────────────────────────────────────────────
ROLE_ADMIN = "admin"
ROLE_USUARIO = "usuario"
ROLE_RESTAURANTE = "restaurante"

ALL_ROLES = [ROLE_ADMIN, ROLE_USUARIO, ROLE_RESTAURANTE]


# ─── Funciones de hash ────────────────────────────────────────────────────────
def _hash_password(password: str) -> str:
    """Genera un hash bcrypt de la contraseña."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    """Verifica una contraseña contra su hash bcrypt."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ─── Inicialización ──────────────────────────────────────────────────────────
def init_users_db() -> None:
    """
    Inicializa la base de datos completa (usuarios, menus, pedidos).
    Crea las tablas si no existen, migra datos JSON si los hay,
    e inserta un administrador por defecto si la tabla está vacía.
    """
    init_db()  # Crea tablas + migra JSON

    # Insertar admin por defecto si no hay usuarios
    conn = get_connection()
    try:
        count = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
        if count == 0:
            conn.execute(
                """INSERT INTO usuarios (username, password, role, nombre)
                   VALUES (?, ?, ?, ?)""",
                ("admin", _hash_password("admin123"), ROLE_ADMIN, "Administrador"),
            )
            conn.commit()
    finally:
        conn.close()


# ─── Registro e inicio de sesión ──────────────────────────────────────────────
def register_user(username: str, password: str, role: str, nombre: str) -> tuple[bool, str]:
    """
    Registra un nuevo usuario en el sistema.

    Args:
        username: Nombre de usuario (único)
        password: Contraseña en texto plano (se hashea antes de guardar)
        role: Rol del usuario (usuario o restaurante)
        nombre: Nombre para mostrar

    Returns:
        Tupla (éxito: bool, mensaje: str)
    """
    if not username or not password or not nombre:
        return False, "Todos los campos son obligatorios"

    if len(username) < 3:
        return False, "El usuario debe tener al menos 3 caracteres"

    if len(password) < 4:
        return False, "La contraseña debe tener al menos 4 caracteres"

    if role not in [ROLE_USUARIO, ROLE_RESTAURANTE]:
        return False, "Rol no válido para registro"

    conn = get_connection()
    try:
        # Verificar si el username ya existe (case-insensitive)
        existing = conn.execute(
            "SELECT 1 FROM usuarios WHERE LOWER(username) = LOWER(?)", (username,)
        ).fetchone()

        if existing:
            return False, "Este nombre de usuario ya existe"

        conn.execute(
            """INSERT INTO usuarios (username, password, role, nombre)
               VALUES (?, ?, ?, ?)""",
            (username, _hash_password(password), role, nombre),
        )
        conn.commit()
        return True, "Registro exitoso"
    finally:
        conn.close()


def login_user(username: str, password: str) -> tuple[bool, str, dict | None]:
    """
    Verifica credenciales e inicia sesión.

    Args:
        username: Nombre de usuario
        password: Contraseña en texto plano

    Returns:
        Tupla (éxito: bool, mensaje: str, datos_usuario: dict | None)
    """
    if not username or not password:
        return False, "Introduce usuario y contraseña", None

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT username, password, role, nombre FROM usuarios WHERE username = ?",
            (username,),
        ).fetchone()

        if row is None:
            return False, "Usuario o contraseña incorrectos", None

        if not _verify_password(password, row["password"]):
            return False, "Usuario o contraseña incorrectos", None

        return True, "Login correcto", {
            "username": row["username"],
            "role": row["role"],
            "nombre": row["nombre"],
        }
    finally:
        conn.close()


# ─── Gestión de sesión ────────────────────────────────────────────────────────
def get_current_user() -> dict | None:
    """
    Obtiene el usuario actual de la sesión.

    Returns:
        Diccionario con datos del usuario o None si no hay sesión activa.
    """
    return st.session_state.get("current_user", None)


def set_current_user(user_data: dict) -> None:
    """Guarda los datos del usuario en la sesión."""
    st.session_state["current_user"] = user_data


def logout() -> None:
    """Cierra la sesión del usuario actual y limpia el estado."""
    keys_to_keep = set()
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            del st.session_state[key]


def require_auth(allowed_roles: list[str] | None = None) -> dict | None:
    """
    Guardia de autenticación para páginas.
    Si no hay usuario logueado, fuerza un rerun (que redirige al Login
    vía st.navigation en app.py). Si el rol no es válido, muestra error.

    Args:
        allowed_roles: Lista de roles permitidos. None = cualquier rol autenticado.

    Returns:
        Datos del usuario si tiene acceso.
    """
    user = get_current_user()

    if user is None:
        st.rerun()
        st.stop()

    if allowed_roles and user["role"] not in allowed_roles:
        st.error("No tienes permisos para acceder a esta sección")
        st.stop()

    return user


# ─── Funciones de administración ──────────────────────────────────────────────
def get_all_users() -> dict:
    """
    Obtiene todos los usuarios registrados (sin contraseñas).

    Returns:
        Diccionario {username: {role, nombre}}
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT username, role, nombre FROM usuarios ORDER BY username"
        ).fetchall()
        return {
            row["username"]: {"role": row["role"], "nombre": row["nombre"]}
            for row in rows
        }
    finally:
        conn.close()


def delete_user(username: str) -> tuple[bool, str]:
    """
    Elimina un usuario del sistema.

    Args:
        username: Nombre de usuario a eliminar

    Returns:
        Tupla (éxito: bool, mensaje: str)
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT role FROM usuarios WHERE username = ?", (username,)
        ).fetchone()

        if row is None:
            return False, "Usuario no encontrado"

        if row["role"] == ROLE_ADMIN:
            admin_count = conn.execute(
                "SELECT COUNT(*) FROM usuarios WHERE role = ?", (ROLE_ADMIN,)
            ).fetchone()[0]
            if admin_count <= 1:
                return False, "No se puede eliminar el último administrador"

        conn.execute("DELETE FROM usuarios WHERE username = ?", (username,))
        conn.commit()
        return True, f"Usuario '{username}' eliminado"
    finally:
        conn.close()


def update_user_role(username: str, new_role: str) -> tuple[bool, str]:
    """
    Cambia el rol de un usuario.

    Args:
        username: Nombre de usuario
        new_role: Nuevo rol a asignar

    Returns:
        Tupla (éxito: bool, mensaje: str)
    """
    if new_role not in ALL_ROLES:
        return False, "Rol no válido"

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT role FROM usuarios WHERE username = ?", (username,)
        ).fetchone()

        if row is None:
            return False, "Usuario no encontrado"

        # Evitar quitar el último admin
        if row["role"] == ROLE_ADMIN and new_role != ROLE_ADMIN:
            admin_count = conn.execute(
                "SELECT COUNT(*) FROM usuarios WHERE role = ?", (ROLE_ADMIN,)
            ).fetchone()[0]
            if admin_count <= 1:
                return False, "No se puede cambiar el rol del último administrador"

        conn.execute(
            "UPDATE usuarios SET role = ? WHERE username = ?",
            (new_role, username),
        )
        conn.commit()
        return True, f"Rol de '{username}' actualizado a '{new_role}'"
    finally:
        conn.close()


def admin_create_user(username: str, password: str, role: str, nombre: str) -> tuple[bool, str]:
    """
    Crea un usuario desde el panel de administración.
    A diferencia de register_user, permite crear cualquier rol (incluido admin).

    Args:
        username: Nombre de usuario (único)
        password: Contraseña en texto plano
        role: Rol del usuario (cualquiera de ALL_ROLES)
        nombre: Nombre para mostrar

    Returns:
        Tupla (éxito: bool, mensaje: str)
    """
    if not username or not password or not nombre:
        return False, "Todos los campos son obligatorios"

    if len(username) < 3:
        return False, "El usuario debe tener al menos 3 caracteres"

    if len(password) < 4:
        return False, "La contraseña debe tener al menos 4 caracteres"

    if role not in ALL_ROLES:
        return False, "Rol no válido"

    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT 1 FROM usuarios WHERE LOWER(username) = LOWER(?)", (username,)
        ).fetchone()

        if existing:
            return False, "Este nombre de usuario ya existe"

        conn.execute(
            """INSERT INTO usuarios (username, password, role, nombre)
               VALUES (?, ?, ?, ?)""",
            (username, _hash_password(password), role, nombre),
        )
        conn.commit()
        return True, f"Usuario '{username}' creado con rol '{role}'"
    finally:
        conn.close()


def update_user_nombre(username: str, new_nombre: str) -> tuple[bool, str]:
    """
    Cambia el nombre de un usuario.

    Args:
        username: Nombre de usuario
        new_nombre: Nuevo nombre para mostrar

    Returns:
        Tupla (éxito: bool, mensaje: str)
    """
    if not new_nombre:
        return False, "El nombre no puede estar vacío"

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM usuarios WHERE username = ?", (username,)
        ).fetchone()

        if row is None:
            return False, "Usuario no encontrado"

        conn.execute(
            "UPDATE usuarios SET nombre = ? WHERE username = ?",
            (new_nombre, username),
        )
        conn.commit()
        return True, f"Nombre de '{username}' actualizado"
    finally:
        conn.close()
