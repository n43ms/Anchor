import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ConsoleLayout } from "@/components/shell/ConsoleLayout";
import DashboardPage from "@/app/(console)/page";
import AllRunsPage from "@/app/(console)/runs/page";
import RunDetailPage from "@/app/(console)/runs/[id]/page";
import NeedsReviewPage from "@/app/(console)/needs-review/page";
import NeedsReviewDetailPage from "@/app/(console)/needs-review/[id]/page";
import FleetPage from "@/app/(console)/workers/page";
import DeploymentsPage from "@/app/(console)/workers/deployments/page";
import ToolRegistryPage from "@/app/(console)/tools/page";
import TestRunPage from "@/app/(console)/tools/test-run/page";
import MetricsPage from "@/app/(console)/metrics/page";
import LogsPage from "@/app/(console)/logs/page";
import EnvironmentPage from "@/app/(console)/settings/environment/page";
import PreviewPage from "@/app/(dev)/preview/page";
import { NotFoundPage } from "@/components/shell/NotFoundPage";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ConsoleLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="runs" element={<AllRunsPage />} />
          <Route path="runs/:id" element={<RunDetailPage />} />
          <Route path="needs-review" element={<NeedsReviewPage />} />
          <Route path="needs-review/:id" element={<NeedsReviewDetailPage />} />
          <Route path="workers" element={<FleetPage />} />
          <Route path="workers/deployments" element={<DeploymentsPage />} />
          <Route path="tools" element={<ToolRegistryPage />} />
          <Route path="tools/test-run" element={<TestRunPage />} />
          <Route path="metrics" element={<MetricsPage />} />
          <Route path="logs" element={<LogsPage />} />
          <Route path="settings/environment" element={<EnvironmentPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
        <Route path="/preview" element={<PreviewPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
