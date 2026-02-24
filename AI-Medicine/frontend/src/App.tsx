import { Suspense, lazy } from "react";
import { Routes, Route, Link, useLocation } from "react-router-dom";

const Landing = lazy(() => import("./pages/Landing"));
const Health = lazy(() => import("./pages/Health"));
const DietPlan = lazy(() => import("./pages/DietPlan"));

function Nav() {
  const loc = useLocation();
  const isLanding = loc.pathname === "/";
  const isHealth = loc.pathname === "/health";
  const isDiet = loc.pathname === "/diet-plan";
  return (
    <nav className={`border-b border-teal-200/60 shadow-sm backdrop-blur ${isLanding ? "border-white/20 bg-black/20" : "bg-white/95"}`}>
      <div className="mx-auto flex h-14 max-w-5xl items-center gap-6 px-4">
        <Link
          to="/"
          className={`text-lg font-bold ${isLanding ? "text-white" : "text-teal-800"}`}
        >
          AI-Medicine
        </Link>
        <Link
          to="/health"
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${isHealth ? "bg-teal-100 text-teal-800" : isLanding ? "text-white/90 hover:bg-white/20" : "text-slate-600 hover:bg-teal-50"}`}
        >
          Health Q&A
        </Link>
        <Link
          to="/diet-plan"
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${isDiet ? "bg-teal-100 text-teal-800" : isLanding ? "text-white/90 hover:bg-white/20" : "text-slate-600 hover:bg-teal-50"}`}
        >
          Diet Plan
        </Link>
      </div>
    </nav>
  );
}

function PageFallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center text-slate-500">
      Loading page…
    </div>
  );
}

export default function App() {
  const location = useLocation();
  const isLanding = location.pathname === "/";

  return (
    <div className={isLanding ? "min-h-screen" : "app-theme min-h-screen"}>
      <Nav />
      <main className={isLanding ? "max-w-none px-0" : "mx-auto max-w-5xl px-4 py-8"}>
        <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/health" element={<Health />} />
            <Route path="/diet-plan" element={<DietPlan />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  );
}
