import PageHeader from '../components/layout/PageHeader';

export default function ReferencePage() {
  return (
    <div>
      <PageHeader
        title="Reference Data"
        description="Manage platforms, sellers, and item master data"
      />
      <div className="bg-info-bg text-info-text rounded-default px-4 py-3 text-sm">
        Reference data management will be implemented here. Upload platforms,
        sellers, and item master files to populate the database.
      </div>
    </div>
  );
}
