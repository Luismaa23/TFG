"""
MenuMatch - Persistencia en Google Sheets

Módulo encargado de sincronizar las evaluaciones de menús con una
hoja de cálculo de Google Sheets como backup externo.

Decisión #15: Dado que Streamlit Community Cloud utiliza un sistema
de archivos efímero, la base de datos SQLite puede perderse entre
reinicios del servidor. Google Sheets actúa como almacenamiento
persistente complementario. La conexión se gestiona con gspread +
google-auth, leyendo las credenciales desde st.secrets.

La función save_to_google_sheets() está diseñada como operación
"fire-and-forget" con try-except: si falla la conexión a Google,
la aplicación continúa funcionando con normalidad usando la BD local.
"""

import json
import logging
from datetime import datetime

import streamlit as st

logger = logging.getLogger(__name__)


def _get_google_sheets_client():
    """
    Crea y devuelve un cliente autorizado de gspread usando las
    credenciales almacenadas en st.secrets["GOOGLE_CREDENTIALS"].

    Returns:
        Cliente gspread autorizado, o None si las dependencias o
        credenciales no están disponibles.

    Raises:
        No lanza excepciones; devuelve None en caso de error.
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        logger.warning(
            "gspread o google-auth no instalados. "
            "La persistencia en Google Sheets está deshabilitada."
        )
        return None

    try:
        creds_dict = dict(st.secrets["GOOGLE_CREDENTIALS"])
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
    Persiste una evaluación de menú como nueva fila en la hoja de
    cálculo 'MenuMatch_Data' de Google Sheets.

    La función es tolerante a fallos: si la conexión a Google falla,
    registra el error y devuelve False sin interrumpir la aplicación.

    Args:
        datos: Diccionario con los campos de la evaluación:
            - eval_id (int): ID de la evaluación en SQLite
            - username (str): Usuario que evalúa
            - platos (list[str]): Lista de platos del menú
            - precio (float): Precio total del menú
            - calorias (int): Calorías totales del menú
            - score (float): Puntuación heurística
            - satisfaccion (int): Valoración 1-5
            - calidad_precio (int): Valoración 1-5
            - elegiria_real (bool): Si elegiría el menú
            - restricciones (dict): Restricciones del usuario
            - recommendation_type (str): Tipo de recomendación

    Returns:
        True si la fila se insertó correctamente, False en caso
        contrario.
    """
    try:
        client = _get_google_sheets_client()
        if client is None:
            return False

        # Abrir la hoja de cálculo por nombre
        spreadsheet = client.open("MenuMatch_Data")
        worksheet = spreadsheet.sheet1

        # Preparar la fila con los datos de la evaluación
        fila = [
            datos.get("eval_id", ""),
            datos.get("username", ""),
            json.dumps(
                datos.get("platos", []), ensure_ascii=False
            ),
            datos.get("precio", 0),
            datos.get("calorias", 0),
            datos.get("score", 0),
            datos.get("recommendation_type", "heuristic"),
            json.dumps(
                datos.get("restricciones", {}), ensure_ascii=False
            ),
            datos.get("satisfaccion", 0),
            datos.get("calidad_precio", 0),
            1 if datos.get("elegiria_real") else 0,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ]

        worksheet.append_row(fila, value_input_option="USER_ENTERED")
        logger.info(
            "Evaluación #%s guardada en Google Sheets.",
            datos.get("eval_id"),
        )
        return True

    except Exception as e:
        logger.error(
            "Error al guardar en Google Sheets (no crítico): %s", e
        )
        return False
