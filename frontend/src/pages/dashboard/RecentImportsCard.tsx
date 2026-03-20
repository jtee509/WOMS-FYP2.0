import { useNavigate } from 'react-router-dom';

const MOCK_IMPORTS = [
  { batchId: 'IMP-2026-001', platform: 'Shopee', seller: 'Store Alpha', date: '2026-02-28', status: 'Completed', rows: 245 },
  { batchId: 'IMP-2026-002', platform: 'Lazada', seller: 'Store Beta', date: '2026-02-27', status: 'Completed', rows: 189 },
  { batchId: 'IMP-2026-003', platform: 'TikTok', seller: 'Store Gamma', date: '2026-02-27', status: 'Processing', rows: 67 },
  { batchId: 'IMP-2026-004', platform: 'Shopee', seller: 'Store Delta', date: '2026-02-26', status: 'Completed', rows: 312 },
  { batchId: 'IMP-2026-005', platform: 'Lazada', seller: 'Store Alpha', date: '2026-02-25', status: 'Failed', rows: 0 },
];

const PLATFORM_COLORS: Record<string, string> = {
  Shopee: 'var(--color-primary)',
  Lazada: 'var(--color-secondary)',
  TikTok: 'var(--color-success)',
};

const STATUS_STYLES: Record<string, string> = {
  Completed: 'bg-success-bg text-success-text',
  Processing: 'bg-info-bg text-info-text',
  Failed: 'bg-error-bg text-error-text',
};

export default function RecentImportsCard() {
  const navigate = useNavigate();

  return (
    <div className="bg-surface rounded-card shadow-card p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-semibold text-text-primary">Recent Order Imports</h3>
        <button
          onClick={() => navigate('/orders/import')}
          className="text-sm text-primary hover:underline cursor-pointer"
        >
          View All
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-divider text-text-secondary text-left">
              <th className="pb-3 font-medium">Batch ID</th>
              <th className="pb-3 font-medium">Platform</th>
              <th className="pb-3 font-medium">Seller</th>
              <th className="pb-3 font-medium">Date</th>
              <th className="pb-3 font-medium">Status</th>
              <th className="pb-3 font-medium text-right">Rows</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-divider">
            {MOCK_IMPORTS.map((row) => (
              <tr key={row.batchId} className="hover:bg-background/50">
                <td className="py-3 font-medium text-text-primary">{row.batchId}</td>
                <td className="py-3">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: PLATFORM_COLORS[row.platform] ?? 'var(--color-divider)' }}
                    />
                    {row.platform}
                  </div>
                </td>
                <td className="py-3 text-text-secondary">{row.seller}</td>
                <td className="py-3 text-text-secondary">{row.date}</td>
                <td className="py-3">
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      STATUS_STYLES[row.status] ?? ''
                    }`}
                  >
                    {row.status}
                  </span>
                </td>
                <td className="py-3 text-right text-text-primary font-medium">{row.rows}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
