import { useNavigate } from 'react-router-dom';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import UploadFileIcon from '@mui/icons-material/UploadFile';

function PlaceholderChart() {
  return (
    <svg viewBox="0 0 600 200" className="w-full h-48" preserveAspectRatio="none">
      {/* Grid lines */}
      {[0, 50, 100, 150, 200].map((y) => (
        <line
          key={y}
          x1="0"
          y1={y}
          x2="600"
          y2={y}
          stroke="var(--color-divider)"
          strokeWidth="0.5"
          strokeDasharray="4 4"
        />
      ))}

      {/* Orders line (primary blue) */}
      <polyline
        points="0,160 50,140 100,120 150,90 200,100 250,70 300,80 350,50 400,60 450,40 500,55 550,30 600,20"
        fill="none"
        stroke="var(--color-primary)"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Returns line (pink) */}
      <polyline
        points="0,180 50,175 100,170 150,165 200,172 250,160 300,168 350,155 400,162 450,150 500,158 550,148 600,145"
        fill="none"
        stroke="var(--color-chart-pink)"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Highlight dot on orders line */}
      <circle cx="450" cy="40" r="5" fill="var(--color-primary)" />
      <circle cx="450" cy="40" r="8" fill="var(--color-primary)" opacity="0.2" />
      {/* Tooltip-like label */}
      <rect x="430" y="16" width="40" height="20" rx="4" fill="var(--color-primary)" />
      <text x="450" y="30" textAnchor="middle" fill="white" fontSize="10" fontWeight="600">
        258
      </text>
    </svg>
  );
}

function ChartLegend() {
  return (
    <div className="flex items-center gap-6 mt-2">
      <div className="flex items-center gap-2">
        <span className="w-3 h-3 rounded-full bg-primary" />
        <span className="text-sm text-text-secondary">Orders</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="w-3 h-3 rounded-full bg-chart-pink" />
        <span className="text-sm text-text-secondary">Returns</span>
      </div>
    </div>
  );
}

export default function OrderOverviewCard() {
  const navigate = useNavigate();

  return (
    <div className="bg-surface rounded-card shadow-card p-6">
      {/* Header row */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-text-primary">Order Overview</h2>
        <div className="flex items-center gap-3">
          <span className="text-sm text-text-secondary border border-divider rounded-default px-3 py-1.5">
            This Month
          </span>
          <button
            onClick={() => navigate('/orders/import')}
            className="btn-gradient-coral text-white text-sm font-medium px-4 py-2 rounded-default flex items-center gap-1.5 cursor-pointer"
          >
            <UploadFileIcon fontSize="small" />
            Import Orders
          </button>
        </div>
      </div>

      {/* Metric + Chart */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Left: Big metric */}
        <div className="flex flex-col justify-center min-w-[180px]">
          <span className="text-4xl font-bold text-text-primary">1,247</span>
          <span className="text-sm text-text-secondary mt-1">Total Orders</span>
          <div className="flex items-center gap-1 mt-2">
            <TrendingUpIcon fontSize="small" className="text-success" />
            <span className="text-sm font-medium text-success">+12.3%</span>
            <span className="text-xs text-text-secondary ml-1">vs last month</span>
          </div>
        </div>

        {/* Right: Chart */}
        <div className="flex-grow">
          <PlaceholderChart />
          <div className="flex items-center justify-between mt-1">
            <ChartLegend />
            <div className="flex gap-4 text-xs text-text-secondary">
              {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].map((m) => (
                <span key={m}>{m}</span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
