import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClientProvider, QueryClient } from "@tanstack/react-query";
import AppLayout from "./components/layout/AppLayout";
import DashboardPage from "./pages/DashboardPage";
import FundDetailPage from "./pages/FundDetailPage";
import DataEntryPage from "./pages/DataEntryPage";
import DataOverviewPage from "./pages/DataOverviewPage";
import ReportsPage from "./pages/ReportsPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 1000 * 60 * 5 }, // 5 min
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        <AppLayout>
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/fund/:fundId" element={<FundDetailPage />} />
            <Route path="/data" element={<DataEntryPage />} />
            <Route path="/data-overview" element={<DataOverviewPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AppLayout>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
