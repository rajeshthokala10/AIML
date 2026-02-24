"""
AI-Medicine: Diet Plan — separate URL (port 7861).
Inputs: Age, lifestyle, food habits (morning to night).
Output: Daily nutrition chart + recommendations (macros + micronutrients, routine modifications).
Training data: open source (English) — see data/diet_plan/ and DATA_SOURCES_DIET.md.
"""
from __future__ import annotations

import os
from pathlib import Path

import gradio as gr

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
import sys
sys.path.insert(0, str(ROOT))

from backend.diet_plan import (
    build_chart_and_totals,
    generate_recommendations,
    get_targets,
)


HEADERS = [
    "Meal",
    "Item",
    "Calories",
    "Protein (g)",
    "Carbs (g)",
    "Fat (g)",
    "Fiber (g)",
    "Iron (mg)",
    "Calcium (mg)",
    "Vitamin C (mg)",
    "Sodium (mg)",
]


def run_diet_plan(
    age_val,
    activity: str,
    morning: str,
    mid_morning: str,
    lunch: str,
    evening: str,
    dinner: str,
    late_night: str,
) -> tuple[list[list], str, str]:
    """Build chart and recommendations. Returns (table_rows, summary, recommendations)."""
    try:
        age = int(age_val) if age_val is not None else 30
    except (ValueError, TypeError):
        age = 30
    age = max(1, min(120, age))
    activity = activity or "Moderate"

    rows, consumed, targets = build_chart_and_totals(
        age, activity, morning or "", mid_morning or "", lunch or "", evening or "", dinner or "", late_night or "",
    )
    recs = generate_recommendations(consumed, targets, age, activity)

    summary = (
        f"**Your daily totals** (consumed): "
        f"Calories {consumed['calories']} kcal, "
        f"Protein {consumed['protein_g']}g, Carbs {consumed['carbs_g']}g, Fat {consumed['fat_g']}g, "
        f"Fiber {consumed['fiber_g']}g. "
        f"**Targets** (age {age}, {activity}): "
        f"Calories ~{targets['calories']} kcal, Protein ~{targets['protein_g']}g, Fiber ~{targets['fiber_g']}g."
    )
    return rows, summary, recs


with gr.Blocks(title="AI-Medicine: Diet Plan", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Diet Plan — Daily Nutrition & Recommendations")
    gr.Markdown(
        "Enter your **age**, **lifestyle**, and **food habits** (morning to night). "
        "You'll get a **nutrition chart** of what you're consuming and **recommendations** to modify your routine (macros + micronutrients)."
    )

    with gr.Row():
        age = gr.Number(label="Age", value=30, minimum=1, maximum=120, precision=0)
        activity = gr.Dropdown(
            label="Lifestyle / Activity level",
            choices=["Sedentary", "Light", "Moderate", "Active", "Very active"],
            value="Moderate",
        )

    gr.Markdown("### Food habits (what you typically eat in a day)")
    morning = gr.Textbox(
        label="Morning / Breakfast",
        placeholder="e.g. 2 idlis, sambar, coffee",
        lines=2,
    )
    mid_morning = gr.Textbox(
        label="Mid-morning",
        placeholder="e.g. fruit, nuts, tea",
        lines=2,
    )
    lunch = gr.Textbox(
        label="Lunch",
        placeholder="e.g. rice, dal, vegetables, curd, 1 roti",
        lines=2,
    )
    evening = gr.Textbox(
        label="Evening",
        placeholder="e.g. tea, 2 biscuits, banana",
        lines=2,
    )
    dinner = gr.Textbox(
        label="Dinner",
        placeholder="e.g. chapati, paneer, vegetables, salad",
        lines=2,
    )
    late_night = gr.Textbox(
        label="Late night",
        placeholder="e.g. milk, or leave empty",
        lines=2,
    )

    submit = gr.Button("Get nutrition chart & recommendations")

    summary = gr.Markdown(label="Summary")
    chart = gr.Dataframe(
        label="Daily nutrition (what you're consuming)",
        headers=HEADERS,
        datatype=["str", "str", "number", "number", "number", "number", "number", "number", "number", "number", "number"],
    )
    recommendations = gr.Markdown(label="Recommendations (how to modify routine, including micronutrients)")

    submit.click(
        fn=run_diet_plan,
        inputs=[age, activity, morning, mid_morning, lunch, evening, dinner, late_night],
        outputs=[chart, summary, recommendations],
    )

    gr.Markdown("---\n*For informational use only. Not a substitute for a dietitian or doctor.*")

if __name__ == "__main__":
    # Separate URL: run on port 7861 (main health app can run on 7860)
    demo.launch(server_name="0.0.0.0", server_port=7861)
