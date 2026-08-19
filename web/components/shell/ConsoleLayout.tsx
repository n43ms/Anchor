import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { ModeBanner } from "./ModeBanner";

export function ConsoleLayout() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-surface-page font-ui text-ink-primary">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <ModeBanner />
        <main className="flex-1 overflow-y-auto p-6 transition-all duration-base">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
