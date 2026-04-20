"""
MenuMatch - Módulo de Base de Datos
Gestión de la conexión SQLite y esquema de tablas.

Decisión #11: Migración de JSON a SQLite con 3 tablas:
- usuarios: Autenticación y roles
- menus: Platos de restaurantes
- pedidos: Selecciones de menú de usuarios con valoración

Se usa SQLite por ser una BD relacional integrada en Python (sin
dependencias externas) que ofrece integridad de datos, consultas
SQL y soporte para concurrencia básica.
"""

import sqlite3
import json
import os

# Ruta a la base de datos
_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
_DB_FILE = os.path.join(_DATA_DIR, "menumatch.db")

# Rutas a los archivos JSON antiguos (para migración)
_USERS_JSON = os.path.join(_DATA_DIR, "users.json")
_MENUS_JSON = os.path.join(_DATA_DIR, "menus.json")


def get_connection() -> sqlite3.Connection:
    """
    Obtiene una conexión a la base de datos SQLite.

    Returns:
        Conexión SQLite con row_factory configurado para acceso
        por nombre de columna (sqlite3.Row).
    """
    os.makedirs(_DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(_DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """
    Inicializa el esquema de la base de datos.
    Crea las 3 tablas si no existen y ejecuta la migración
    automática desde JSON si hay datos previos.
    """
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    UNIQUE NOT NULL,
                password    TEXT    NOT NULL,
                role        TEXT    NOT NULL DEFAULT 'usuario',
                nombre      TEXT    NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS menus (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre           TEXT    NOT NULL,
                precio           REAL    NOT NULL,
                calorias         INTEGER NOT NULL,
                categoria        TEXT    DEFAULT 'Principal',
                vegetariano      BOOLEAN DEFAULT 0,
                sin_gluten       BOOLEAN DEFAULT 0,
                con_lactosa      BOOLEAN DEFAULT 0,
                con_frutos_secos BOOLEAN DEFAULT 0,
                con_huevo        BOOLEAN DEFAULT 0,
                bajo_sal         BOOLEAN DEFAULT 0,
                uploaded_by      TEXT    NOT NULL,
                uploaded_at      TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS pedidos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    NOT NULL,
                platos      TEXT    NOT NULL,
                precio      REAL    NOT NULL,
                calorias    INTEGER NOT NULL,
                valoracion  INTEGER DEFAULT 0,
                fecha       TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS evaluaciones_menus (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                username            TEXT    NOT NULL,
                platos              TEXT    NOT NULL,
                precio              REAL    NOT NULL,
                calorias            INTEGER NOT NULL,
                score               REAL    NOT NULL,
                recommendation_type TEXT    NOT NULL DEFAULT 'heuristic',
                restricciones_json  TEXT    DEFAULT '{}',
                satisfaccion        INTEGER NOT NULL CHECK(satisfaccion BETWEEN 1 AND 5),
                calidad_precio      INTEGER NOT NULL CHECK(calidad_precio BETWEEN 1 AND 5),
                elegiria_real       BOOLEAN NOT NULL DEFAULT 0,
                fecha               TEXT    NOT NULL DEFAULT (datetime('now'))
            );
        """)
        conn.commit()

        # Migración automática desde JSON
        _migrate_users_from_json(conn)
        _migrate_menus_from_json(conn)

        # Migración: añadir columnas de restricciones alimentarias
        # (Decisión #12) — seguro para BD existentes que ya tengan datos
        _migrate_add_restriction_columns(conn)

    finally:
        conn.close()


def _migrate_add_restriction_columns(conn: sqlite3.Connection) -> None:
    """
    Añade las 4 nuevas columnas de restricciones alimentarias a la tabla
    'menus' si no existen. Necesario para bases de datos creadas antes de
    la Decisión #12.

    Cada ALTER TABLE se ejecuta por separado y se ignora el error si la
    columna ya existe (idempotente).
    """
    new_columns = [
        ("con_lactosa", "BOOLEAN DEFAULT 0"),
        ("con_frutos_secos", "BOOLEAN DEFAULT 0"),
        ("con_huevo", "BOOLEAN DEFAULT 0"),
        ("bajo_sal", "BOOLEAN DEFAULT 0"),
    ]
    for col_name, col_type in new_columns:
        try:
            conn.execute(f"ALTER TABLE menus ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass  # La columna ya existe
    conn.commit()


def _migrate_users_from_json(conn: sqlite3.Connection) -> None:
    """
    Migra usuarios desde data/users.json a la tabla 'usuarios'.
    Solo se ejecuta si el JSON existe y la tabla está vacía.
    Tras migrar, renombra el JSON a .json.bak.
    """
    if not os.path.exists(_USERS_JSON):
        return

    # Comprobar si ya hay usuarios en la BD
    count = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    if count > 0:
        return

    try:
        with open(_USERS_JSON, "r", encoding="utf-8") as f:
            users = json.load(f)

        for username, data in users.items():
            conn.execute(
                """INSERT INTO usuarios (username, password, role, nombre)
                   VALUES (?, ?, ?, ?)""",
                (username, data["password"], data["role"], data["nombre"]),
            )
        conn.commit()

        # Renombrar JSON a backup
        os.rename(_USERS_JSON, _USERS_JSON + ".bak")
    except Exception:
        pass  # Si falla la migración, no bloquear el arranque


def _migrate_menus_from_json(conn: sqlite3.Connection) -> None:
    """
    Migra platos desde data/menus.json a la tabla 'menus'.
    Solo se ejecuta si el JSON existe y la tabla está vacía.
    Tras migrar, renombra el JSON a .json.bak.
    """
    if not os.path.exists(_MENUS_JSON):
        return

    # Comprobar si ya hay menús en la BD
    count = conn.execute("SELECT COUNT(*) FROM menus").fetchone()[0]
    if count > 0:
        return

    try:
        with open(_MENUS_JSON, "r", encoding="utf-8") as f:
            menus = json.load(f)

        for plato in menus:
            conn.execute(
                """INSERT INTO menus
                   (nombre, precio, calorias, categoria, vegetariano, sin_gluten,
                    con_lactosa, con_frutos_secos, con_huevo, bajo_sal,
                    uploaded_by, uploaded_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    plato.get("nombre", "Sin nombre"),
                    plato.get("precio", 0),
                    plato.get("calorias", 0),
                    plato.get("categoria", "Principal"),
                    1 if plato.get("vegetariano") else 0,
                    1 if plato.get("sin_gluten") else 0,
                    1 if plato.get("con_lactosa") else 0,
                    1 if plato.get("con_frutos_secos") else 0,
                    1 if plato.get("con_huevo") else 0,
                    1 if plato.get("bajo_sal") else 0,
                    plato.get("uploaded_by", ""),
                    plato.get("uploaded_at", ""),
                ),
            )
        conn.commit()

        # Renombrar JSON a backup
        os.rename(_MENUS_JSON, _MENUS_JSON + ".bak")
    except Exception:
        pass  # Si falla la migración, no bloquear el arranque


# ─── Funciones de Pedidos ─────────────────────────────────────────────────────

def create_pedido(username: str, platos: list, precio: float, calorias: int) -> int:
    """
    Crea un nuevo pedido en la base de datos.

    Args:
        username: Usuario que realiza el pedido
        platos: Lista de nombres de platos seleccionados
        precio: Precio total del menú
        calorias: Calorías totales del menú

    Returns:
        ID del pedido creado.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO pedidos (username, platos, precio, calorias)
               VALUES (?, ?, ?, ?)""",
            (username, json.dumps(platos, ensure_ascii=False), precio, calorias),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_pedidos_by_user(username: str) -> list[dict]:
    """
    Obtiene todos los pedidos de un usuario, ordenados por fecha descendente.

    Args:
        username: Nombre de usuario

    Returns:
        Lista de diccionarios con los datos de cada pedido.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT id, platos, precio, calorias, valoracion, fecha
               FROM pedidos WHERE username = ? ORDER BY fecha DESC""",
            (username,),
        ).fetchall()

        pedidos = []
        for row in rows:
            pedidos.append({
                "id": row["id"],
                "platos": json.loads(row["platos"]),
                "precio": row["precio"],
                "calorias": row["calorias"],
                "valoracion": row["valoracion"],
                "fecha": row["fecha"],
            })
        return pedidos
    finally:
        conn.close()


def update_valoracion(pedido_id: int, valoracion: int) -> bool:
    """
    Actualiza la valoración de un pedido.

    Args:
        pedido_id: ID del pedido
        valoracion: Valoración 1-5

    Returns:
        True si se actualizó, False si no se encontró.
    """
    if not 1 <= valoracion <= 5:
        return False

    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE pedidos SET valoracion = ? WHERE id = ?",
            (valoracion, pedido_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_all_pedidos() -> list[dict]:
    """
    Obtiene todos los pedidos del sistema (para panel admin).

    Returns:
        Lista de diccionarios con todos los pedidos.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT id, username, platos, precio, calorias, valoracion, fecha
               FROM pedidos ORDER BY fecha DESC"""
        ).fetchall()

        pedidos = []
        for row in rows:
            pedidos.append({
                "id": row["id"],
                "username": row["username"],
                "platos": json.loads(row["platos"]),
                "precio": row["precio"],
                "calorias": row["calorias"],
                "valoracion": row["valoracion"],
                "fecha": row["fecha"],
            })
        return pedidos
    finally:
        conn.close()


# ─── Funciones de Evaluaciones (ML Feedback) ─────────────────────────────────

def create_evaluacion(
    username: str,
    platos: list,
    precio: float,
    calorias: int,
    score: float,
    satisfaccion: int,
    calidad_precio: int,
    elegiria_real: bool,
    restricciones: dict = None,
    recommendation_type: str = "heuristic",
) -> int:
    """
    Registra la evaluación de un usuario sobre un menú recomendado.
    Estos datos alimentarán el futuro modelo de Machine Learning.

    Args:
        username: Usuario que evalúa
        platos: Lista de nombres de platos del menú evaluado
        precio: Precio total del menú
        calorias: Calorías totales del menú
        score: Puntuación heurística asignada al menú
        satisfaccion: Valoración de satisfacción general (1-5)
        calidad_precio: Valoración de relación calidad-precio (1-5)
        elegiria_real: Si el usuario elegiría realmente este menú
        restricciones: Dict con las restricciones del usuario al momento
        recommendation_type: Tipo de recomendación ('heuristic' o 'ml')

    Returns:
        ID de la evaluación creada.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO evaluaciones_menus
               (username, platos, precio, calorias, score,
                recommendation_type, restricciones_json,
                satisfaccion, calidad_precio, elegiria_real)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                username,
                json.dumps(platos, ensure_ascii=False),
                precio,
                calorias,
                score,
                recommendation_type,
                json.dumps(restricciones or {}, ensure_ascii=False),
                satisfaccion,
                calidad_precio,
                1 if elegiria_real else 0,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_all_evaluaciones() -> list[dict]:
    """
    Obtiene todas las evaluaciones del sistema (para explotación ML / admin).

    Returns:
        Lista de diccionarios con todas las evaluaciones.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT id, username, platos, precio, calorias, score,
                      recommendation_type, restricciones_json,
                      satisfaccion, calidad_precio, elegiria_real, fecha
               FROM evaluaciones_menus ORDER BY fecha DESC"""
        ).fetchall()

        evaluaciones = []
        for row in rows:
            evaluaciones.append({
                "id": row["id"],
                "username": row["username"],
                "platos": json.loads(row["platos"]),
                "precio": row["precio"],
                "calorias": row["calorias"],
                "score": row["score"],
                "recommendation_type": row["recommendation_type"],
                "restricciones": json.loads(row["restricciones_json"]),
                "satisfaccion": row["satisfaccion"],
                "calidad_precio": row["calidad_precio"],
                "elegiria_real": bool(row["elegiria_real"]),
                "fecha": row["fecha"],
            })
        return evaluaciones
    finally:
        conn.close()
