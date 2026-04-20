"""
MenuMatch - Motor de Recomendación Heurístico (Basado en Reglas)

Decisión #13: Primer motor de recomendación del sistema.
Algoritmo basado en reglas con dos fases:
  1. Filtrado estricto (Hard Rules): restricciones dietéticas + presupuesto
  2. Puntuación ponderada (Soft Scoring): satisfacción, precio y calorías

Fórmula de scoring:
  score = (w1 × satisfacción_media) - (w2 × precio_normalizado) - (w3 × desviación_calórica)

Flujo de datos (MVVM):
  Vista (Página Streamlit) → recoge parámetros del usuario
  Modelo (este módulo) → ejecuta la lógica de recomendación pura

La satisfacción_media se simula con 3.0 por defecto. En el futuro,
será reemplazada por las valoraciones reales de los usuarios (tabla
pedidos) para alimentar un modelo de ML supervisado.
"""


# ─── Filtrado estricto ────────────────────────────────────────────────────────


def _cumple_restricciones(menu: dict, restricciones: dict) -> bool:
    """
    Verifica si un menú cumple con TODAS las restricciones del usuario.

    Mapeo de restricciones usuario → atributo del menú:

    Restricciones POSITIVAS (el plato DEBE tener la propiedad):
      - vegetariano   → menu["vegetariano"] debe ser True
      - sin_gluten    → menu["sin_gluten"]  debe ser True
      - bajo_sal      → menu["bajo_sal"]    debe ser True

    Restricciones NEGATIVAS (el plato NO DEBE tener la propiedad):
      - sin_lactosa       → menu["con_lactosa"]       debe ser False
      - sin_frutos_secos  → menu["con_frutos_secos"]  debe ser False
      - sin_huevo         → menu["con_huevo"]          debe ser False

    Args:
        menu: Diccionario con los atributos del menú/plato.
        restricciones: Diccionario con las preferencias del usuario.

    Returns:
        True si el menú pasa todos los filtros, False en caso contrario.
    """
    # Restricciones positivas: el menú DEBE tener esta propiedad
    if restricciones.get("vegetariano") and not menu.get("vegetariano", False):
        return False
    if restricciones.get("sin_gluten") and not menu.get("sin_gluten", False):
        return False
    if restricciones.get("bajo_sal") and not menu.get("bajo_sal", False):
        return False

    # Restricciones negativas: el menú NO DEBE tener esta propiedad
    if restricciones.get("sin_lactosa") and menu.get("con_lactosa", False):
        return False
    if restricciones.get("sin_frutos_secos") and menu.get("con_frutos_secos", False):
        return False
    if restricciones.get("sin_huevo") and menu.get("con_huevo", False):
        return False

    return True


# ─── Cálculo de puntuación ────────────────────────────────────────────────────


def _calcular_score(
    menu: dict,
    presupuesto: float,
    calorias_objetivo: int,
    w1: float,
    w2: float,
    w3: float,
    satisfaccion_media: float = 3.0,
) -> float:
    """
    Calcula la puntuación heurística de un menú.

    Fórmula:
      score = (w1 × satisfaccion_media) - (w2 × precio_normalizado)
              - (w3 × desviacion_calorica)

    Donde:
      - precio_normalizado  = precio_menu / presupuesto_usuario  (rango 0–1)
      - desviacion_calorica = |calorias_menu - calorias_objetivo| / calorias_objetivo
        (penalización proporcional a la distancia del objetivo calórico)

    Args:
        menu: Diccionario con precio y calorias del menú.
        presupuesto: Presupuesto máximo del usuario (€).
        calorias_objetivo: Objetivo calórico del usuario (kcal).
        w1: Peso de la satisfacción (por defecto 0.5).
        w2: Peso del precio normalizado (por defecto 0.3).
        w3: Peso de la desviación calórica (por defecto 0.2).
        satisfaccion_media: Satisfacción simulada (por defecto 3.0).

    Returns:
        Puntuación heurística del menú (float). Mayor = mejor.
    """
    precio = menu.get("precio", 0)
    calorias = menu.get("calorias", 0)

    # Normalizar precio: 0 = gratis, 1 = usa todo el presupuesto
    precio_normalizado = precio / presupuesto if presupuesto > 0 else 1.0

    # Penalización por alejarse del objetivo calórico
    desviacion_calorica = (
        abs(calorias - calorias_objetivo) / calorias_objetivo
        if calorias_objetivo > 0
        else 0.0
    )

    score = (w1 * satisfaccion_media) - (w2 * precio_normalizado) - (w3 * desviacion_calorica)
    return score


