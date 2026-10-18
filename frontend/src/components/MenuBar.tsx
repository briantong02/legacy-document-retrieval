import { useNavigate } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import { NavTabs } from "@/components/NavTabs";
import { Button } from "@/components/ui/Button";
import duxLogo from "@/assets/b2b/dux-logo.png";

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const first = parts[0] ?? "";
  const last = parts.length > 1 ? (parts[parts.length - 1] ?? "") : "";
  const initials = `${first.charAt(0)}${last.charAt(0)}`;

  return (initials || first.slice(0, 2) || "?").toUpperCase();
}

export function MenuBar() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const displayName = user?.displayName ?? user?.username ?? "Session active";

  async function handleSignOut() {
    await signOut();
    navigate("/login", { replace: true });
  }

  return (
    <header className="sticky top-0 z-20 shadow-b2b">
      <div className="bg-b2b-dark">
        <div className="flex w-full items-center justify-between gap-4 px-4 py-3 md:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <img
              src={duxLogo}
              alt="dux"
              className="h-[34px] w-14 shrink-0 object-contain object-left"
            />
            <span className="truncate font-display text-lg font-medium text-white">
              Legacy Document Retrieval
            </span>
          </div>

          <div className="flex shrink-0 items-center gap-3">
            <div className="flex items-center gap-2">
              <span
                className="grid h-8 w-8 place-items-center rounded-full bg-white/10 text-xs font-bold text-white"
                aria-hidden="true"
              >
                {getInitials(displayName)}
              </span>
              <span className="hidden max-w-[12rem] truncate text-sm text-white sm:block">
                {displayName}
              </span>
            </div>

            <Button
              variant="ghostDark"
              size="sm"
              onClick={() => void handleSignOut()}
            >
              Logout
            </Button>
          </div>
        </div>
      </div>

      <NavTabs />
    </header>
  );
}
