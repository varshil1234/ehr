def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 2)

def bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal weight"
    if bmi < 30:
        return "Overweight"
    return "Obese weight"

def target_weight_range(height_cm: float) -> dict:
    height_m = height_cm / 100
    return {
        "min": round(18.5 * (height_m ** 2), 1),
        "max": round(24.9 * (height_m ** 2), 1),
    }
