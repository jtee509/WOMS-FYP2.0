interface StatCardProps {
  label: string;
  value: string;
  change?: string;
  changeType?: 'up' | 'down';
  variant?: 'default' | 'gradient';
  icon: React.ReactNode;
}

function MiniSparkline({ color }: { color: string }) {
  return (
    <svg viewBox="0 0 80 32" className="w-20 h-8" preserveAspectRatio="none">
      <polyline
        points="0,28 12,20 24,24 36,12 48,16 60,6 72,10 80,4"
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function StatCard({
  label,
  value,
  change,
  changeType = 'up',
  variant = 'default',
  icon,
}: StatCardProps) {
  const isGradient = variant === 'gradient';

  return (
    <div
      className={`rounded-card p-5 flex items-center justify-between ${
        isGradient
          ? 'stat-card-gradient text-white shadow-card'
          : 'bg-surface text-text-primary shadow-card'
      }`}
    >
      <div className="flex flex-col gap-1">
        <div
          className={`w-10 h-10 rounded-default flex items-center justify-center ${
            isGradient ? 'bg-white/20' : 'bg-primary/10'
          }`}
        >
          <span className={isGradient ? 'text-white' : 'text-primary'}>
            {icon}
          </span>
        </div>
        <span
          className={`text-2xl font-bold mt-2 ${
            isGradient ? 'text-white' : 'text-text-primary'
          }`}
        >
          {value}
        </span>
        <span
          className={`text-sm ${
            isGradient ? 'text-white/80' : 'text-text-secondary'
          }`}
        >
          {label}
        </span>
        {change && (
          <span
            className={`text-xs font-medium ${
              isGradient
                ? 'text-white/90'
                : changeType === 'up'
                  ? 'text-success'
                  : 'text-error'
            }`}
          >
            {changeType === 'up' ? '\u25B2' : '\u25BC'} {change}
          </span>
        )}
      </div>
      <MiniSparkline color={isGradient ? 'rgba(255,255,255,0.5)' : 'var(--color-primary)'} />
    </div>
  );
}
