import { Sidebar } from 'react-pro-sidebar';
import LogoutIcon from '@mui/icons-material/Logout';
import SidebarNav from './SidebarNav';
import LayoutWarehouseSelector from './WarehouseSelector';

export const SIDEBAR_WIDTH = 260;
export const SIDEBAR_COLLAPSED_WIDTH = 80;
const HEADER_HEIGHT = 64;

interface AppSidebarProps {
  collapsed: boolean;
  toggled: boolean;
  onBackdropClick: () => void;
  onNavigate: (path: string) => void;
  onLogout: () => void;
}

export default function AppSidebar({
  collapsed,
  toggled,
  onBackdropClick,
  onNavigate,
  onLogout,
}: AppSidebarProps) {
  return (
    <Sidebar
      collapsed={collapsed}
      toggled={toggled}
      onBackdropClick={onBackdropClick}
      breakPoint="md"
      backgroundColor="var(--color-surface)"
      rootStyles={{
        borderRight: '1px solid var(--color-divider)',
        height: `calc(100vh - ${HEADER_HEIGHT}px)`,
        position: 'fixed' as const,
        top: `${HEADER_HEIGHT}px`,
        left: 0,
        zIndex: 1200,
      }}
      width={`${SIDEBAR_WIDTH}px`}
      collapsedWidth={`${SIDEBAR_COLLAPSED_WIDTH}px`}
    >
      <div className="flex flex-col h-full">
        {/* Warehouse selector */}
        <div className="p-3 border-b border-divider">
          <LayoutWarehouseSelector collapsed={collapsed} />
        </div>

        {/* Navigation — driven by NAV_CONFIG in nav.config.tsx */}
        <div className="flex-1 overflow-y-auto">
          <SidebarNav collapsed={collapsed} onNavigate={onNavigate} />
        </div>

        {/* Logout button */}
        <div className="border-t border-divider p-3">
          <button
            onClick={onLogout}
            className={`flex items-center gap-3 w-full px-4 py-2.5 rounded-default text-text-secondary hover:bg-error-bg hover:text-error cursor-pointer transition-colors ${
              collapsed ? 'justify-center' : ''
            }`}
          >
            <LogoutIcon fontSize="small" />
            {!collapsed && <span className="text-sm">Logout</span>}
          </button>
        </div>
      </div>
    </Sidebar>
  );
}
