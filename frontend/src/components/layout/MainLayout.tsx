import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Sidebar, Menu, MenuItem } from 'react-pro-sidebar';
import MenuIcon from '@mui/icons-material/Menu';
import DashboardIcon from '@mui/icons-material/Dashboard';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import StorageIcon from '@mui/icons-material/Storage';
import SyncIcon from '@mui/icons-material/Sync';
import useIsMobile from '../hooks/useIsMobile';

const NAV_ITEMS = [
  { label: 'Dashboard', path: '/', icon: <DashboardIcon /> },
  { label: 'Order Import', path: '/orders/import', icon: <UploadFileIcon /> },
  { label: 'Reference Data', path: '/reference', icon: <StorageIcon /> },
  { label: 'ML Staging', path: '/ml', icon: <SyncIcon /> },
];

const SIDEBAR_WIDTH = 260;
const SIDEBAR_COLLAPSED_WIDTH = 80;

export default function MainLayout() {
  const isMobile = useIsMobile();
  const [collapsed, setCollapsed] = useState(false);
  const [toggled, setToggled] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const handleToggle = () => {
    if (isMobile) {
      setToggled((prev) => !prev);
    } else {
      setCollapsed((prev) => !prev);
    }
  };

  const handleMenuClick = (path: string) => {
    navigate(path);
    if (isMobile) setToggled(false);
  };

  const sidebarWidth = collapsed ? SIDEBAR_COLLAPSED_WIDTH : SIDEBAR_WIDTH;

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <Sidebar
        collapsed={collapsed}
        toggled={toggled}
        onBackdropClick={() => setToggled(false)}
        breakPoint="md"
        backgroundColor="var(--color-surface)"
        rootStyles={{
          borderRight: '1px solid var(--color-divider)',
          height: '100vh',
          position: 'fixed' as const,
          top: 0,
          left: 0,
          zIndex: 1200,
        }}
        width={`${SIDEBAR_WIDTH}px`}
        collapsedWidth={`${SIDEBAR_COLLAPSED_WIDTH}px`}
      >
        {/* Sidebar header */}
        <div
          className="p-4 flex items-center min-h-16 border-b border-divider"
          style={{ justifyContent: collapsed ? 'center' : 'flex-start' }}
        >
          <span className="text-xl font-bold text-primary whitespace-nowrap overflow-hidden">
            {collapsed ? 'W' : 'WOMS'}
          </span>
        </div>

        {/* Navigation menu */}
        <Menu
          menuItemStyles={{
            button: ({ active }: { active: boolean }) => ({
              backgroundColor: active
                ? 'color-mix(in srgb, var(--color-primary) 8%, transparent)'
                : 'transparent',
              color: active
                ? 'var(--color-primary)'
                : 'var(--color-text-primary)',
              fontWeight: active ? 600 : 400,
              '&:hover': {
                backgroundColor:
                  'color-mix(in srgb, var(--color-primary) 4%, transparent)',
              },
            }),
          }}
        >
          {NAV_ITEMS.map((item) => (
            <MenuItem
              key={item.path}
              icon={item.icon}
              active={location.pathname === item.path}
              onClick={() => handleMenuClick(item.path)}
            >
              {item.label}
            </MenuItem>
          ))}
        </Menu>
      </Sidebar>

      {/* Main content area */}
      <main
        className="flex-grow flex flex-col min-h-screen transition-[margin-left] duration-300"
        style={{ marginLeft: isMobile ? 0 : `${sidebarWidth}px` }}
      >
        {/* Top bar */}
        <header className="sticky top-0 z-[1100] bg-surface shadow-appbar">
          <div className="flex items-center min-h-16 px-4">
            <button
              onClick={handleToggle}
              className="mr-4 p-2 rounded-full hover:bg-black/5 cursor-pointer"
              aria-label="Toggle menu"
            >
              <MenuIcon />
            </button>
            <h6 className="text-lg font-semibold whitespace-nowrap overflow-hidden text-ellipsis flex-grow">
              Warehouse Order Management System
            </h6>
          </div>
        </header>

        {/* Page content */}
        <div className="p-6 flex-grow">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