# ─── Motor principal de recomendación ─────────────────────────────────────────


def recomendar_menu_heuristico(
    menus_disponibles: list[dict],
    presupuesto_usuario: float,
    calorias_objetivo: int,
    restricciones_usuario: dict,
    w1: float = 0.5,
    w2: float = 0.3,
    w3: float = 0.2,
) -> tuple[dict, float] | None:
    """
    Motor de recomendación heurístico basado en reglas.

    Proceso:
      1. Filtrado estricto: descarta menús que no cumplen restricciones
         dietéticas o superan el presupuesto.
      2. Si no quedan menús válidos, retorna None.
      3. Calcula la puntuación de cada menú superviviente.
      4. Retorna el menú con la puntuación más alta.

    Args:
        menus_disponibles: Lista de diccionarios con datos de cada menú.
            Cada dict debe contener: nombre, precio, calorias, y las
            restricciones booleanas (vegetariano, sin_gluten, etc.).
        presupuesto_usuario: Presupuesto máximo en euros.
        calorias_objetivo: Objetivo calórico del usuario (kcal).
        restricciones_usuario: Dict con restricciones dietéticas del usuario.
            Claves: vegetariano, sin_gluten, sin_lactosa, sin_frutos_secos,
            sin_huevo, bajo_sal (todas bool).
        w1: Peso de satisfacción en la fórmula (default 0.5).
        w2: Peso de precio normalizado en la fórmula (default 0.3).
        w3: Peso de desviación calórica en la fórmula (default 0.2).

    Returns:
        Tupla (menu_optimo, score) con el mejor menú y su puntuación,
        o None si ningún menú cumple las restricciones.
    """
    # 1. Filtrado estricto (Hard Rules)
    menus_validos = [
        m for m in menus_disponibles
        if m.get("precio", 0) <= presupuesto_usuario
        and _cumple_restricciones(m, restricciones_usuario)
    ]

    # 2. Si no quedan menús, retornar None
    if not menus_validos:
        return None

    # 3. Calcular score para cada menú superviviente
    menus_con_score = []
    for menu in menus_validos:
        score = _calcular_score(
            menu, presupuesto_usuario, calorias_objetivo, w1, w2, w3
        )
        menus_con_score.append((menu, score))

    # 4. Retornar el menú con mayor score
    mejor = max(menus_con_score, key=lambda x: x[1])
    return mejor


def recomendar_top_n(
    menus_disponibles: list[dict],
    presupuesto_usuario: float,
    calorias_objetivo: int,
    restricciones_usuario: dict,
    n: int = 5,
    w1: float = 0.5,
    w2: float = 0.3,
    w3: float = 0.2,
) -> list[tuple[dict, float]]:
    """
    Retorna los N mejores menús según la heurística, ordenados
    de mayor a menor puntuación.

    Útil para mostrar alternativas al usuario junto con el menú
    óptimo principal.

    Args:
        menus_disponibles: Lista de dicts con datos de cada menú.
        presupuesto_usuario: Presupuesto máximo (€).
        calorias_objetivo: Objetivo calórico (kcal).
        restricciones_usuario: Restricciones dietéticas del usuario.
        n: Número de resultados a retornar (default 5).
        w1, w2, w3: Pesos de la fórmula.

    Returns:
        Lista de tuplas (menu, score) ordenada por score descendente.
        Lista vacía si ningún menú cumple las restricciones.
    """
    menus_validos = [
        m for m in menus_disponibles
        if m.get("precio", 0) <= presupuesto_usuario
        and _cumple_restricciones(m, restricciones_usuario)
    ]

    if not menus_validos:
        return []

    menus_con_score = []
    for menu in menus_validos:
        score = _calcular_score(
            menu, presupuesto_usuario, calorias_objetivo, w1, w2, w3
        )
        menus_con_score.append((menu, score))

    menus_con_score.sort(key=lambda x: x[1], reverse=True)
    return menus_con_score[:n]


