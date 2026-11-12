def compute_grade(marks: float) -> str:
    """Daraja kulingana na alama (0-100). Badilisha hapa kama shule yako inatumia mgawanyo tofauti."""
    if marks >= 75:
        return "A"
    if marks >= 65:
        return "B"
    if marks >= 45:
        return "C"
    if marks >= 30:
        return "D"
    return "F"