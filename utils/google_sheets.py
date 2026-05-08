"""
MenuMatch - Persistencia en Google Sheets
Escritura de evaluaciones y lectura de datos históricos desde la nube.
"""

import json
import logging
from datetime import datetime
import streamlit as st

logger = logging.getLogger(__name__)


def _get_google_sheets_client():
    """
    Crea y devuelve un cliente autenticado de gspread usando las credenciales
    de Service Account almacenadas en st.secrets["GOOGLE_CREDENTIALS"].

    Returns:
        Cliente gspread autorizado, o None si faltan dependencias o credenciales.
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        logger.warning("gspread o google-auth no instalados.")
        return None

    try:
        creds_json = st.secrets["GOOGLE_CREDENTIALS"]
        creds_dict = json.loads(creds_json)

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = Credentials.from_service_account_info(
            creds_dict, scopes=scopes
        )
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        logger.error("Error al crear cliente de Google Sheets: %s", e)
        return None


def save_to_google_sheets(datos: dict) -> bool:
    """
    Append a new evaluation row to the first sheet of MenuMatch_Data.

    Args:
        datos: Diccionario con los campos de la evaluación a persistir.

    Returns:
        True si la fila se escribió correctamente, False en caso contrario.
    """
    try:
        client = _get_google_sheets_client()
        if client is None:
            return False

        spreadsheet = client.open("MenuMatch_Data")
        worksheet = spreadsheet.sheet1

        fila = [
            datos.get("eval_id", ""),
            datos.get("username", ""),
            json.dumps(datos.get("platos", []), ensure_ascii=False),
            datos.get("precio", 0),
            datos.get("calorias", 0),
            datos.get("score", 0),
            datos.get("recommendation_type", "heuristic"),
            json.dumps(datos.get("restricciones", {}), ensure_ascii=False),
            datos.get("satisfaccion", 0),
            datos.get("calidad_precio", 0),
            1 if datos.get("elegiria_real") else 0,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ]

        worksheet.append_row(fila, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        logger.error("Error al guardar en Google Sheets: %s", e)
        return False


def get_all_data_from_sheets():
    """
    Descarga todos los registros históricos de evaluaciones desde la nube.

    Abre el documento ``MenuMatch_Data``, lee la primera hoja completa
    (incluyendo la fila de cabecera como nombres de columna) y devuelve
    los datos como un DataFrame de Pandas.

    Returns:
        ``pd.DataFrame`` con todos los registros de la hoja. Si la hoja está
        vacía o solo contiene cabecera, devuelve un DataFrame vacío con las
        columnas correctas pero sin filas.

    Raises:
        ConnectionError: Si no se puede autenticar con Google (credenciales
            ausentes, inválidas o sin permisos sobre el documento).
        RuntimeError: Si ocurre cualquier otro error de red o de la API de
            Google Sheets durante la lectura.
    """
    import pandas as pd

    client = _get_google_sheets_client()
    if client is None:
        raise ConnectionError(
            "No se pudo conectar con Google Sheets. "
            "Verifica que GOOGLE_CREDENTIALS esté configurado en st.secrets "
            "y que la cuenta de servicio tenga acceso al documento MenuMatch_Data."
        )

    try:
        spreadsheet = client.open("MenuMatch_Data")
        worksheet = spreadsheet.sheet1
        records = worksheet.get_all_records()

        if not records:
            # Hoja vacía o solo cabecera: devolver DataFrame vacío
            logger.info("La hoja MenuMatch_Data está vacía o no tiene datos.")
            return pd.DataFrame()

        return pd.DataFrame(records)

    except Exception as e:
        logger.error("Error al leer datos de Google Sheets: %s", e)
        raise RuntimeError(
            f"Error al descargar datos desde Google Sheets: {e}"
        ) from e