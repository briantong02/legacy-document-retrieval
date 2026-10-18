import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import { Button } from "@/components/ui/Button";
import duxLogo from "@/assets/b2b/dux-logo.png";
import loginBackground from "@/assets/b2b/img/login-background3.webp";

const fieldClass =
  "mt-1.5 block w-full rounded-md border border-[#dddddd] bg-white px-3 py-2 text-sm text-[#414041] transition placeholder:text-[#999999] focus:border-b2b-red focus:outline-none focus-visible:ring-2 focus-visible:ring-b2b-red/30 disabled:bg-[#f6f6f6]";

const labelClass = "block text-xs font-bold uppercase text-[#666666]";

interface LocationState {
  from?: string;
}

export function Login() {
  const { signIn, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await signIn(username, password);
      setPassword("");
      const from = (location.state as LocationState | null)?.from;
      navigate(from ?? "/", { replace: true });
    } catch (caught) {
      setPassword("");
      setError(
        caught instanceof Error && caught.message
          ? caught.message
          : "Unable to sign in. Please try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  // An authenticated user has no business on the login page - this is what makes the
  // dev auth bypass work without a sign-in, and stops a stale /login URL trapping you.
  if (isAuthenticated) {
    const from = (location.state as LocationState | null)?.from;
    return <Navigate to={from ?? "/"} replace />;
  }

  if (isLoading) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#f1f1f1] md:flex">
      <section className="flex min-h-screen w-full items-center justify-center bg-white px-6 py-8 md:w-[40%] md:px-10">
        <div className="w-full max-w-[360px]">
          <img
            src={duxLogo}
            alt="DuxVault"
            className="mx-auto h-auto w-[172px] -translate-y-2.5"
          />
          <h1 className="mt-3.5 text-center font-display text-[22px] font-bold uppercase tracking-[0.01em] text-[#414041]">
            Legacy Document Retrieval
          </h1>

          <h2 className="mt-10 text-center font-sans text-[16px] font-bold text-[#414041]">
            Welcome back!
          </h2>

          <p className="mx-auto mt-5 max-w-[300px] text-center text-sm text-[#666666]">
            Sign in with your network account to continue.
          </p>

          <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className={labelClass} htmlFor="username">
                Username
              </label>
              <input
                id="username"
                name="username"
                className={fieldClass}
                placeholder="CORP\username"
                autoComplete="username"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                required
                disabled={isSubmitting}
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </div>

            <div>
              <label className={labelClass} htmlFor="password">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                className={fieldClass}
                autoComplete="current-password"
                required
                disabled={isSubmitting}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </div>

            {error ? (
              <p
                role="alert"
                className="rounded-md border border-b2b-red/30 bg-b2b-red-soft px-3 py-2 text-sm text-b2b-red"
              >
                {error}
              </p>
            ) : null}

            <Button
              type="submit"
              className="w-full"
              disabled={isSubmitting || !username || !password}
            >
              {isSubmitting ? "Signing in…" : "Sign In"}
            </Button>
          </form>
        </div>
      </section>

      <section
        className="hidden min-h-screen flex-1 bg-center bg-cover bg-no-repeat md:block"
        style={{ backgroundImage: `url(${loginBackground})` }}
        aria-label="Factory floor"
      >
        <div className="h-full w-full" />
      </section>
    </div>
  );
}
