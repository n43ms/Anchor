import { Sidebar } from "@/components/shell/Sidebar";
import { ModeBanner } from "@/components/shell/ModeBanner";

export default function ConsoleLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <ModeBanner />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
