import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("App error:", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-slate-100 px-4">
          <div className="max-w-md rounded-xl border border-red-200 bg-white p-6 shadow-lg">
            <h1 className="text-lg font-semibold text-red-800">Something went wrong</h1>
            <p className="mt-2 text-sm text-slate-600">
              The page failed to load. Try refreshing. If the problem continues, check the browser console (F12 → Console) for details.
            </p>
            <button
              type="button"
              onClick={() => this.setState({ hasError: false })}
              className="mt-4 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700"
            >
              Try again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
