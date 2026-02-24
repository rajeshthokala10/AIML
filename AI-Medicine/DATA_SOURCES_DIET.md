# Diet Plan — Open Source Health Data (South Indian Focus)

The **diet plan** uses open-source–style data for **South Indian foods**, with inputs separated by **time of day** (breakfast, lunch, dinner, snack) and **AI-driven** suggestions.

---

## 1. South Indian Food Database

- **File**: `data/diet_plan/south_indian_foods.json`
- **Content**: South Indian breakfast (idli, dosa, upma, pongal, vada, pesarattu, uttapam, poha, filter coffee, tea, milk, banana), **snack** (bajji, bonda, murukku, mixture, nuts, biscuit, vada, tea, coffee, banana), **lunch** (rice, sambar, rasam, curd, curd rice, tamarind rice, lemon rice, dal, potato/okra/beans/cabbage/brinjal/tomato curries, papad, chicken/fish/egg curry, chapati, paratha, buttermilk), **dinner** (rice, chapati, dal, curd, potato curry, vegetables, sambar, milk).
- **Meal types**: Each food has `meal_type`: `["breakfast"]`, `["snack"]`, `["lunch"]`, `["dinner"]`, or combined (e.g. `["lunch", "dinner"]`). Dropdowns are filtered by **Breakfast** (morning), **Lunch**, **Dinner**, and **Snack** (mid-morning, evening, late night).
- **Nutrients**: Per-100g values (calories, protein, carbs, fat, fiber, iron, calcium, vitamin C, sodium) in IFCT/INDB style.

---

## 2. Open Source References (Health / Nutrient Data)

- **IFCT 2017** (Indian Food Composition Tables): 528 foods, NIN; [GitHub: ifct2017/ifct2017](https://github.com/ifct2017/ifct2017), [Zenodo](https://zenodo.org/records/7088653).
- **Indian Nutrient Databank (INDB)**: 1,014 Indian recipes, per 100g and per serving; [Anuvaad / INDB](https://www.anuvaad.org.in/indian-nutrient-databank/).
- **Kaggle – Indian Food Nutrition**: [Indian Food Nutritional Values Dataset](https://www.kaggle.com/datasets/batthulavinay/indian-food-nutrition/data).

Values in `south_indian_foods.json` are aligned with these sources; you can extend or replace the file with exports from IFCT/INDB.

---

## 3. Input by Time of Day

- **Morning / Breakfast**: Only foods with `meal_type` containing `breakfast` (idli, dosa, upma, pongal, vada, etc.).
- **Mid-morning / Evening / Late night**: Only `snack` foods (bajji, bonda, murukku, nuts, tea, etc.).
- **Lunch**: Only `lunch` foods (rice, sambar, rasam, curries, dal, etc.).
- **Dinner**: Only `dinner` foods (rice, chapati, dal, curd, vegetables, etc.).

So all options and curries reflect **South Indian** items and the **correct meal** (breakfast vs lunch vs dinner).

---

## 4. AI-Driven Model

- **Rule-based**: Chart, summary, and nutrient-based recommendations (macros + micronutrients) from `backend/diet_plan.py`.
- **AI suggestion**: Short, AI-generated diet tips (2–3 sentences) using the health SLM (`backend/inference.generate`) from age, activity, and consumed totals; returned as `ai_suggestion` in the API and shown in the UI as **“AI diet suggestion”**.

---

## 5. Extending the Database

- Add or edit entries in `south_indian_foods.json` (same schema: `name`, `name_te`, `meal_type`, `per_100g`, `default_portion_g`).
- Or build this file from IFCT/INDB/Kaggle (filter South Indian, map to breakfast/lunch/dinner/snack) and place it at `data/diet_plan/south_indian_foods.json`; the app uses it when present.
