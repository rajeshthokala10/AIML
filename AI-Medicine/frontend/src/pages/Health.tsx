import { useState, useRef } from "react";
import { chat, chatVoice } from "../api";

type Lang = "te" | "en";

export default function Health() {
  const [lang, setLang] = useState<Lang>("en");
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [inputMode, setInputMode] = useState<"text" | "voice">("text");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    setError("");
    setAudioUrl(null);
    setLoading(true);
    try {
      const res = await chat(question.trim(), lang);
      setResponse(res.response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  const handleVoiceSubmit = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setResponse("");
    setAudioUrl(null);
    setLoading(true);
    try {
      const blob = await chatVoice(file, lang);
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
      setResponse("(Listen to the voice response below)");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Voice request failed");
    } finally {
      setLoading(false);
    }
    e.target.value = "";
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Health Q&A</h1>
        <p className="mt-1 text-slate-600">
          Ask in Telugu or English. Input: text or voice. Response: text and optional voice.
        </p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <label className="mb-2 block text-sm font-medium text-slate-700">Language</label>
        <div className="flex gap-4">
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="radio"
              name="lang"
              checked={lang === "te"}
              onChange={() => setLang("te")}
              className="h-4 w-4 text-emerald-600"
            />
            <span>Telugu</span>
          </label>
          <label className="flex cursor-pointer items-center gap-2">
            <input
              type="radio"
              name="lang"
              checked={lang === "en"}
              onChange={() => setLang("en")}
              className="h-4 w-4 text-emerald-600"
            />
            <span>English</span>
          </label>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex gap-2">
          <button
            type="button"
            onClick={() => setInputMode("text")}
            className={`rounded-lg px-4 py-2 text-sm font-medium ${inputMode === "text" ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-600"}`}
          >
            Text input
          </button>
          <button
            type="button"
            onClick={() => setInputMode("voice")}
            className={`rounded-lg px-4 py-2 text-sm font-medium ${inputMode === "voice" ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-600"}`}
          >
            Voice / Video
          </button>
        </div>

        {inputMode === "text" ? (
          <form onSubmit={handleTextSubmit} className="space-y-4">
            <label className="block text-sm font-medium text-slate-700">Your question</label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={lang === "te" ? "ఉదాహరణ: పోషకాహారంలో ప్రోటీన్ ఎందుకు ముఖ్యం?" : "e.g. Why is protein important in diet?"}
              rows={3}
              className="w-full rounded-lg border border-slate-300 px-4 py-3 text-slate-900 placeholder-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
            <button
              type="submit"
              disabled={loading}
              className="rounded-lg bg-emerald-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              {loading ? "Getting response…" : "Get advice"}
            </button>
            {loading && (
              <p className="mt-2 text-sm text-slate-500">First request may take 1–2 min (loading AI model).</p>
            )}
          </form>
        ) : (
          <div>
            <label className="block text-sm font-medium text-slate-700">Upload audio or video</label>
            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*,video/*"
              onChange={handleVoiceSubmit}
              className="mt-2 block w-full text-sm text-slate-600 file:mr-4 file:rounded-lg file:border-0 file:bg-emerald-50 file:px-4 file:py-2 file:text-emerald-700"
            />
            {loading && <p className="mt-2 text-sm text-slate-500">Processing…</p>}
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {(response || audioUrl) && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="mb-3 text-lg font-semibold text-slate-900">Response</h2>
          {response && (
            <div className="mb-4 whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-slate-800">
              {response}
            </div>
          )}
          {audioUrl && (
            <div className="flex items-center gap-3">
              <audio ref={audioRef} src={audioUrl} controls className="max-w-full" />
            </div>
          )}
        </div>
      )}

      <p className="text-xs text-slate-500">
        Informational health advice only. Not a substitute for professional medical care.
      </p>
    </div>
  );
}
