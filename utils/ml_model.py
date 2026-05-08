"""
MenuMatch - Módulo de Machine Learning (Regresión Logística)
Entrenamiento, evaluación y persistencia del modelo de clasificación binaria.

Decisión #19: Este módulo es la única fuente de verdad para el ciclo de vida
del modelo ML. Encapsula:
  - Obtención del dataset limpio (vía ml_pipeline.get_clean_dataset)
  - División train/test y estandarización con StandardScaler
  - Entrenamiento de LogisticRegression
  - Evaluación con accuracy y confusion matrix
  - Persistencia de modelo y escalador en models/

El retorno de train_and_evaluate_model() es un dict serializable, diseñado
para ser consumido directamente por la capa de presentación (Streamlit) sin
acoplamiento entre capas.
"""

import os
import logging
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from utils.ml_pipeline import get_clean_dataset

logger = logging.getLogger(__name__)

# ─── Constantes ───────────────────────────────────────────────────────────────

#: Carpeta donde se persisten el modelo y el escalador.
_MODELS_DIR: str = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "models"
)

#: Ruta al archivo del modelo serializado.
MODEL_PATH: str = os.path.join(_MODELS_DIR, "logistic_model.joblib")

#: Ruta al archivo del escalador serializado.
SCALER_PATH: str = os.path.join(_MODELS_DIR, "scaler.joblib")

#: Columnas usadas como features predictivas (X).
FEATURE_COLS: list[str] = ["calorias", "price_ratio", "score"]

#: Columna objetivo binaria (y).
TARGET_COL: str = "satisfied"

#: Mínimo de registros recomendado para resultados fiables.
MIN_RECORDS_RECOMMENDED: int = 20

#: Semilla de aleatoriedad para reproducibilidad.
RANDOM_STATE: int = 42


# ─── Función principal ────────────────────────────────────────────────────────


def train_and_evaluate_model() -> dict:
    """
    Ejecuta el pipeline completo de ML: obtención de datos → split →
    escalado → entrenamiento → evaluación → persistencia.

    Pipeline detallado:
    1. Llama a ``get_clean_dataset()`` para obtener el DataFrame preprocesado.
    2. Si hay menos de ``MIN_RECORDS_RECOMMENDED`` registros, añade una
       advertencia en el resultado pero continúa para permitir pruebas.
    3. Extrae ``X = [calorias, price_ratio, score]`` y ``y = satisfied``.
    4. Divide en 80 % train / 20 % test con estratificación si es posible.
    5. Estandariza ``X`` con ``StandardScaler`` ajustado solo sobre train.
    6. Entrena ``LogisticRegression(max_iter=1000)``.
    7. Evalúa sobre el conjunto de test: accuracy y confusion matrix.
    8. Persiste modelo y escalador en ``models/`` con joblib.

    Returns:
        Diccionario con las claves:

        - ``"accuracy"`` (float): Exactitud sobre el conjunto de test (0–1).
        - ``"confusion_matrix"`` (list[list[int]]): Matriz de confusión 2×2.
        - ``"n_train"`` (int): Número de muestras de entrenamiento.
        - ``"n_test"`` (int): Número de muestras de test.
        - ``"n_total"`` (int): Total de registros del dataset.
        - ``"model_path"`` (str): Ruta absoluta del modelo guardado.
        - ``"scaler_path"`` (str): Ruta absoluta del escalador guardado.
        - ``"warning"`` (str | None): Aviso si la muestra es pequeña.
        - ``"features"`` (list[str]): Columnas usadas como features.

    Raises:
        ValueError: Si el dataset está vacío o le faltan columnas requeridas.
        RuntimeError: Si ocurre un error inesperado durante el entrenamiento.
    """
    # ── 1. Obtención del dataset ───────────────────────────────────────────────
    df: pd.DataFrame = get_clean_dataset()

    if df.empty:
        raise ValueError(
            "El dataset está vacío. Es necesario que los usuarios registren "
            "al menos algunas evaluaciones antes de entrenar el modelo."
        )

    # Verificar que las columnas requeridas existen
    required_cols = FEATURE_COLS + [TARGET_COL]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(
            f"Faltan columnas requeridas en el dataset: {missing}. "
            "Comprueba que get_clean_dataset() devuelve el esquema correcto."
        )

    # ── 2. Aviso de muestra pequeña ────────────────────────────────────────────
    n_total = len(df)
    warning_msg: str | None = None

    if n_total < MIN_RECORDS_RECOMMENDED:
        warning_msg = (
            f"⚠️ El dataset solo contiene {n_total} registros "
            f"(mínimo recomendado: {MIN_RECORDS_RECOMMENDED}). "
            "Las métricas obtenidas no serán estadísticamente representativas, "
            "pero el entrenamiento se ejecuta igualmente para pruebas."
        )
        logger.warning(warning_msg)

    # ── 3. Separación de features y target ────────────────────────────────────
    X: pd.DataFrame = df[FEATURE_COLS].copy()
    y: pd.Series = df[TARGET_COL].copy()

    # ── 4. División train / test ───────────────────────────────────────────────
    # Se intenta estratificar para mantener la proporción de clases.
    # Si solo hay una clase o la muestra es muy pequeña, se desactiva.
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=0.2,
            random_state=RANDOM_STATE,
            stratify=y,
        )
    except ValueError:
        # Muestra demasiado pequeña para estratificar
        logger.warning("Estratificación desactivada (muestra insuficiente).")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=0.2,
            random_state=RANDOM_STATE,
        )

    n_train = len(X_train)
    n_test = len(X_test)

    # ── 5. Estandarización ────────────────────────────────────────────────────
    # El escalador se ajusta SOLO sobre los datos de entrenamiento para
    # evitar data leakage hacia el conjunto de test.
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # ── 6. Entrenamiento ──────────────────────────────────────────────────────
    # max_iter=1000 para garantizar convergencia en datasets pequeños.
    # solver='lbfgs' es el predeterminado y adecuado para clasificación binaria.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")   # Suprimir ConvergenceWarning en datasets tiny
        model = LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)
        model.fit(X_train_scaled, y_train)

    # ── 7. Evaluación ─────────────────────────────────────────────────────────
    y_pred = model.predict(X_test_scaled)
    acc: float = float(accuracy_score(y_test, y_pred))
    cm: list[list[int]] = confusion_matrix(y_test, y_pred).tolist()

    logger.info(
        "Modelo entrenado — accuracy=%.3f | train=%d | test=%d",
        acc, n_train, n_test,
    )

    # ── 8. Persistencia ───────────────────────────────────────────────────────
    os.makedirs(_MODELS_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)

    logger.info("Modelo guardado en: %s", MODEL_PATH)
    logger.info("Escalador guardado en: %s", SCALER_PATH)

    return {
        "accuracy": acc,
        "confusion_matrix": cm,
        "n_train": n_train,
        "n_test": n_test,
        "n_total": n_total,
        "model_path": MODEL_PATH,
        "scaler_path": SCALER_PATH,
        "warning": warning_msg,
        "features": FEATURE_COLS,
    }


