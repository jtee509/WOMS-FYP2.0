import PageHeader from '../../components/layout/PageHeader';
import { useWarehouse } from '../../api/contexts/WarehouseContext';
import LocationManagementSection from '../settings/LocationManagementSection';
import WarehouseIcon from '@mui/icons-material/Warehouse';

export default function LocationSetupPage() {
  const { selectedWarehouse, loading } = useWarehouse();

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader
          title="Location Setup"
          description="Manage warehouse bin locations and hierarchy"
        />
        <div className="flex justify-center py-16">
          <span className="inline-block w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (!selectedWarehouse) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader
          title="Location Setup"
          description="Manage warehouse bin locations and hierarchy"
        />
        <div className="bg-surface rounded-card shadow-card p-12 flex flex-col items-center gap-4 text-center">
          <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-background text-text-secondary">
            <WarehouseIcon style={{ fontSize: 32 }} />
          </div>
          <div>
            <p className="text-base font-medium text-text-primary">No warehouse selected</p>
            <p className="text-sm text-text-secondary mt-1">
              Select a warehouse from the sidebar to manage its locations.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Location Setup"
        description="Manage warehouse bin locations and hierarchy"
      />

      {/* Warehouse context banner */}
      <div className="flex items-center gap-3 bg-surface rounded-card shadow-card px-5 py-3">
        <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary/10 text-primary">
          <WarehouseIcon fontSize="small" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-text-primary truncate">
            {selectedWarehouse.warehouse_name}
          </p>
          <p className="text-xs text-text-secondary">
            {selectedWarehouse.location_count ?? 0} location{(selectedWarehouse.location_count ?? 0) !== 1 ? 's' : ''}
            {' '}&middot;{' '}
            <span className={selectedWarehouse.is_active ? 'text-emerald-600' : 'text-text-secondary'}>
              {selectedWarehouse.is_active ? 'Active' : 'Inactive'}
            </span>
          </p>
        </div>
      </div>

      {/* Location management — uses the selected warehouse, no dropdown */}
      <LocationManagementSection
        overrideWarehouseId={selectedWarehouse.id}
        overrideWarehouseName={selectedWarehouse.warehouse_name}
        generatorPath="/warehouse/locations/generator"
      />
    </div>
  );
}
