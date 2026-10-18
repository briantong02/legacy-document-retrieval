import { Link } from "react-router-dom";

export function NotFound() {
  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-6 md:px-6">
      <div className="space-y-3 rounded-3xl border border-stone-300/70 bg-stone-50/90 p-6 shadow-[0_24px_60px_rgba(75,54,35,0.12)]">
        <span className="inline-flex items-center rounded-full bg-teal-600/10 px-2.5 py-1 text-xs font-semibold text-teal-800">
          404
        </span>
        <h1 className="font-serif text-3xl font-semibold">Page not found</h1>
        <p className="text-stone-600">
          The route you requested does not exist in the DUX Vault frontend.
        </p>
        <Link
          className="inline-flex min-h-11 items-center justify-center rounded-xl border border-transparent bg-teal-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-teal-800"
          to="/ar-registration"
        >
          Go to the app
        </Link>
      </div>
    </main>
  );
}
