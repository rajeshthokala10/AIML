const API_BASE = import.meta.env.VITE_API_URL || "/api";

export async function chat(question: string, lang: "te" | "en"): Promise<{ response: string }> {
  const form = new FormData();
  form.append("question", question);
  form.append("lang", lang);
  const r = await fetch(`${API_BASE}/chat`, { method: "POST", body: form });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function chatVoice(file: File, lang: "te" | "en"): Promise<Blob> {
  const form = new FormData();
  form.append("file", file);
  form.append("lang", lang);
  form.append("return_audio", "true");
  const r = await fetch(`${API_BASE}/chat/voice`, { method: "POST", body: form });
  if (!r.ok) throw new Error(await r.text());
  return r.blob();
}

export type MealSlot = "morning" | "mid_morning" | "lunch" | "evening" | "dinner" | "late_night";

export interface DietPlanFood {
  id: string;
  name_en: string;
  name_te: string;
  label: string;
}

export async function getDietPlanFoods(lang: "te" | "en", meal_slot?: MealSlot): Promise<{ foods: DietPlanFood[] }> {
  const params = new URLSearchParams({ lang });
  if (meal_slot) params.set("meal_slot", meal_slot);
  const r = await fetch(`${API_BASE}/diet-plan/foods?${params}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export interface DietPlanRequest {
  age: number;
  activity: string;
  lang: "te" | "en";
  morning: string[] | string;
  mid_morning: string[] | string;
  lunch: string[] | string;
  evening: string[] | string;
  dinner: string[] | string;
  late_night: string[] | string;
}

export interface DietPlanResponse {
  chart: { headers: string[]; rows: (string | number)[][] };
  summary: string;
  recommendations: string;
  ai_suggestion?: string;
  consumed: Record<string, number>;
  targets: Record<string, number>;
}

export async function dietPlan(body: DietPlanRequest): Promise<DietPlanResponse> {
  const r = await fetch(`${API_BASE}/diet-plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
