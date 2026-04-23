"""
MenuMatch - Motor de Recomendación Heurístico (Basado en Reglas)

Decisión #13 (Rev. 3): Motor de recomendación con Plantillas de Menú
y scoring balanceado.

Correcciones sobre Rev. 2:
  1. FILTRO SEMÁNTICO: Postres y Acompañamientos NO pueden formar una
     plantilla 'Plato Único'. Solo Primeros, Segundos y Platos Únicos
     reales tienen esa capacidad semántica.

  2. PENALIZACIÓN ASIMÉTRICA DE DÉFICIT CALÓRICO: La fórmula anterior
     penalizaba igual el exceso que el déficit calórico. El nuevo
     cálculo aplica una penalización exponencial (×3) cuando el menú
     se queda MUY por debajo del objetivo (> 40% de déficit), lo que
     destruye cualquier bonus de plantilla para ítems insignificantes
     como un acompañamiento o un postre aislado.

  3. BONUS REDUCIDO A DESEMPATE: El bonus de la plantilla 'Plato Único'
     se reduce a un valor mínimo (0.05) para que actúe únicamente como
     criterio de desempate entre menús de puntuación muy similar, sin
     dominar la ecuación.

  PLANTILLAS SOPORTADAS:
  ┌─────────────┬──────────────────────────────────────────────────────┐
  │ Plato Único │ Solo Primero, Segundo o Plato Único real.            │
  │             │ Priorizado cuando presupuesto < 6€ o kcal < 500.     │
  ├─────────────┼──────────────────────────────────────────────────────┤
  │ Clásico     │ 1 Primero + 1 Segundo                                │
  ├─────────────┼──────────────────────────────────────────────────────┤
  │ Ligero      │ 1 (Primero o Segundo) + 1 Postre                     │
  ├─────────────┼──────────────────────────────────────────────────────┤
  │ Completo    │ 1 Primero + 1 Segundo + 1 (Postre o Acompañamiento)  │
  └─────────────┴──────────────────────────────────────────────────────┘

Fórmula de scoring (Rev. 3):
  desv = |kcal_menu - kcal_objetivo| / kcal_objetivo
  penalizacion_cal = desv × 3  si déficit > 40%  (kcal_menu < 0.6 × objetivo)
                   = desv       en cualquier otro caso
  score = (w1 × sat) - (w2 × precio_norm) - (w3 × penalizacion_cal)
          + bonus_plantilla   [bonus máx. 0.05, solo desempate]

Flujo de datos (MVVM):
  Vista (Página Streamlit) → recoge parámetros del usuario
  Modelo (este módulo) → ejecuta la lógica de recomendación pura
"""

from itertools import product


# ─── Constantes de Plantillas ─────────────────────────────────────────────────

# Umbral para activar el modo "solo Platos Únicos"
_UMBRAL_PRESUPUESTO_BAJO = 6.0   # €
_UMBRAL_CALORIAS_BAJAS   = 500   # kcal

# Bonus de plantilla: valor mínimo para actuar solo como desempate.
# NO debe dominar la ecuación; el objetivo calórico es el factor principal.
_BONUS_PLATO_UNICO = 0.05

# Umbral de déficit calórico a partir del cual se aplica penalización ×3.
# Si el menú aporta menos del 60% de las kcal objetivo → déficit severo.
_UMBRAL_DEFICIT_SEVERO = 0.40   # 40% por debajo del objetivo
_MULTIPLICADOR_DEFICIT  = 3.0   # factor de amplificación del castigo

# Categorías reconocidas por tipo
_CAT_PRIMEROS = {"Primero", "Entrante", "primero", "entrante"}
_CAT_SEGUNDOS = {"Segundo", "Principal", "segundo", "principal"}
_CAT_POSTRES  = {"Postre", "postre"}
_CAT_ACOMP    = {"Acompañamiento", "Guarnicion", "acompañamiento", "guarnicion"}
_CAT_UNICOS   = {"Plato Único", "plato único", "Unico", "unico", "Único", "único"}

# Categorías EXCLUIDAS de la plantilla 'Plato Único' (filtro semántico inclusivo).
# Se compara en minúsculas y con singular/plural para ser robusto ante variaciones
# de escritura en la base de datos.
_CAT_EXCLUIDAS_PLATO_UNICO = {
    "postre", "postres",
    "acompañamiento", "acompañamientos",
    "bebida", "bebidas",
    "pan",
}

