import { Outlet } from "react-router-dom";
import { MenuBar } from "@/components/MenuBar";

export function AppShell() {
  return (
    <div className="min-h-screen bg-[#f1f1f1] text-[#414041]">
      <MenuBar />
      <main className="mx-auto w-full max-w-10xl px-4 py-6 md:px-6">
        <Outlet />
      </main>
    </div>
  );
}
