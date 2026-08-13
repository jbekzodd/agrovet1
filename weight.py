"""
AgroVet AI — Vazn hisoblash moduli
"""


def calc_cattle_weight(girth_cm: float, length_cm: float) -> float:
    return round((girth_cm ** 2) * length_cm / 10838, 1)


def calc_sheep_goat_weight(girth_cm: float, length_cm: float) -> float:
    return round((girth_cm ** 2) * length_cm / 13000, 1)


FORMULAS = {
    "cattle": calc_cattle_weight,
    "sheep": calc_sheep_goat_weight,
}
