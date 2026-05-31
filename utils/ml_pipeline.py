"""
MenuMatch - Pipeline de Machine Learning
Módulo de preparación y limpieza del dataset para entrenamiento de modelos ML.

Decisión ADR: Este módulo centraliza toda la lógica de feature engineering
para asegurar que el preprocesamiento sea reproducible y esté desacoplado
de la capa de presentación (Streamlit).

La función principal `get_clean_dataset` actúa como la única fuente de
verdad para obtener el conjunto de datos ML-ready a partir de la BD SQLite.
"""

import sqlite3
import json
import os

import pandas as pd


# ─── Constantes ───────────────────────────────────────────────────────────────

_DEFAULT_PRESUPUESTO_MAX: float = 15.0
"""Valor de presupuesto_max que se asigna cuando el JSON de restricciones
no contiene el campo o su parseo falla."""

_FINAL_COLUMNS: list[str] = [
    "id",
    "calorias",
    "precio",
    "presupuesto_max",
    "price_ratio",
    "score",
    "recommendation_type",
    "satisfied",
]
"""Columnas que componen el DataFrame final entregado al pipeline de ML.
Se excluyen columnas redundantes (calidad_precio) y no predictivas
(platos JSON, restricciones_json, fecha, username)."""


# ─── Función principal ────────────────────────────────────────────────────────


