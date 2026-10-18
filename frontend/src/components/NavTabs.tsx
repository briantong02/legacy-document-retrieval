import { NavLink } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import { navigationItems } from "@/config/navigation";

export function NavTabs() {
  const { groups } = useAuth();
  const visibleItems = navigationItems.filter(
    (item) => !item.requiredGroup || groups.includes(item.requiredGroup),
  );

  return (
    <nav
      className="border-b border-[#ebebeb] bg-white"
      aria-label="Document options"
    >
      <div className="mx-auto w-full max-w-7xl overflow-x-auto px-4 md:px-6">
        <ul className="flex w-full min-w-max items-stretch justify-center">
          {visibleItems.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                title={item.label}
                className={({ isActive }) =>
                  [
                    "inline-flex h-12 items-center gap-2 border-b-2 px-4 text-sm transition",
                    isActive
                      ? "border-b2b-red font-bold text-[#414041]"
                      : "border-transparent text-[#666666] hover:border-[#dddddd] hover:text-[#414041]",
                  ].join(" ")
                }
              >
                <span>{item.tabLabel}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  );
}
