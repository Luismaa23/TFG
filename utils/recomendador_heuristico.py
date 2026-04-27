"""
MenuMatch - Motor de Recomendación Heurístico (Basado en Reglas)

Decisión #13 (Rev. 4): Motor de recomendación con Plantillas de Menú
y scoring simplificado lineal (Baseline para ML).

Correcciones sobre Rev. 3:
  1. SIMPLIFICACIÓN DE SCORING: La fórmula se refactoriza para ser lineal
     y predecible, priorizando la desviación calórica en un 95%.
  2. PRECIO COMO DESEMPATE: El presupuesto es un límite absoluto (hard-ban).
     El precio solo se usa como un factor minúsculo de penalización para 
     desempatar menús con calorías similares.
  3. ELIMINACIÓN DE BONUS: Se eliminan todos los bonus por "ahorro" 
     para evitar comportamientos agresivos e impredecibles.
  4. BARRERAS DE SEGURIDAD MANTENIDAS: Se conserva el filtro semántico 
     y el hard-ban de postres/panes como plato único, además de la penalización
     drástica por déficit calórico severo (< 60% del objetivo).

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
  ├─────────────┼──────────────────────────────────────────────────────┤
  │ Tradicional │ 1 Primero + 1 Segundo + 1 Postre + 1 Acompañamiento  │
  └─────────────┴──────────────────────────────────────────────────────┘

Fórmula de scoring (Rev. 4):
  desv = |kcal_menu - kcal_objetivo| / kcal_objetivo
  score_base = 1.0 - desv
  desempate_precio = precio_menu * 0.001
  score = score_base - desempate_precio
  
  Si kcal_menu < 0.6 × kcal_objetivo: score = score * 0.1 (penalización severa)

Flujo de datos (MVVM):
  Vista (Página Streamlit) → recoge parámetros del usuario
  Modelo (este módulo) → ejecuta la lógica de recomendación pura
"""

from itertools import product


# ─── Constantes de Plantillas ─────────────────────────────────────────────────

# Umbral para activar el modo "solo Platos Únicos"
_UMBRAL_PRESUPUESTO_BAJO = 6.0   # €
_UMBRAL_CALORIAS_BAJAS   = 500   # kcal

# Bonus de plantilla eliminado a petición de tutor para hacer el modelo Baseline predecible.

# Umbral de déficit calórico a partir del cual se aplica penalización ×3.
# Si el menú aporta menos del 60% de las kcal objetivo → déficit severo.
_UMBRAL_DEFICIT_SEVERO = 0.40   # 40% por debajo del objetivo
_MULTIPLICADOR_DEFICIT  = 3.0   # factor de amplificación del castigo

# Categorías son detectadas ahora mediante normalización (.lower().strip())
# y subcadenas ('postre' in cat) en la fase de generación.

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
    w1: float = None,  # Mantenidos por compatibilidad pero ignorados
    w2: float = None,
    w3: float = None,
    satisfaccion_media: float = 3.0,
) -> float:
    """
    Calcula la puntuación heurística de un menú con scoring lineal predecible.

    La fórmula se ha simplificado drásticamente a petición académica para
    servir como Baseline puro. 
    - Presupuesto: El presupuesto no aporta "ahorro" en el score. Es un
      límite absoluto (se filtra antes de llamar a esta función).
    - Prioridad Calórica (95%): La desviación sobre el objetivo calórico
      es el componente casi total del score.
    - Precio (5%): Penalización minúscula por precio, usado únicamente como
      desempate si dos menús tienen valores calóricos idénticos.

    Fórmula:
      score = 1.0 - desviacion_calorica - (precio_menu * 0.001)

    Args:
        menu: Diccionario con precio, calorias y plantilla del menú.
        presupuesto: (Ignorado en cálculo, límite absoluto previo).
        calorias_objetivo: Objetivo calórico del usuario (kcal).
        w1, w2, w3: Ignorados (se mantienen para evitar romper llamadas existentes).
        satisfaccion_media: (Ignorada temporalmente hasta ML real).

    Returns:
        Puntuación heurística del menú (float). Mayor = mejor.
    """
    precio = menu.get("precio", 0)
    calorias = menu.get("calorias", 0)

    # ── Prioridad Calórica: Desviación (0 = perfecto, mayor = peor) ──
    desviacion_calorica = (
        abs(calorias - calorias_objetivo) / calorias_objetivo
        if calorias_objetivo > 0
        else 0.0
    )

    # Score base centrado en cumplimiento calórico
    score = 1.0 - desviacion_calorica

    # ── Desempate por precio: penalización minúscula (no bonus agresivo) ──
    score -= (precio * 0.001)

    # ── PENALIZACIÓN POR DÉFICIT CALÓRICO SEVERO ───────
    # Si el menú aporta menos del 60% de las kcal objetivo, el score
    # se hunde drásticamente multiplicándose por 0.1. Esto previene
    # recomendar un "pan" o "postre" suelto si de forma anómala pasara los filtros.
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
    # ── Clasificar platos por categoría (con normalización robusta) ──
    primeros = []
    segundos = []
    postres  = []
    acomps   = []
    
    for p in platos:
        cat = p.get("categoria", "").lower().strip()
        if "primero" in cat or "entrante" in cat:
            primeros.append(p)
        elif "segundo" in cat or "principal" in cat:
            segundos.append(p)
        elif "postre" in cat:
            postres.append(p)
        elif "acompañamiento" in cat or "guarnicion" in cat or "guarnición" in cat:
            acomps.append(p)

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

    # ── Plantilla: Tradicional (Primero + Segundo + Postre + Acompañamiento) ──
    if postres and acomps:
        for p1, p2, postre, acomp in product(primeros, segundos, postres, acomps):
            combinaciones.append(
                {**_combinar_platos([p1, p2, postre, acomp]), "plantilla": "Tradicional"}
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
