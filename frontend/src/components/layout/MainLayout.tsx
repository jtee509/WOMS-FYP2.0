import { useState } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import useIsMobile from '../hooks/useIsMobile';
import { useAuth } from '../../api/contexts/AuthContext';
import TopBar from './TopBar';
import AppSidebar, { SIDEBAR_WIDTH, SIDEBAR_COLLAPSED_WIDTH } from './AppSidebar';

export default function MainLayout() {
  const isMobile = useIsMobile();
  const [collapsed, setCollapsed] = useState(false);
  const [toggled, setToggled] = useState(false);
  const navigate = useNavigate();
  const { user, logout } = useAuth();

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

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const sidebarWidth = collapsed ? SIDEBAR_COLLAPSED_WIDTH : SIDEBAR_WIDTH;

  return (
    <>
      <TopBar
        user={user}
        onToggleMenu={handleToggle}
        onLogout={handleLogout}
        onNavigate={navigate}
      />

      <div className="flex min-h-screen bg-background pt-16">
        <AppSidebar
          collapsed={collapsed}
          toggled={toggled}
          onBackdropClick={() => setToggled(false)}
          onNavigate={handleMenuClick}
          onLogout={handleLogout}
        />

        <main
          className="flex-grow flex flex-col min-h-[calc(100vh-4rem)] transition-[margin-left] duration-300"
          style={{ marginLeft: isMobile ? 0 : `${sidebarWidth}px` }}
        >
          <div className="p-6 flex-grow">
            <Outlet />
          </div>
        </main>
      </div>
    </>
  );
}