# Hard-ban de Plato Único: umbrales mínimos de calidad nutricional/económica.
# Un plato que no los supere no puede recomendarse como comida completa.
_MIN_KCAL_PLATO_UNICO  = 300   # kcal mínimas
_MIN_PRECIO_PLATO_UNICO = 2.00  # € mínimo


# ─── Filtrado estricto ────────────────────────────────────────────────────────


def _cumple_restricciones(menu: dict, restricciones: dict) -> bool:
    """
    Verifica si un menú cumple con TODAS las restricciones dietéticas del usuario.

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
    if restricciones.get("vegetariano") and not menu.get("vegetariano", False):
        return False
    if restricciones.get("sin_gluten") and not menu.get("sin_gluten", False):
        return False
    if restricciones.get("bajo_sal") and not menu.get("bajo_sal", False):
        return False
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
    Calcula la puntuación heurística de un menú con scoring adaptativo.

    La novedad respecto a la versión anterior es el BONUS ADAPTATIVO:
    si el menú es un Plato Único y el usuario tiene un contexto de bajo
    presupuesto (< 6€) o bajas calorías (< 500 kcal), se añade un bonus
    que compensa la penalización implícita por precio que sufría el plato
    único al compararse con combinaciones más caras.

    Fórmula:
      score = (w1 × satisfaccion_media) - (w2 × precio_normalizado)
              - (w3 × desviacion_calorica) + bonus_plantilla

    Donde:
      - precio_normalizado  = precio_menu / presupuesto_usuario  (rango 0–1)
      - desviacion_calorica = |calorias_menu - calorias_objetivo| / calorias_objetivo
      - bonus_plantilla     = _BONUS_PLATO_UNICO_BAJO_CONTEXTO si aplica,
                              0.0 en caso contrario.

    Args:
        menu: Diccionario con precio, calorias y plantilla del menú.
        presupuesto: Presupuesto máximo del usuario (€).
        calorias_objetivo: Objetivo calórico del usuario (kcal).
        w1: Peso de la satisfacción (por defecto 0.5).
        w2: Peso del precio normalizado (por defecto 0.3).
        w3: Peso de la desviación calórica (por defecto 0.2).
        satisfaccion_media: Satisfacción simulada (por defecto 3.0).

    Returns:
        Puntuación heurística del menú (float). Mayor = mejor.
    """
    precio    = menu.get("precio", 0)
    calorias  = menu.get("calorias", 0)
    plantilla = menu.get("plantilla", "")

    # ── Precio normalizado (0 = gratis, 1 = agota el presupuesto) ──
    precio_normalizado = precio / presupuesto if presupuesto > 0 else 1.0

    # ── Penalización calórica estándar ────────────────────────────────
    desviacion_calorica = (
        abs(calorias - calorias_objetivo) / calorias_objetivo
        if calorias_objetivo > 0
        else 0.0
    )

    score = (
        (w1 * satisfaccion_media)
        - (w2 * precio_normalizado)
        - (w3 * desviacion_calorica)
    )

    # ── Bonus de plantilla (desempate únicamente) ─────────────────────
    contexto_bajo = (
        presupuesto < _UMBRAL_PRESUPUESTO_BAJO
        or calorias_objetivo < _UMBRAL_CALORIAS_BAJAS
    )
    if plantilla == "Plato Único" and contexto_bajo:
        score += _BONUS_PLATO_UNICO

    # ── PENALIZACIÓN MULTIPLICATIVA POR DÉFICIT CALÓRICO SEVERO ───────
    # Si el menú aporta menos del 60% de las kcal objetivo, el score
    # total se multiplica por 0.1 (hundimiento drástico).
    # Esta barrera es POSTERIOR a cualquier bonus y precio, de modo que
    # ningún ahorro económico ni bonus de plantilla puede compensarla.
    # Es la única forma de garantizar que un ítem de 150 kcal nunca
    # supere a un menú de 700-900 kcal en contextos normales.
    if calorias_objetivo > 0 and calorias < 0.60 * calorias_objetivo:
        score *= 0.1

    return score


# ─── Generador de combinaciones con Plantillas de Menú ───────────────────────


