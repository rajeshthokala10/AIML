import { useEffect, useState } from "react";
import { dietPlan, getDietPlanFoods, type DietPlanFood, type DietPlanRequest, type DietPlanResponse, type MealSlot } from "../api";

const ACTIVITIES = ["Sedentary", "Light", "Moderate", "Active", "Very active"];

const MEAL_KEYS: MealSlot[] = ["morning", "mid_morning", "lunch", "evening", "dinner", "late_night"];
const MEAL_LABELS_EN: Record<string, string> = {
  morning: "Morning / Breakfast",
  mid_morning: "Mid-morning",
  lunch: "Lunch",
  evening: "Evening",
  dinner: "Dinner",
  late_night: "Late night",
};
const MEAL_LABELS_TE: Record<string, string> = {
  morning: "ఉదయం / అల్పాహారం",
  mid_morning: "మిడ్-మార్నింగ్",
  lunch: "మధ్యాహ్న భోజనం",
  evening: "సాయంత్రం",
  dinner: "రాత్రి భోజనం",
  late_night: "రాత్రి తర్వాత",
};

const initialSelections: Record<string, string[]> = {
  morning: [],
  mid_morning: [],
  lunch: [],
  evening: [],
  dinner: [],
  late_night: [],
};

export default function DietPlanPage() {
  const [lang, setLang] = useState<"te" | "en">("en");
  const [age, setAge] = useState(30);
  const [activity, setActivity] = useState("Moderate");
  const [foodsBySlot, setFoodsBySlot] = useState<Record<string, DietPlanFood[]>>({});
  const [selections, setSelections] = useState<Record<string, string[]>>(initialSelections);
  const [result, setResult] = useState<DietPlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const labels = lang === "te" ? MEAL_LABELS_TE : MEAL_LABELS_EN;

  useEffect(() => {
    Promise.all(MEAL_KEYS.map((slot) => getDietPlanFoods(lang, slot).then((r) => ({ slot, foods: r.foods }))))
      .then((results) => {
        const bySlot: Record<string, DietPlanFood[]> = {};
        results.forEach(({ slot, foods }) => {
          bySlot[slot] = foods;
        });
        setFoodsBySlot(bySlot);
      })
      .catch(() => setFoodsBySlot({}));
  }, [lang]);

  const addFood = (mealKey: string, foodId: string) => {
    if (!foodId) return;
    setSelections((s) => ({
      ...s,
      [mealKey]: s[mealKey].includes(foodId) ? s[mealKey] : [...s[mealKey], foodId],
    }));
  };

  const removeFood = (mealKey: string, foodId: string) => {
    setSelections((s) => ({
      ...s,
      [mealKey]: s[mealKey].filter((id) => id !== foodId),
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setResult(null);
    setLoading(true);
    try {
      const body: DietPlanRequest = {
        age: Math.max(1, Math.min(120, age)),
        activity,
        lang,
        morning: selections.morning,
        mid_morning: selections.mid_morning,
        lunch: selections.lunch,
        evening: selections.evening,
        dinner: selections.dinner,
        late_night: selections.late_night,
      };
      const res = await dietPlan(body);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  const allFoods = Object.values(foodsBySlot).flat();
  const getLabel = (foodId: string) => allFoods.find((f) => f.id === foodId)?.label ?? foodId;

  return (
    <div className="space-y-8">
      <div className="rounded-2xl bg-white/90 p-6 shadow-lg backdrop-blur">
        <h1 className="text-2xl font-bold text-slate-800">
          {lang === "te" ? "డైట్ ప్లాన్" : "Diet Plan"}
        </h1>
        <p className="mt-1 text-slate-600">
          {lang === "te"
            ? "వయస్సు, జీవనశైలి మరియు రోజువారీ ఆహార అలవాట్లను ఎంచుకోండి. పోషకాహార చార్ట్ మరియు సిఫార్సులను పొందండి."
            : "Select your age, lifestyle, and daily food habits. Get a nutrition chart and recommendations."}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="rounded-2xl bg-white/90 p-6 shadow-lg backdrop-blur">
          <h2 className="mb-4 text-lg font-semibold text-slate-800">
            {lang === "te" ? "భాష / Language" : "Language"}
          </h2>
          <div className="flex gap-4">
            <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-teal-200 bg-teal-50/50 px-4 py-2 transition hover:bg-teal-50">
              <input
                type="radio"
                name="lang"
                checked={lang === "te"}
                onChange={() => setLang("te")}
                className="h-4 w-4 text-teal-600"
              />
              <span className="font-medium text-slate-700">తెలుగు</span>
            </label>
            <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-teal-200 bg-teal-50/50 px-4 py-2 transition hover:bg-teal-50">
              <input
                type="radio"
                name="lang"
                checked={lang === "en"}
                onChange={() => setLang("en")}
                className="h-4 w-4 text-teal-600"
              />
              <span className="font-medium text-slate-700">English</span>
            </label>
          </div>
        </div>

        <div className="rounded-2xl bg-white/90 p-6 shadow-lg backdrop-blur">
          <h2 className="mb-4 text-lg font-semibold text-slate-800">
            {lang === "te" ? "ప్రొఫైల్" : "Profile"}
          </h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-slate-700">
                {lang === "te" ? "వయస్సు" : "Age"}
              </label>
              <input
                type="number"
                min={1}
                max={120}
                value={age}
                onChange={(e) => setAge(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-4 py-2 text-slate-900 focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700">
                {lang === "te" ? "ఆక్టివిటీ స్థాయి" : "Activity level"}
              </label>
              <select
                value={activity}
                onChange={(e) => setActivity(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-4 py-2 text-slate-900 focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
              >
                {ACTIVITIES.map((a) => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="rounded-2xl bg-white/90 p-6 shadow-lg backdrop-blur">
          <h2 className="mb-4 text-lg font-semibold text-slate-800">
            {lang === "te" ? "ఆహార అలవాట్లు (రోజువారీ)" : "Food habits (typical day)"}
          </h2>
          <p className="mb-4 text-sm text-slate-600">
            {lang === "te" ? "ప్రతి భోజనానికి డ్రాప్‌డౌన్ నుండి ఎన్ని ఐటెమ్లు అయినా ఎంచుకోండి." : "Select one or more items from the dropdown for each meal."}
          </p>
          <div className="space-y-5">
            {MEAL_KEYS.map((key) => (
              <div key={key} className="rounded-xl border border-slate-200 bg-slate-50/50 p-4">
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  {labels[key]}
                </label>
                <div className="flex flex-wrap items-center gap-2">
                  <select
                    className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
                    value=""
                    onChange={(e) => {
                      addFood(key, e.target.value);
                      e.target.value = "";
                    }}
                  >
                    <option value="">
                      {lang === "te" ? "+ ఐటెమ్ ఎంచుకోండి" : "+ Select item"}
                    </option>
                    {(foodsBySlot[key] || []).map((f) => (
                      <option key={f.id} value={f.id}>{f.label}</option>
                    ))}
                  </select>
                  {selections[key].map((id) => (
                    <span
                      key={id}
                      className="inline-flex items-center gap-1 rounded-full bg-teal-100 px-3 py-1 text-sm font-medium text-teal-800"
                    >
                      {getLabel(id)}
                      <button
                        type="button"
                        onClick={() => removeFood(key, id)}
                        className="ml-1 rounded-full p-0.5 hover:bg-teal-200"
                        aria-label="Remove"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="rounded-xl bg-teal-600 px-8 py-3 text-base font-semibold text-white shadow-md transition hover:bg-teal-700 disabled:opacity-50"
        >
          {loading
            ? (lang === "te" ? "చార్ట్ రూపొందిస్తోంది…" : "Generating chart…")
            : (lang === "te" ? "పోషకాహార చార్ట్ మరియు సిఫార్సులు పొందండి" : "Get nutrition chart & recommendations")}
        </button>
      </form>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-6">
          <div className="rounded-2xl bg-white/90 p-6 shadow-lg backdrop-blur">
            <h2 className="mb-3 text-lg font-semibold text-slate-800">
              {lang === "te" ? "సారాంశం" : "Summary"}
            </h2>
            <p className="text-slate-700">{result.summary}</p>
          </div>

          <div className="overflow-hidden rounded-2xl bg-white/90 shadow-lg backdrop-blur">
            <div className="overflow-x-auto p-6">
              <h2 className="mb-4 text-lg font-semibold text-slate-800">
                {lang === "te" ? "రోజువారీ పోషకాహారం (మీరు తీసుకునేవి)" : "Daily nutrition (what you're consuming)"}
              </h2>
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead>
                  <tr className="bg-teal-50">
                    {result.chart.headers.map((h, i) => (
                      <th key={i} className="px-4 py-3 text-left font-medium text-slate-700">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 bg-white">
                  {result.chart.rows.map((row, i) => (
                    <tr
                      key={i}
                      className={
                        row[1] === "(subtotal)" || row[1] === "(ఉపమొత్తం)"
                          ? "bg-slate-50 font-medium"
                          : row[0] === "TOTAL (day)" || row[0] === "మొత్తం (రోజు)"
                          ? "bg-teal-50 font-semibold"
                          : ""
                      }
                    >
                      {row.map((cell, j) => (
                        <td key={j} className="whitespace-nowrap px-4 py-2 text-slate-800">
                          {typeof cell === "number" ? (Number.isInteger(cell) ? cell : cell.toFixed(1)) : cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {result.ai_suggestion && (
            <div className="rounded-2xl border-2 border-teal-200 bg-teal-50/50 p-6 shadow-lg backdrop-blur">
              <h2 className="mb-3 text-lg font-semibold text-teal-800">
                {lang === "te" ? "AI డైట్ సూచన" : "AI diet suggestion"}
              </h2>
              <p className="whitespace-pre-wrap text-slate-700">{result.ai_suggestion}</p>
            </div>
          )}
          <div className="rounded-2xl bg-white/90 p-6 shadow-lg backdrop-blur">
            <h2 className="mb-3 text-lg font-semibold text-slate-800">
              {lang === "te" ? "సిఫార్సులు" : "Recommendations"}
            </h2>
            <div className="space-y-2 text-slate-700">
              {result.recommendations.split("\n").map((line, i) => {
                if (!line.trim()) return null;
                const content = line.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
                  part.startsWith("**") && part.endsWith("**") ? (
                    <strong key={j}>{part.slice(2, -2)}</strong>
                  ) : (
                    part
                  )
                );
                return (
                  <p key={i} className={line.startsWith("**") ? "mt-3 font-medium text-slate-900" : ""}>
                    {content}
                  </p>
                );
              })}
            </div>
          </div>
        </div>
      )}

      <p className="text-xs text-slate-500">
        {lang === "te" ? "సమాచార ప్రయోజనాల కోసం మాత్రమే. డైటీషియన్ లేదా వైద్యుడి ప్రత్యామ్నాయం కాదు." : "For informational use only. Not a substitute for a dietitian or doctor."}
      </p>
    </div>
  );
}
