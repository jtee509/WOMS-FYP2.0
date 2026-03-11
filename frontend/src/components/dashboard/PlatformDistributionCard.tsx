const PLATFORMS = [
  { name: 'Shopee', value: 45, color: 'var(--color-primary)' },
  { name: 'Lazada', value: 32, color: 'var(--color-secondary)' },
  { name: 'TikTok', value: 23, color: 'var(--color-success)' },
];

const RADIUS = 60;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

function DonutChart() {
  let offset = 0;

  return (
    <svg viewBox="0 0 160 160" className="w-40 h-40 mx-auto">
      {/* Background circle */}
      <circle
        cx="80"
        cy="80"
        r={RADIUS}
        fill="none"
        stroke="var(--color-divider)"
        strokeWidth="18"
      />
      {/* Segments */}
      {PLATFORMS.map((platform) => {
        const dashLen = (platform.value / 100) * CIRCUMFERENCE;
        const currentOffset = offset;
        offset += dashLen;
        return (
          <circle
            key={platform.name}
            cx="80"
            cy="80"
            r={RADIUS}
            fill="none"
            stroke={platform.color}
            strokeWidth="18"
            strokeDasharray={`${dashLen} ${CIRCUMFERENCE - dashLen}`}
            strokeDashoffset={-currentOffset}
            strokeLinecap="round"
            transform="rotate(-90 80 80)"
          />
        );
      })}
      {/* Center label */}
      <text x="80" y="76" textAnchor="middle" className="text-text-primary" fontSize="20" fontWeight="700">
        517
      </text>
      <text x="80" y="94" textAnchor="middle" className="text-text-secondary" fontSize="10">
        Total
      </text>
    </svg>
  );
}

export default function PlatformDistributionCard() {
  return (
    <div className="bg-surface rounded-card shadow-card p-6">
      <h3 className="text-base font-semibold text-text-primary mb-4">Platform Distribution</h3>

      <DonutChart />

      {/* Legend */}
      <div className="flex justify-center gap-6 mt-4">
        {PLATFORMS.map((platform) => (
          <div key={platform.name} className="flex items-center gap-2">
            <span
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: platform.color }}
            />
            <span className="text-sm text-text-secondary">
              {platform.name}
            </span>
            <span className="text-sm font-medium text-text-primary">
              {platform.value}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