# ─── Utilidades de inferencia ─────────────────────────────────────────────────


def load_model_and_scaler() -> tuple[LogisticRegression, StandardScaler] | tuple[None, None]:
    """
    Carga el modelo y el escalador previamente entrenados desde disco.

    Returns:
        Tupla ``(model, scaler)`` si los archivos existen, o ``(None, None)``
        si aún no se ha entrenado el modelo.
    """
    if not os.path.exists(MODEL_PATH) or not os.path.exists(SCALER_PATH):
        logger.info("No se encontró modelo entrenado en %s", _MODELS_DIR)
        return None, None

    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    return model, scaler


def predict_satisfaction(
    calorias: float,
    price_ratio: float,
    score: float,
) -> dict:
    """
    Predice si un usuario quedaría satisfecho con un menú dado.

    Carga el modelo y el escalador desde disco, estandariza las features
    de entrada y retorna la predicción binaria junto con las probabilidades.

    Args:
        calorias: Calorías totales del menú.
        price_ratio: Ratio precio / presupuesto_max del usuario.
        score: Score heurístico asignado al menú por el recomendador.

    Returns:
        Diccionario con:
        - ``"satisfied"`` (int): 1 = satisfecho predicho, 0 = no satisfecho.
        - ``"prob_satisfied"`` (float): Probabilidad de clase positiva (0–1).
        - ``"prob_not_satisfied"`` (float): Probabilidad de clase negativa (0–1).
        - ``"model_available"`` (bool): False si el modelo no está entrenado.

    Example:
        >>> result = predict_satisfaction(calorias=850, price_ratio=0.75, score=0.82)
        >>> result["satisfied"]
        1
    """
    model, scaler = load_model_and_scaler()

    if model is None:
        return {
            "satisfied": None,
            "prob_satisfied": None,
            "prob_not_satisfied": None,
            "model_available": False,
        }

    features = np.array([[calorias, price_ratio, score]])
    features_scaled = scaler.transform(features)
    prediction = int(model.predict(features_scaled)[0])
    probabilities = model.predict_proba(features_scaled)[0]

    return {
        "satisfied": prediction,
        "prob_satisfied": float(probabilities[1]),
        "prob_not_satisfied": float(probabilities[0]),
        "model_available": True,
    }