# ─── Generador de combinaciones ──────────────────────────────────────────────


def generar_combinaciones_menu(platos: list[dict]) -> list[dict]:
    """
    Genera combinaciones de menú a partir de platos individuales.

    Estrategia de combinación:
      - Si hay primeros/entrantes Y segundos/principales: genera pares
        (Primero + Segundo) como menús de 2 platos.
      - Si no hay suficientes categorías para combinar: cada plato
        individual se trata como un menú de 1 plato.

    Lógica de restricciones combinadas:
      - Propiedades POSITIVAS (vegetariano, sin_gluten, bajo_sal):
        el combo las tiene solo si TODOS los platos las tienen.
      - Propiedades NEGATIVAS (con_lactosa, con_frutos_secos, con_huevo):
        el combo las tiene si ALGÚN plato las tiene.

    Args:
        platos: Lista de diccionarios de platos individuales de la BD.

    Returns:
        Lista de dicts representando menús (combinados o individuales).
        Cada dict contiene: nombre, platos, precio, calorias, y
        todas las restricciones booleanas.
    """
    primeros = [p for p in platos if p.get("categoria") in ["Primero", "Entrante"]]
    segundos = [p for p in platos if p.get("categoria") in ["Segundo", "Principal"]]

    combinaciones = []

    # Generar pares Primero + Segundo
    if primeros and segundos:
        for p1 in primeros:
            for p2 in segundos:
                combinaciones.append(_combinar_platos([p1, p2]))

    # Fallback: si no se pueden generar combinaciones, usar platos sueltos
    if not combinaciones:
        for p in platos:
            combinaciones.append({
                "nombre": p.get("nombre", "Sin nombre"),
                "platos": [p.get("nombre", "")],
                "precio": p.get("precio", 0),
                "calorias": p.get("calorias", 0),
                "vegetariano": p.get("vegetariano", False),
                "sin_gluten": p.get("sin_gluten", False),
                "con_lactosa": p.get("con_lactosa", False),
                "con_frutos_secos": p.get("con_frutos_secos", False),
                "con_huevo": p.get("con_huevo", False),
                "bajo_sal": p.get("bajo_sal", False),
                "es_combinacion": False,
            })

    return combinaciones


def _combinar_platos(platos: list[dict]) -> dict:
    """
    Combina múltiples platos en un único diccionario de menú.

    Args:
        platos: Lista de dicts de platos a combinar.

    Returns:
        Dict con datos agregados del menú combinado.
    """
    nombres = [p.get("nombre", "") for p in platos]
    return {
        "nombre": " + ".join(nombres),
        "platos": nombres,
        "precio": round(sum(p.get("precio", 0) for p in platos), 2),
        "calorias": sum(p.get("calorias", 0) for p in platos),
        # Positivas: TODOS deben cumplir
        "vegetariano": all(p.get("vegetariano", False) for p in platos),
        "sin_gluten": all(p.get("sin_gluten", False) for p in platos),
        "bajo_sal": all(p.get("bajo_sal", False) for p in platos),
        # Negativas: basta con que UNO contenga
        "con_lactosa": any(p.get("con_lactosa", False) for p in platos),
        "con_frutos_secos": any(p.get("con_frutos_secos", False) for p in platos),
        "con_huevo": any(p.get("con_huevo", False) for p in platos),
        "es_combinacion": True,
    }
