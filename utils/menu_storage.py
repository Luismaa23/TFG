"""
MenuMatch - Módulo de Almacenamiento de Menús
Persistencia de platos en SQLite (tabla 'menus').

Decisión #11: Migrado de data/menus.json a SQLite.
Decisión #12: Añadidas 4 restricciones alimentarias (con_lactosa,
con_frutos_secos, con_huevo, bajo_sal) para el modelo de ML.
Los platos se almacenan en la tabla 'menus' de data/menumatch.db,
compartidos entre todos los usuarios del sistema.
"""

from utils.database import get_connection


def get_all_menus() -> list[dict]:
    """
    Obtiene todos los platos del sistema.

    Returns:
        Lista de diccionarios con los datos de cada plato.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT id, nombre, precio, calorias, categoria,
                      vegetariano, sin_gluten, con_lactosa,
                      con_frutos_secos, con_huevo, bajo_sal,
                      uploaded_by, uploaded_at
               FROM menus ORDER BY uploaded_at DESC"""
        ).fetchall()

        return [
            {
                "id": row["id"],
                "nombre": row["nombre"],
                "precio": row["precio"],
                "calorias": row["calorias"],
                "categoria": row["categoria"],
                "vegetariano": bool(row["vegetariano"]),
                "sin_gluten": bool(row["sin_gluten"]),
                "con_lactosa": bool(row["con_lactosa"]),
                "con_frutos_secos": bool(row["con_frutos_secos"]),
                "con_huevo": bool(row["con_huevo"]),
                "bajo_sal": bool(row["bajo_sal"]),
                "uploaded_by": row["uploaded_by"],
                "uploaded_at": row["uploaded_at"],
            }
            for row in rows
        ]
    finally:
        conn.close()


def add_menu_item(plato: dict, uploaded_by: str = "") -> int:
    """
    Añade un plato al almacén compartido.

    Args:
        plato: Diccionario con los datos del plato
        uploaded_by: Username del restaurante que lo subió

    Returns:
        ID del plato creado.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO menus
               (nombre, precio, calorias, categoria, vegetariano, sin_gluten,
                con_lactosa, con_frutos_secos, con_huevo, bajo_sal, uploaded_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                uploaded_by,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def add_menu_items(platos: list[dict], uploaded_by: str = "") -> int:
    """
    Añade múltiples platos al almacén compartido (ej: importación CSV).

    Args:
        platos: Lista de diccionarios con los datos de cada plato
        uploaded_by: Username del restaurante que los subió

    Returns:
        Número de platos añadidos.
    """
    conn = get_connection()
    try:
        for plato in platos:
            conn.execute(
                """INSERT INTO menus
                   (nombre, precio, calorias, categoria, vegetariano, sin_gluten,
                    con_lactosa, con_frutos_secos, con_huevo, bajo_sal, uploaded_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                    uploaded_by,
                ),
            )
        conn.commit()
        return len(platos)
    finally:
        conn.close()


def clear_all_menus() -> None:
    """Elimina todos los platos del sistema."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM menus")
        conn.commit()
    finally:
        conn.close()


def delete_menu_item(menu_id: int) -> bool:
    """
    Elimina un plato por su ID.

    Args:
        menu_id: ID del plato en la base de datos

    Returns:
        True si se eliminó, False si el ID no existe.
    """
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM menus WHERE id = ?", (menu_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