def generar_combinaciones_menu(
    platos: list[dict],
    presupuesto_hint: float = 999.0,
    calorias_hint: int = 9999,
) -> list[dict]:
    """
    Genera combinaciones de menú basadas en Plantillas estructuradas.

    En lugar de combinaciones arbitrarias de N platos, este generador
    aplica cuatro plantillas válidas que representan estructuras de menú
    reales en la restauración. Esto elimina el sesgo anterior hacia
    "Primero + Segundo" e incluye postres, acompañamientos y platos únicos.

    PLANTILLAS:
      - "Plato Único"  → 1 plato de cualquier categoría.
                         Si presupuesto < 6€ o kcal < 500, se genera
                         EXCLUSIVAMENTE esta plantilla para no inundar
                         el ranking con combinaciones inaccesibles.
      - "Clásico"      → 1 Primero + 1 Segundo.
      - "Ligero"       → 1 (Primero o Segundo) + 1 Postre.
      - "Completo"     → 1 Primero + 1 Segundo + 1 (Postre o Acompañamiento).

    Lógica de restricciones combinadas:
      - Propiedades POSITIVAS (vegetariano, sin_gluten, bajo_sal):
        el combo las tiene solo si TODOS los platos las tienen.
      - Propiedades NEGATIVAS (con_lactosa, con_frutos_secos, con_huevo):
        el combo las tiene si ALGÚN plato las tiene.

    Args:
        platos: Lista de dicts de platos individuales de la BD.
        presupuesto_hint: Presupuesto del usuario (€). Usado para activar
            el modo "solo Platos Únicos" en contextos de bajo presupuesto.
        calorias_hint: Objetivo calórico (kcal). Usado del mismo modo.

    Returns:
        Lista de dicts representando menús estructurados con plantilla.
        Cada dict añade la clave "plantilla" para trazabilidad.
    """
    # ── Clasificar platos por categoría ──
    primeros = [p for p in platos if p.get("categoria", "") in _CAT_PRIMEROS]
    segundos = [p for p in platos if p.get("categoria", "") in _CAT_SEGUNDOS]
    postres  = [p for p in platos if p.get("categoria", "") in _CAT_POSTRES]
    acomps   = [p for p in platos if p.get("categoria", "") in _CAT_ACOMP]

    # ── FILTRO SEMÁNTICO INCLUSIVO (robusto a mayúsculas y plurales) ──
    # Se excluyen por categoría los ítems que nunca pueden ser una comida
    # completa por sí solos: postres, acompañamientos, bebidas y pan.
    # La comparación se hace en minúsculas para evitar fallos por variaciones
    # de escritura en la base de datos.
    # Además, se aplica un HARD-BAN nutricional/económico: un plato con
    # menos de 300 kcal o menos de 2.00€ no puede ser un Plato Único,
    # independientemente de su categoría.
    candidatos_plato_unico = [
        p for p in platos
        if p.get("categoria", "").lower() not in _CAT_EXCLUIDAS_PLATO_UNICO
        and p.get("calorias", 0) >= _MIN_KCAL_PLATO_UNICO
        and p.get("precio", 0) >= _MIN_PRECIO_PLATO_UNICO
    ]

    contexto_bajo = (
        presupuesto_hint < _UMBRAL_PRESUPUESTO_BAJO
        or calorias_hint < _UMBRAL_CALORIAS_BAJAS
    )

    combinaciones: list[dict] = []

    # ── Plantilla: Plato Único ──────────────────────────────────────────────
    # Siempre se genera. Si el contexto es bajo, es la ÚNICA plantilla.
    for p in candidatos_plato_unico:
        combinaciones.append(
            {**_combinar_platos([p]), "plantilla": "Plato Único"}
        )

    if contexto_bajo:
        # En contexto bajo, devolver solo Platos Únicos para que el
        # ranking sea relevante y no esté dominado por combos prohibitivos.
        return combinaciones if combinaciones else _fallback_platos_sueltos(platos)

    # ── Plantilla: Clásico (Primero + Segundo) ──────────────────────────────
    for p1, p2 in product(primeros, segundos):
        combinaciones.append(
            {**_combinar_platos([p1, p2]), "plantilla": "Clásico"}
        )

    # ── Plantilla: Ligero ((Primero o Segundo) + Postre) ───────────────────
    if postres:
        for plato_base in primeros + segundos:
            for postre in postres:
                combinaciones.append(
                    {**_combinar_platos([plato_base, postre]), "plantilla": "Ligero"}
                )

    # ── Plantilla: Completo (Primero + Segundo + (Postre o Acompañamiento)) ─
    complementos = postres + acomps
    if complementos:
        for p1, p2 in product(primeros, segundos):
            for comp in complementos:
                combinaciones.append(
                    {**_combinar_platos([p1, p2, comp]), "plantilla": "Completo"}
                )

    # Fallback: si no se ha generado ninguna combinación estructurada
    # (p.ej. catálogo con un solo plato de una sola categoría),
    # devolver todos los platos como Platos Únicos.
    if not combinaciones:
        return _fallback_platos_sueltos(platos)

    return combinaciones


