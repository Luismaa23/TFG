"""
MenuMatch - Persistencia en Google Sheets (CORREGIDO)
"""

import json
import logging
from datetime import datetime
import streamlit as st

logger = logging.getLogger(__name__)

def _get_google_sheets_client():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        logger.warning("gspread o google-auth no instalados.")
        return None

    try:
        # EL CAMBIO ESTÁ AQUÍ: Usamos json.loads porque st.secrets lo lee como texto
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
    try:
        client = _get_google_sheets_client()
        if client is None:
            return False

        # Abrir la hoja de cálculo
        spreadsheet = client.open("MenuMatch_Data")
        # sheet1 siempre toma la primera pestaña, se llame como se llame
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