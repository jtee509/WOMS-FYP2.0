import PageHeader from '../components/layout/PageHeader';

export default function MLSyncPage() {
  return (
    <div>
      <PageHeader
        title="ML Staging"
        description="Sync order data to the ML staging database"
      />
      <div className="bg-info-bg text-info-text rounded-default px-4 py-3 text-sm">
        ML sync controls will be implemented here. Initialise the ML schema
        and sync staged orders from woms_db to ml_woms_db.
      </div>
    </div>
  );
}