def get_clean_dataset(db_path: str = "data/menumatch.db") -> pd.DataFrame:
    """
    Extrae, transforma y limpia el dataset de evaluaciones para su uso en ML.

    Pipeline de transformación aplicado:
    1. Lectura de todos los registros de ``evaluaciones_menus`` vía SQLite.
    2. Parseo de ``restricciones_json`` para extraer ``presupuesto_max``
       (fallback: ``_DEFAULT_PRESUPUESTO_MAX`` = 15.0 si el campo falta o
       el JSON es inválido).
    3. Ingeniería de features:
       - ``price_ratio``: relación precio / presupuesto_max, captura si el
         menú entra dentro del presupuesto del usuario.
       - ``satisfied``: variable objetivo binaria (1 si satisfaccion >= 4,
         0 si satisfaccion <= 3).
    4. Selección de columnas: se retienen únicamente las features predictivas
       y la variable objetivo definidas en ``_FINAL_COLUMNS``.

    Args:
        db_path: Ruta relativa o absoluta al archivo SQLite de MenuMatch.
                 Por defecto ``'data/menumatch.db'`` (relativa al CWD).

    Returns:
        DataFrame limpio con las columnas ``['id', 'calorias', 'precio',
        'presupuesto_max', 'price_ratio', 'score', 'recommendation_type',
        'satisfied']``, listo para ser consumido por un clasificador ML.

    Raises:
        FileNotFoundError: Si ``db_path`` no existe.
        pd.errors.DatabaseError: Si la tabla ``evaluaciones_menus`` no existe
            en la base de datos indicada.

    Example:
        >>> df = get_clean_dataset()
        >>> print(df.shape)
        (N, 8)
        >>> print(df["satisfied"].value_counts())
        1    ...
        0    ...
    """
    import unicodedata
    import streamlit as st
    
    df = None
    data_source = "Local"

    # \u2500\u2500 1. Intento de extracci\u00f3n desde Google Sheets (Nube) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    try:
        from utils.google_sheets import get_all_data_from_sheets
        df_sheets = get_all_data_from_sheets()
        
        if df_sheets is not None and not df_sheets.empty:
            # Adaptaci\u00f3n de nombres de columnas (manejando may\u00fasculas y espacios)
            rename_map = {}
            for col in df_sheets.columns:
                norm_col = str(col).lower().strip()
                norm_col = unicodedata.normalize('NFKD', norm_col).encode('ASCII', 'ignore').decode('utf-8')
                norm_col = norm_col.replace(' ', '_').replace('-', '_')
                
                if norm_col in ('eval_id', 'identificador', 'id', ''):
                    rename_map[col] = 'id'
                elif 'restriccion' in norm_col:
                    rename_map[col] = 'restricciones_json'
                elif 'satisfaccion' in norm_col or 'satifaccion' in norm_col:
                    rename_map[col] = 'satisfaccion'
                elif 'recommendation' in norm_col or 'recomendacion' in norm_col:
                    rename_map[col] = 'recommendation_type'
                elif 'score' in norm_col or 'puntuacion' in norm_col:
                    rename_map[col] = 'score'
                elif 'calorias' in norm_col:
                    rename_map[col] = 'calorias'
                elif norm_col == 'precio':
                    rename_map[col] = 'precio'
                else:
                    rename_map[col] = norm_col
                    
            df_sheets = df_sheets.rename(columns=rename_map)
            
            # Verificar que las columnas requeridas existan
            required_cols = ['id', 'precio', 'calorias', 'score', 'recommendation_type', 'restricciones_json', 'satisfaccion']
            missing = [c for c in required_cols if c not in df_sheets.columns]
            
            if not missing:
                df = df_sheets[required_cols].copy()
                data_source = "Cloud (Google Sheets)"
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Fallo al obtener datos de Google Sheets: %s", e)

    # \u2500\u2500 2. Fallback: Extracci\u00f3n desde SQLite (Local) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    if df is None or df.empty:
        abs_path = os.path.abspath(db_path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(
                f"No se encontr\u00f3 la base de datos en: {abs_path}\n"
                "Aseg\u00farate de ejecutar la app al menos una vez para inicializar la BD."
            )

        conn = sqlite3.connect(abs_path)
        try:
            df = pd.read_sql_query(
                """
                SELECT
                    id,
                    precio,
                    calorias,
                    score,
                    recommendation_type,
                    restricciones_json,
                    satisfaccion
                FROM evaluaciones_menus
                """,
                conn,
            )
        finally:
            conn.close()

    # Mostrar informacion sobre la fuente de datos si estamos bajo Streamlit
    try:
        st.info(f"Datos extraidos desde: {data_source}")
    except Exception:
        pass

    if df.empty:
        # Devolver DataFrame vac\u00edo con el esquema correcto para no romper el pipeline
        return pd.DataFrame(columns=_FINAL_COLUMNS)

    # ── 3. Parseo de restricciones_json → presupuesto_max ────────────────────
    def _extract_presupuesto(raw_json: str) -> float:
        """
        Extrae ``presupuesto_max`` del JSON de restricciones del usuario.

        Aplica el valor por defecto ``_DEFAULT_PRESUPUESTO_MAX`` cuando:
        - El valor es ``None`` o una cadena vacía.
        - El JSON no es parseable.
        - El campo ``presupuesto_max`` no existe en el dict.
        - El valor extraído no es numérico.
        """
        try:
            if not raw_json:
                return _DEFAULT_PRESUPUESTO_MAX
            data = json.loads(raw_json)
            value = data.get("presupuesto_max", _DEFAULT_PRESUPUESTO_MAX)
            return float(value) if value is not None else _DEFAULT_PRESUPUESTO_MAX
        except (json.JSONDecodeError, ValueError, TypeError):
            return _DEFAULT_PRESUPUESTO_MAX

    df["presupuesto_max"] = df["restricciones_json"].apply(_extract_presupuesto)

    # ── 4. Feature engineering ────────────────────────────────────────────────
    # price_ratio: cuánto del presupuesto consume el menú recomendado.
    # Se protege contra divisiones por cero con un mínimo de 0.01.
    df["price_ratio"] = df["precio"] / df["presupuesto_max"].clip(lower=0.01)

    # satisfied: variable objetivo binaria derivada de la columna satisfaccion.
    # satisfaccion >= 4  →  1 (usuario satisfecho)
    # satisfaccion <= 3  →  0 (usuario insatisfecho)
    df["satisfied"] = (df["satisfaccion"] >= 4).astype(int)

    # ── 5. Selección y retorno de columnas finales ────────────────────────────
    # Se descartan: restricciones_json, satisfaccion, calidad_precio, fecha,
    # username, platos (no predictivos o redundantes con satisfied/price_ratio).
    return df[_FINAL_COLUMNS].copy()
