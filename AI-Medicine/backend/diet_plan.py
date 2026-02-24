"""
Diet plan backend: parse meals, aggregate nutrients, build chart, generate recommendations.
Uses open-source style food DB (data/diet_plan/food_nutrients.json).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FOOD_DB_PATH = ROOT / "data" / "diet_plan" / "food_nutrients.json"
SOUTH_INDIAN_FOODS_PATH = ROOT / "data" / "diet_plan" / "south_indian_foods.json"

# Meal slot -> meal_type for South Indian DB (breakfast, snack, lunch, dinner)
MEAL_SLOT_TO_TYPE = {
    "morning": "breakfast",
    "mid_morning": "snack",
    "lunch": "lunch",
    "evening": "snack",
    "dinner": "dinner",
    "late_night": "snack",
}

# Telugu labels for dropdown and chart (key = food name in DB).
FOOD_NAME_TE = {
    "rice": "అన్నం", "roti": "రోటి", "idli": "ఇడ్లి", "dosa": "దోసె", "sambar": "సాంబార్",
    "curd": "పెరుగు", "milk": "పాలు", "egg": "గుడ్డు", "bread": "బ్రెడ్", "oatmeal": "ఓట్మీల్",
    "coffee": "కాఫీ", "tea": "చా", "dal": "పప్పు", "chicken": "కోడి", "fish": "చేప",
    "potato": "ఆలూ", "vegetables": "కూరగాయలు", "salad": "సలాడ్", "fruit": "పండు",
    "banana": "అరటి", "apple": "ఆపిల్", "nuts": "కాయలు", "biscuit": "బిస్కెట్",
    "juice": "జ్యూస్", "paneer": "పనీర్", "chapati": "చపాతి", "pasta": "పాస్టా", "pizza": "పిజ్జా",
}

# Chart headers: en / te
CHART_HEADERS_EN = ["Meal", "Item", "Calories", "Protein (g)", "Carbs (g)", "Fat (g)", "Fiber (g)", "Iron (mg)", "Calcium (mg)", "Vitamin C (mg)", "Sodium (mg)"]
CHART_HEADERS_TE = ["భోజనం", "ఐటెమ్", "కేలరీలు", "ప్రోటీన్ (g)", "కార్బోహైడ్రేట్స్ (g)", "ఫ్యాట్ (g)", "ఫైబర్ (g)", "ఇనుము (mg)", "కాల్షియం (mg)", "విటమిన్ C (mg)", "సోడియం (mg)"]

# Meal names for chart: en / te
MEAL_NAMES_EN = ("Morning / Breakfast", "Mid-morning", "Lunch", "Evening", "Dinner", "Late night")
MEAL_NAMES_TE = ("ఉదయం / అల్పాహారం", "మిడ్-మార్నింగ్", "మధ్యాహ్న భోజనం", "సాయంత్రం", "రాత్రి భోజనం", "రాత్రి తర్వాత")

# Rough daily targets (adult, 2000 cal baseline). Adjusted by age and activity in get_targets().
DEFAULT_DAILY = {
    "calories": 2000,
    "protein_g": 50,
    "carbs_g": 250,
    "fat_g": 65,
    "fiber_g": 25,
    "iron_mg": 18,
    "calcium_mg": 1000,
    "vitamin_c_mg": 90,
    "sodium_mg": 2300,
}


def load_food_db() -> list[dict]:
    """Load food -> nutrients mapping. Prefer South Indian DB; fallback to food_nutrients.json."""
    if SOUTH_INDIAN_FOODS_PATH.exists():
        with open(SOUTH_INDIAN_FOODS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw = data.get("foods", [])
        # Normalize: meal_type may be list; ensure per_100g, default_portion_g
        out = []
        for entry in raw:
            e = dict(entry)
            if isinstance(e.get("meal_type"), str):
                e["meal_type"] = [e["meal_type"]]
            if "name_te" not in e:
                e["name_te"] = FOOD_NAME_TE.get(e.get("name", ""), e.get("name", ""))
            out.append(e)
        return out
    if not FOOD_DB_PATH.exists():
        return []
    with open(FOOD_DB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    raw = data.get("foods", [])
    for entry in raw:
        if "meal_type" not in entry:
            entry["meal_type"] = ["breakfast", "snack", "lunch", "dinner"]
    return raw


def get_foods_for_dropdown(lang: str = "en", meal_slot: str | None = None) -> list[dict]:
    """Return list of {id, name_en, name_te, label} for dropdown. If meal_slot given, filter by meal_type (South Indian DB)."""
    db = load_food_db()
    meal_type = MEAL_SLOT_TO_TYPE.get(meal_slot, None) if meal_slot else None
    out = []
    for entry in db:
        name = entry.get("name", "")
        if meal_type is not None:
            types = entry.get("meal_type") or []
            if isinstance(types, str):
                types = [types]
            if meal_type not in types:
                continue
        name_te = entry.get("name_te") or FOOD_NAME_TE.get(name, name)
        label = name_te if lang == "te" else name
        out.append({"id": name, "name_en": name, "name_te": name_te, "label": label})
    return out


def get_food_by_id(food_id: str, db: list[dict] | None = None) -> dict | None:
    """Get food entry by id (name)."""
    if db is None:
        db = load_food_db()
    for entry in db:
        if entry.get("name") == food_id:
            return entry
    return None


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().strip())


def _parse_portion(text: str) -> tuple[float, str]:
    """Extract number and food from '2 idlis' or '1 cup sambar'. Returns (multiplier, food_name)."""
    text = _normalize(text)
    # e.g. "2 idlis", "1 cup sambar", "half cup milk", "idli"
    m = re.match(r"^(\d+(?:\.\d+)?)\s+(.+)$", text)
    if m:
        try:
            n = float(m.group(1))
            food = m.group(2).strip()
            return n, food
        except ValueError:
            pass
    m = re.match(r"^(?:half|1/2)\s+(.+)$", text)
    if m:
        return 0.5, m.group(1).strip()
    return 1.0, text


def _match_food(food_name: str, db: list[dict]) -> dict | None:
    """Find best matching food in DB (by substring)."""
    food_name = _normalize(food_name)
    # Remove common words
    for w in ["cup", "bowl", "plate", "piece", "pieces", "glass", "slice", "spoon"]:
        food_name = food_name.replace(w, " ").strip()
    food_name = _normalize(food_name)
    for entry in db:
        name = _normalize(entry["name"])
        if name in food_name or food_name in name:
            return entry
    # Try single-word match
    words = food_name.split()
    for entry in db:
        name = _normalize(entry["name"])
        if any(w == name or name in w for w in words if len(w) > 2):
            return entry
    return None


def parse_meals(
    morning: str, mid_morning: str, lunch: str, evening: str, dinner: str, late_night: str,
) -> list[tuple[str, list[tuple[str, float, dict]]]]:
    """
    Parse meal text into (meal_name, [(food_display, multiplier, food_entry), ...]).
    Each meal text: "2 idlis, sambar, coffee" -> split by comma, parse each.
    """
    db = load_food_db()
    meals = [
        ("Morning / Breakfast", morning),
        ("Mid-morning", mid_morning),
        ("Lunch", lunch),
        ("Evening", evening),
        ("Dinner", dinner),
        ("Late night", late_night),
    ]
    result = []
    for meal_name, text in meals:
        if not (text or "").strip():
            result.append((meal_name, []))
            continue
        items = []
        for part in re.split(r"[,;]", text):
            part = part.strip()
            if not part:
                continue
            mult, food_name = _parse_portion(part)
            entry = _match_food(food_name, db)
            if entry:
                items.append((part.strip(), mult, entry))
            else:
                # Unknown food: try generic "vegetables" or "fruit" for single words
                w = _normalize(food_name).split()[0] if food_name else ""
                if w in ("veg", "vegetable", "vegetables", "curry"):
                    entry = _match_food("vegetables", db)
                    if entry:
                        items.append((part.strip(), mult, entry))
                elif w in ("fruit", "fruits"):
                    entry = _match_food("fruit", db)
                    if entry:
                        items.append((part.strip(), mult, entry))
        result.append((meal_name, items))
    return result


def aggregate_nutrients(parsed: list[tuple[str, list[tuple[str, float, dict]]]]) -> tuple[list[list[Any]], dict]:
    """
    Build per-meal and total nutrient table. Returns (rows for table, total_dict).
    Table rows: [meal, item, calories, protein_g, carbs_g, fat_g, fiber_g, iron_mg, calcium_mg, vitamin_c_mg, sodium_mg]
    """
    rows = []
    total = {k: 0.0 for k in DEFAULT_DAILY.keys()}
    key_map = {
        "calories": "calories",
        "protein": "protein_g",
        "carbs": "carbs_g",
        "fat": "fat_g",
        "fiber": "fiber_g",
        "iron_mg": "iron_mg",
        "calcium_mg": "calcium_mg",
        "vitamin_c_mg": "vitamin_c_mg",
        "sodium_mg": "sodium_mg",
    }
    for meal_name, items in parsed:
        meal_totals = {k: 0.0 for k in total}
        for display, mult, entry in items:
            p100 = entry.get("per_100g", {})
            portion_g = entry.get("default_portion_g", 100) * mult
            scale = portion_g / 100.0
            row = [meal_name, display]
            for db_key, our_key in key_map.items():
                val = p100.get(db_key, 0) * scale
                row.append(round(val, 1))
                total[our_key] += val
                meal_totals[our_key] += val
            rows.append(row)
        if items:
            rows.append([meal_name, "(subtotal)", round(meal_totals["calories"], 1),
                        round(meal_totals["protein_g"], 1), round(meal_totals["carbs_g"], 1),
                        round(meal_totals["fat_g"], 1), round(meal_totals["fiber_g"], 1),
                        round(meal_totals["iron_mg"], 1), round(meal_totals["calcium_mg"], 1),
                        round(meal_totals["vitamin_c_mg"], 1), round(meal_totals["sodium_mg"], 1)])
    total = {k: round(v, 1) for k, v in total.items()}
    if rows:
        rows.append(["TOTAL (day)", "", total["calories"], total["protein_g"], total["carbs_g"],
                     total["fat_g"], total["fiber_g"], total["iron_mg"], total["calcium_mg"],
                     total["vitamin_c_mg"], total["sodium_mg"]])
    return rows, total


def get_targets(age: int, activity: str) -> dict:
    """Daily targets by age and activity (simplified)."""
    base = DEFAULT_DAILY.copy()
    # Age: reduce calories slightly for 50+
    if age >= 50:
        base["calories"] = int(base["calories"] * 0.9)
        base["calcium_mg"] = 1200
    if age >= 70:
        base["calories"] = int(base["calories"] * 0.85)
    # Activity multiplier for calories
    mult = {"Sedentary": 1.0, "Light": 1.15, "Moderate": 1.3, "Active": 1.5, "Very active": 1.7}.get(activity, 1.0)
    base["calories"] = int(base["calories"] * mult)
    base["protein_g"] = max(50, int(base["calories"] / 40))  # rough
    return base


def build_chart_and_totals(
    age: int,
    activity: str,
    morning: str, mid_morning: str, lunch: str, evening: str, dinner: str, late_night: str,
) -> tuple[list[list[Any]], dict, dict]:
    """Parse meals, aggregate, return (table_rows, consumed_totals, target_totals)."""
    parsed = parse_meals(morning, mid_morning, lunch, evening, dinner, late_night)
    rows, consumed = aggregate_nutrients(parsed)
    targets = get_targets(age, activity)
    return rows, consumed, targets


def build_chart_and_totals_from_selections(
    age: int,
    activity: str,
    meals_dict: dict[str, list[str]],
    lang: str = "en",
) -> tuple[list[list[Any]], dict, dict]:
    """Build chart from selected food ids per meal. meals_dict: {morning: [idli, sambar], ...}. lang: en|te for labels."""
    db = load_food_db()
    meal_keys = ["morning", "mid_morning", "lunch", "evening", "dinner", "late_night"]
    meal_names = MEAL_NAMES_TE if lang == "te" else MEAL_NAMES_EN
    parsed = []
    for i, key in enumerate(meal_keys):
        meal_name = meal_names[i]
        ids = meals_dict.get(key) or []
        items = []
        for food_id in ids:
            entry = get_food_by_id(food_id, db)
            if entry:
                name_te = entry.get("name_te") or FOOD_NAME_TE.get(food_id, food_id)
                label = name_te if lang == "te" else food_id
                items.append((label, 1.0, entry))
        parsed.append((meal_name, items))
    rows, consumed = aggregate_nutrients(parsed)
    if lang == "te":
        for row in rows:
            if len(row) > 1 and row[1] == "(subtotal)":
                row[1] = "(ఉపమొత్తం)"
            if len(row) > 0 and row[0] == "TOTAL (day)":
                row[0] = "మొత్తం (రోజు)"
    targets = get_targets(age, activity)
    return rows, consumed, targets


def get_chart_headers(lang: str) -> list[str]:
    """Return chart column headers in requested language."""
    return CHART_HEADERS_TE if lang == "te" else CHART_HEADERS_EN


def generate_recommendations(consumed: dict, targets: dict, age: int, activity: str, lang: str = "en") -> str:
    """Generate text recommendations in English or Telugu."""
    if lang == "te":
        return _generate_recommendations_te(consumed, targets, age, activity)
    return _generate_recommendations_en(consumed, targets, age, activity)


def _generate_recommendations_en(consumed: dict, targets: dict, age: int, activity: str) -> str:
    """Generate recommendations in English."""
    lines = []
    c, t = consumed.get("calories", 0), targets.get("calories", 2000)
    if c < t * 0.85:
        lines.append(f"• **Calories**: You're under target ({c} vs ~{t} kcal). Consider adding a balanced snack (nuts, fruit, or dairy) or slightly larger portions at meals.")
    elif c > t * 1.15:
        lines.append(f"• **Calories**: Intake is above target ({c} vs ~{t} kcal). Consider reducing portion sizes or high-calorie snacks; prefer vegetables and lean protein.")
    else:
        lines.append(f"• **Calories**: Within a reasonable range ({c} kcal). Maintain similar intake for your activity level.")
    p, pt = consumed.get("protein_g", 0), targets.get("protein_g", 50)
    if p < pt * 0.8:
        lines.append(f"• **Protein**: Below target ({p}g vs ~{pt}g). Add dal, eggs, chicken, fish, paneer, or curd to meals.")
    elif p >= pt:
        lines.append(f"• **Protein**: Adequate ({p}g).")
    fib, ft = consumed.get("fiber_g", 0), targets.get("fiber_g", 25)
    if fib < ft * 0.8:
        lines.append(f"• **Fiber**: Low ({fib}g vs ~{ft}g). Add whole grains, vegetables, fruits, and dal; prefer whole fruit over juice.")
    iron, it = consumed.get("iron_mg", 0), targets.get("iron_mg", 18)
    if iron < it * 0.7:
        lines.append(f"• **Iron**: Below target ({iron} mg). Include green leafy vegetables, dal, nuts, and optionally lean meat; pair with vitamin C for absorption.")
    cal, ct = consumed.get("calcium_mg", 0), targets.get("calcium_mg", 1000)
    if cal < ct * 0.8:
        lines.append(f"• **Calcium**: Below target ({cal} mg). Add milk, curd, paneer, or fortified foods; consider green vegetables.")
    vc, vct = consumed.get("vitamin_c_mg", 0), targets.get("vitamin_c_mg", 90)
    if vc < vct * 0.7:
        lines.append(f"• **Vitamin C**: Low ({vc} mg). Add citrus, amla, tomatoes, and fresh vegetables.")
    sod = consumed.get("sodium_mg", 0)
    if sod > 2300:
        lines.append(f"• **Sodium**: High ({sod} mg). Reduce added salt and processed snacks; use herbs and spices for flavor.")
    lines.append("\n**Routine suggestions:**")
    lines.append("• Spread meals across the day; include a mid-morning and evening snack if needed.")
    lines.append("• Prefer whole foods over packaged; include vegetables at lunch and dinner.")
    lines.append("• Stay hydrated; limit sugary drinks.")
    return "\n".join(lines)


def generate_ai_diet_suggestion(age: int, activity: str, consumed: dict, targets: dict, lang: str = "en") -> str:
    """AI-driven short diet suggestion using health SLM. Returns 2-3 brief tips in requested language."""
    try:
        from backend.inference import generate
    except Exception:
        return ""
    c, p, fib = consumed.get("calories", 0), consumed.get("protein_g", 0), consumed.get("fiber_g", 0)
    t_c, t_p = targets.get("calories", 2000), targets.get("protein_g", 50)
    if lang == "te":
        prompt = (
            f"వయస్సు {age}, శారీరక శ్రమ: {activity}. రోజువారీ: కేలరీలు {c} (లక్ష్యం ~{t_c}), ప్రోటీన్ {p}g (లక్ష్యం ~{t_p}), ఫైబర్ {fib}g. "
            "దక్షిణ భారత ఆహారంతో 2-3 చిన్న డైట్ చిట్కాలు ఇవ్వండి. చాలా సంక్షిప్తంగా రాయండి."
        )
    else:
        prompt = (
            f"Age {age}, activity: {activity}. Daily: calories {c} (target ~{t_c}), protein {p}g (target ~{t_p}), fiber {fib}g. "
            "Give 2-3 short diet tips for South Indian food. Keep it very brief."
        )
    try:
        reply = generate(prompt, lang=lang, max_new_tokens=150)
        return (reply or "").strip()[:500]
    except Exception:
        return ""


def _generate_recommendations_te(consumed: dict, targets: dict, age: int, activity: str) -> str:
    """Generate recommendations in Telugu."""
    lines = []
    c, t = consumed.get("calories", 0), targets.get("calories", 2000)
    if c < t * 0.85:
        lines.append(f"• **కేలరీలు**: లక్ష్యం కంటే తక్కువ ({c} vs ~{t} kcal). సంతులిత స్నాక్ (కాయలు, పండు, పెరుగు) లేదా కొంచెం ఎక్కువ పోర్షన్లు జోడించండి.")
    elif c > t * 1.15:
        lines.append(f"• **కేలరీలు**: లక్ష్యం కంటే ఎక్కువ ({c} vs ~{t} kcal). పోర్షన్ సైజ్ తగ్గించండి లేదా అధిక కేలరీ స్నాక్స్ తగ్గించండి; కూరగాయలు మరియు లీన్ ప్రోటీన్ ప్రాధాన్యం ఇవ్వండి.")
    else:
        lines.append(f"• **కేలరీలు**: సరైన పరిధిలో ({c} kcal). ఇలాగే కొనసాగించండి.")
    p, pt = consumed.get("protein_g", 0), targets.get("protein_g", 50)
    if p < pt * 0.8:
        lines.append(f"• **ప్రోటీన్**: లక్ష్యం కంటే తక్కువ ({p}g vs ~{pt}g). పప్పు, గుడ్డు, కోడి, చేప, పనీర్ లేదా పెరుగు జోడించండి.")
    elif p >= pt:
        lines.append(f"• **ప్రోటీన్**: తగినంత ({p}g).")
    fib, ft = consumed.get("fiber_g", 0), targets.get("fiber_g", 25)
    if fib < ft * 0.8:
        lines.append(f"• **ఫైబర్**: తక్కువ ({fib}g vs ~{ft}g). ధాన్యాలు, కూరగాయలు, పండ్లు మరియు పప్పు జోడించండి; జ్యూస్ కంటే పండు ప్రాధాన్యం.")
    iron, it = consumed.get("iron_mg", 0), targets.get("iron_mg", 18)
    if iron < it * 0.7:
        lines.append(f"• **ఇనుము**: లక్ష్యం కంటే తక్కువ ({iron} mg). ఆకుకూరలు, పప్పు, కాయలు జోడించండి; విటమిన్ C తో తీసుకోండి.")
    cal, ct = consumed.get("calcium_mg", 0), targets.get("calcium_mg", 1000)
    if cal < ct * 0.8:
        lines.append(f"• **కాల్షియం**: లక్ష్యం కంటే తక్కువ ({cal} mg). పాలు, పెరుగు, పనీర్ జోడించండి.")
    vc, vct = consumed.get("vitamin_c_mg", 0), targets.get("vitamin_c_mg", 90)
    if vc < vct * 0.7:
        lines.append(f"• **విటమిన్ C**: తక్కువ ({vc} mg). సిట్రస్, ఉసిరి, టమాటా జోడించండి.")
    sod = consumed.get("sodium_mg", 0)
    if sod > 2300:
        lines.append(f"• **సోడియం**: ఎక్కువ ({sod} mg). ఉప్పు మరియు ప్రాసెస్డ్ స్నాక్స్ తగ్గించండి.")
    lines.append("\n**రోజువారీ సూచనలు:**")
    lines.append("• భోజనాలను రోజంతా పంచుకోండి; మిడ్-మార్నింగ్ మరియు సాయంత్ర స్నాక్ జోడించండి.")
    lines.append("• ప్యాకేజ్డ్ కంటే సహజ ఆహారం; మధ్యాహ్నం మరియు రాత్రి కూరగాయలు జోడించండి.")
    lines.append("• నీరు తగినంత త్రాగండి; చక్కెర పానీయాలు తగ్గించండి.")
    return "\n".join(lines)
