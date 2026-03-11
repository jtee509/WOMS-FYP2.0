import ShoppingCartIcon from '@mui/icons-material/ShoppingCart';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import Inventory2Icon from '@mui/icons-material/Inventory2';
import OrderOverviewCard from '../components/dashboard/OrderOverviewCard';
import StatCard from '../components/dashboard/StatCard';
import PlatformDistributionCard from '../components/dashboard/PlatformDistributionCard';
import RecentImportsCard from '../components/dashboard/RecentImportsCard';

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-6">
      {/* Order Overview — full width */}
      <OrderOverviewCard />

      {/* Stat cards row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6">
        <StatCard
          label="Total Orders"
          value="1,247"
          change="+12.3%"
          changeType="up"
          variant="gradient"
          icon={<ShoppingCartIcon />}
        />
        <StatCard
          label="Pending Orders"
          value="84"
          change="+3.2%"
          changeType="up"
          icon={<HourglassEmptyIcon />}
        />
        <StatCard
          label="Completed"
          value="1,102"
          change="+8.1%"
          changeType="up"
          icon={<CheckCircleIcon />}
        />
        <StatCard
          label="Items in Catalogue"
          value="1,900"
          icon={<Inventory2Icon />}
        />
      </div>

      {/* Bottom row — distribution + recent imports */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PlatformDistributionCard />
        <RecentImportsCard />
      </div>
    </div>
  );
}
