import { Routes, Route } from 'react-router-dom';
import MainLayout from './components/layout/MainLayout';
import LoginPage from './pages/LoginPage';
import ProtectedRoute from './components/auth/ProtectedRoute';
import DashboardPage from './pages/DashboardPage';
import OrderImportPage from './pages/OrderImportPage';
import ReferencePage from './pages/ReferencePage';
import MLSyncPage from './pages/MLSyncPage';
import NotFoundPage from './pages/NotFoundPage';

export default function App() {
  return (
    <Routes>
      {/* Login — standalone page, no sidebar/appbar */}
      <Route path="/login" element={<LoginPage />} />

      {/* All other pages — protected, wrapped in MainLayout */}
      <Route
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/orders/import" element={<OrderImportPage />} />
        <Route path="/reference" element={<ReferencePage />} />
        <Route path="/ml" element={<MLSyncPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
