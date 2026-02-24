import { Link } from "react-router-dom";
import { useState, useEffect } from "react";

const QUOTES = [
  "Your health is an investment, not an expense.",
  "Prevention is better than cure — start today.",
  "Small steps in nutrition lead to a healthier life.",
  "AI meets care: personalized health at your fingertips.",
  "Listen to your body; empower it with the right choices.",
];

export default function Landing() {
  const [quoteIndex, setQuoteIndex] = useState(0);

  useEffect(() => {
    const t = setInterval(() => {
      setQuoteIndex((i) => (i + 1) % QUOTES.length);
    }, 5000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="landing-page relative min-h-screen flex flex-col">
      {/* Background: AI + Doctor themed images with overlay */}
      <div className="landing-bg absolute inset-0 -z-10" aria-hidden />
      <div className="absolute inset-0 -z-10 bg-gradient-to-b from-teal-900/85 via-cyan-900/80 to-teal-900/90" aria-hidden />

      {/* Top: Motivational quotes */}
      <section className="quotes-section px-4 pt-8 pb-6 text-center">
        <div className="mx-auto max-w-3xl">
          <p className="text-lg font-medium text-white/95 drop-shadow-md md:text-xl">
            &ldquo;{QUOTES[quoteIndex]}&rdquo;
          </p>
          <div className="mt-3 flex justify-center gap-1">
            {QUOTES.map((_, i) => (
              <button
                key={i}
                type="button"
                aria-label={`Quote ${i + 1}`}
                onClick={() => setQuoteIndex(i)}
                className={`h-1.5 w-1.5 rounded-full transition ${i === quoteIndex ? "bg-white scale-125" : "bg-white/50"}`}
              />
            ))}
          </div>
        </div>
      </section>

      {/* Main content: hero + CTAs */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-10">
        <div className="mx-auto max-w-2xl text-center">
          <h1 className="text-4xl font-bold tracking-tight text-white drop-shadow-lg md:text-5xl">
            AI-Medicine
          </h1>
          <p className="mt-4 text-xl text-cyan-100/95">
            AI + Doctor at the core — personalized health advice and diet plans.
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <Link
              to="/health"
              className="rounded-xl bg-white px-8 py-4 text-lg font-semibold text-teal-800 shadow-lg transition hover:bg-cyan-50 hover:shadow-xl"
            >
              Health Q&A
            </Link>
            <Link
              to="/diet-plan"
              className="rounded-xl border-2 border-white/90 bg-white/10 px-8 py-4 text-lg font-semibold text-white backdrop-blur transition hover:bg-white/20"
            >
              Diet Plan
            </Link>
          </div>
        </div>
      </main>

      {/* Bottom: Developed by Radit Software Solutions Pvt Ltd */}
      <footer className="landing-footer mt-auto border-t border-white/20 bg-black/20 py-4 text-center backdrop-blur-sm">
        <p className="text-sm font-medium text-white/90">
          Developed by <span className="font-semibold text-white">Radit Software Solutions Pvt Ltd</span>
        </p>
      </footer>
    </div>
  );
}
