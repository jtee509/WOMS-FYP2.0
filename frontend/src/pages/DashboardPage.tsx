import PageHeader from '../components/layout/PageHeader';

export default function DashboardPage() {
  const cards = [
    { label: 'Total Orders', value: '--' },
    { label: 'Platforms', value: '--' },
    { label: 'Active Sellers', value: '--' },
    { label: 'Items in Catalogue', value: '--' },
  ];

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Warehouse Order Management System overview"
      />
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6">
        {cards.map((card) => (
          <div
            key={card.label}
            className="bg-surface rounded-card shadow-card p-5"
          >
            <p className="text-sm text-text-secondary mb-1">{card.label}</p>
            <p className="text-3xl font-semibold text-text-primary">
              {card.value}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