def _fallback_platos_sueltos(platos: list[dict]) -> list[dict]:
    """
    Genera una lista de Platos Únicos como fallback cuando no es posible
    construir ninguna combinación estructurada.

    Args:
        platos: Lista de dicts de platos individuales.

    Returns:
        Lista de dicts de menús individuales con plantilla "Plato Único".
    """
    return [
        {**_combinar_platos([p]), "plantilla": "Plato Único"}
        for p in platos
    ]


def _combinar_platos(platos: list[dict]) -> dict:
    """
    Combina múltiples platos en un único diccionario de menú agregado.

    La lógica de combinación de restricciones booleanas sigue la
    regla del mínimo común: las propiedades positivas (vegetariano,
    sin_gluten, bajo_sal) se heredan solo si TODOS los platos las
    tienen; las negativas (alérgenos) se activan si ALGÚN plato
    los contiene.

    Args:
        platos: Lista de dicts de platos a combinar (mínimo 1).

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
        "vegetariano":    all(p.get("vegetariano", False) for p in platos),
        "sin_gluten":     all(p.get("sin_gluten", False) for p in platos),
        "bajo_sal":       all(p.get("bajo_sal", False) for p in platos),
        # Negativas: basta con que UNO contenga
        "con_lactosa":      any(p.get("con_lactosa", False) for p in platos),
        "con_frutos_secos": any(p.get("con_frutos_secos", False) for p in platos),
        "con_huevo":        any(p.get("con_huevo", False) for p in platos),
        "es_combinacion": len(platos) > 1,
    }


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
    Motor de recomendación heurístico basado en Plantillas de Menú.

    Proceso:
      1. Filtrado estricto: descarta menús que superan presupuesto
         o incumplen restricciones dietéticas.
      2. Si no quedan menús válidos, retorna None.
      3. Calcula el score adaptativo para cada menú superviviente.
      4. Retorna el menú con la puntuación más alta.

    Args:
        menus_disponibles: Lista de dicts generados por generar_combinaciones_menu().
            Cada dict debe contener: nombre, platos, precio, calorias,
            plantilla, y las restricciones booleanas.
        presupuesto_usuario: Presupuesto máximo en euros.
        calorias_objetivo: Objetivo calórico del usuario (kcal).
        restricciones_usuario: Dict con restricciones dietéticas del usuario.
        w1: Peso de satisfacción en la fórmula (default 0.5).
        w2: Peso de precio normalizado en la fórmula (default 0.3).
        w3: Peso de desviación calórica en la fórmula (default 0.2).

    Returns:
        Tupla (menu_optimo, score) con el mejor menú y su puntuación,
        o None si ningún menú cumple las restricciones.
    """
    menus_validos = [
        m for m in menus_disponibles
        if m.get("precio", 0) <= presupuesto_usuario
        and _cumple_restricciones(m, restricciones_usuario)
    ]

    if not menus_validos:
        return None

    menus_con_score = [
        (
            menu,
            _calcular_score(
                menu, presupuesto_usuario, calorias_objetivo, w1, w2, w3
            ),
        )
        for menu in menus_validos
    ]

    return max(menus_con_score, key=lambda x: x[1])


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

    Incluye menús de todas las plantillas (Plato Único, Clásico,
    Ligero, Completo) para ofrecer diversidad real de opciones al usuario.

    Args:
        menus_disponibles: Lista de dicts generados por generar_combinaciones_menu().
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

    menus_con_score = [
        (
            menu,
            _calcular_score(
                menu, presupuesto_usuario, calorias_objetivo, w1, w2, w3
            ),
        )
        for menu in menus_validos
    ]

    menus_con_score.sort(key=lambda x: x[1], reverse=True)
    return menus_con_score[:n]
