import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";
import type { ReactNode } from "react";

interface ProtectedRouteProps {
  requiredGroup?: string;
  children?: ReactNode;
}

export function ProtectedRoute({
  requiredGroup,
  children,
}: ProtectedRouteProps) {
  const location = useLocation();
  const { groups, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <main className="mx-auto w-full max-w-7xl px-4 py-6 md:px-6">
        <div className="space-y-3 rounded-3xl border border-stone-300/70 bg-stone-50/90 p-6 shadow-[0_24px_60px_rgba(75,54,35,0.12)]">
          <h1 className="font-serif text-2xl font-semibold">Loading session</h1>
          <p className="text-sm text-stone-600 md:text-base">
            Checking your backend session and permissions.
          </p>
        </div>
      </main>
    );
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: `${location.pathname}${location.search}` }}
      />
    );
  }

  if (requiredGroup && !groups.includes(requiredGroup)) {
    return <Navigate to="/unauthorized" replace />;
  }

  if (children) {
    return <>{children}</>;
  }

  return <Outlet />;
}
