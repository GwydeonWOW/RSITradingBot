import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Layout } from "@/components/layout/Layout";

const DashboardPage = lazy(() => import("@/pages/DashboardPage").then((m) => ({ default: m.DashboardPage })));
const StrategyPage = lazy(() => import("@/pages/StrategyPage").then((m) => ({ default: m.StrategyPage })));
const BacktestPage = lazy(() => import("@/pages/BacktestPage").then((m) => ({ default: m.BacktestPage })));
const OrdersPage = lazy(() => import("@/pages/OrdersPage").then((m) => ({ default: m.OrdersPage })));
const PerformancePage = lazy(() => import("@/pages/PerformancePage").then((m) => ({ default: m.PerformancePage })));
const SettingsPage = lazy(() => import("@/pages/SettingsPage").then((m) => ({ default: m.SettingsPage })));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function PageLoader() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-sm text-gray-600">Loading...</div>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<DashboardPage />} />
              <Route path="strategy" element={<StrategyPage />} />
              <Route path="backtest" element={<BacktestPage />} />
              <Route path="orders" element={<OrdersPage />} />
              <Route path="performance" element={<PerformancePage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
