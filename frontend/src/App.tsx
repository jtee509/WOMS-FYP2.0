import { Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import MainLayout from './components/layout/MainLayout';
import LoginPage from './pages/LoginPage';
import ProtectedRoute from './components/auth/ProtectedRoute';
import { WarehouseProvider } from './api/contexts/WarehouseContext';
import DashboardPage from './pages/DashboardPage';
import OrderImportPage from './pages/OrderImportPage';
import ReferencePage from './pages/ReferencePage';
import MLSyncPage from './pages/MLSyncPage';
import SettingsPage from './pages/settings/SettingsPage';
import UsersRolesPage from './pages/admin/UsersRolesPage';
import AuditLogsPage from './pages/admin/AuditLogsPage';
import ItemsListPage from './pages/items/ItemsListPage';
import ItemFormPage from './pages/items/ItemFormPage';
import CatalogCreatePage from './pages/items/CatalogCreatePage';
import CatalogUploadPage from './pages/items/CatalogUploadPage';
import InventoryLevelsPage from './pages/warehouse/InventoryLevelsPage';
import InventoryMovementsPage from './pages/warehouse/InventoryMovementsPage';
import InventoryAlertsPage from './pages/warehouse/InventoryAlertsPage';
import BundleFormPage from './pages/bundles/BundleFormPage';
import LocationSetupPage from './pages/warehouse/LocationSetupPage';
import LocationGeneratorPage from './pages/warehouse/LocationGeneratorPage';
import PlaceholderPage from './pages/PlaceholderPage';
import NotFoundPage from './pages/NotFoundPage';

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
    <Routes>
      {/* Login — standalone page, no sidebar/appbar */}
      <Route path="/login" element={<LoginPage />} />

      {/* All other pages — protected, wrapped in MainLayout */}
      <Route
        element={
          <ProtectedRoute>
            <WarehouseProvider>
              <MainLayout />
            </WarehouseProvider>
          </ProtectedRoute>
        }
      >
        {/* Dashboard */}
        <Route path="/" element={<DashboardPage />} />
        <Route path="/dashboard/metrics" element={<DashboardPage />} />
        <Route path="/dashboard/alerts" element={<PlaceholderPage />} />

        {/* Catalog */}
        <Route path="/catalog/items" element={<ItemsListPage />} />
        <Route path="/catalog/items/upload" element={<CatalogUploadPage />} />
        <Route path="/catalog/items/new" element={<CatalogCreatePage />} />
        <Route path="/catalog/items/:id/edit" element={<ItemFormPage />} />
        <Route path="/catalog/bundles" element={<Navigate to="/catalog/items" replace />} />
        <Route path="/catalog/bundles/new" element={<Navigate to="/catalog/items/new" replace />} />
        <Route path="/catalog/bundles/:id/edit" element={<BundleFormPage />} />
        <Route path="/catalog/translation" element={<PlaceholderPage />} />
        <Route path="/catalog/history" element={<PlaceholderPage />} />

        {/* Inventory */}
        <Route path="/inventory/levels" element={<InventoryLevelsPage />} />
        <Route path="/inventory/movements" element={<InventoryMovementsPage />} />
<Route path="/inventory/alerts" element={<InventoryAlertsPage />} />
        <Route path="/inventory/stock-check" element={<PlaceholderPage />} />
        <Route path="/inventory/triggers" element={<PlaceholderPage />} />

        {/* Orders */}
        <Route path="/orders/details" element={<PlaceholderPage />} />
        <Route path="/orders/mass-ship" element={<PlaceholderPage />} />
        <Route path="/orders/cancellation" element={<PlaceholderPage />} />
        <Route path="/orders/returns" element={<PlaceholderPage />} />
        <Route path="/orders/import" element={<OrderImportPage />} />

        {/* Shipments */}
        <Route path="/shipments/management" element={<PlaceholderPage />} />
        <Route path="/shipments/group" element={<PlaceholderPage />} />
        <Route path="/shipments/schedule" element={<PlaceholderPage />} />
        <Route path="/shipments/fleet" element={<PlaceholderPage />} />

        {/* Seller Management */}
        <Route path="/sellers/profiles" element={<PlaceholderPage />} />
        <Route path="/sellers/import" element={<PlaceholderPage />} />
        <Route path="/sellers/new-order" element={<PlaceholderPage />} />
        <Route path="/sellers/allocation" element={<PlaceholderPage />} />

        {/* Warehouse */}
        <Route path="/warehouse/locations" element={<LocationSetupPage />} />
        <Route path="/warehouse/locations/generator" element={<LocationGeneratorPage />} />

        {/* Settings sub-pages — must be before the wildcard */}
        <Route path="/settings/users" element={<UsersRolesPage />} />
        <Route path="/settings/audit" element={<AuditLogsPage />} />

        {/* Settings — wildcard lets SettingsPage handle remaining sub-paths */}
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/settings/*" element={<SettingsPage />} />

        {/* Legacy / misc (not in nav but kept for backward compat) */}
        <Route path="/reference" element={<ReferencePage />} />
        <Route path="/ml" element={<MLSyncPage />} />

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
    </QueryClientProvider>
  );
}
