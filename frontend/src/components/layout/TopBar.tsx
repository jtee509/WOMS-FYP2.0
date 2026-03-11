import { useState, useRef, useEffect } from 'react';
import MenuIcon from '@mui/icons-material/Menu';
import WarehouseIcon from '@mui/icons-material/Warehouse';
import SearchIcon from '@mui/icons-material/Search';
import LogoutIcon from '@mui/icons-material/Logout';
import PersonIcon from '@mui/icons-material/Person';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import NotificationsNoneIcon from '@mui/icons-material/NotificationsNone';
import type { AuthUser } from '../../api/base_types/auth';

interface TopBarProps {
  user: AuthUser | null;
  onToggleMenu: () => void;
  onLogout: () => void;
  onNavigate: (path: string) => void;
}

export default function TopBar({ user, onToggleMenu, onLogout, onNavigate }: TopBarProps) {
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  const userInitial = user?.username?.charAt(0).toUpperCase() ?? 'U';

  // Close profile dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <header className="fixed top-0 left-0 right-0 z-[1300] bg-surface shadow-appbar">
      <div className="flex items-center h-16 px-4 gap-4">
        {/* Logo */}
        <div className="flex items-center gap-2 shrink-0">
          <WarehouseIcon className="text-primary" />
          <span className="text-xl font-bold text-text-primary whitespace-nowrap hidden sm:inline">
            WOMS
          </span>
        </div>

        {/* Hamburger toggle */}
        <button
          onClick={onToggleMenu}
          className="p-2 rounded-full hover:bg-black/5 cursor-pointer"
          aria-label="Toggle menu"
        >
          <MenuIcon />
        </button>

        {/* Search bar */}
        <div className="hidden md:flex items-center flex-grow max-w-md relative">
          <SearchIcon
            fontSize="small"
            className="absolute left-3 text-text-secondary"
          />
          <input
            type="text"
            placeholder="Search..."
            className="w-full pl-10 pr-4 py-2 rounded-full border border-divider bg-background text-sm text-text-primary outline-none focus:border-primary transition-colors"
            readOnly
          />
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* User profile dropdown */}
        <div className="relative" ref={profileRef}>
          <button
            onClick={() => setProfileOpen((prev) => !prev)}
            className="flex items-center gap-3 cursor-pointer rounded-default px-2 py-1.5 hover:bg-black/5 transition-colors"
          >
            {/* Avatar */}
            <div className="w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center text-sm font-semibold">
              {userInitial}
            </div>
            {/* Email + role (hidden on mobile) */}
            <div className="hidden md:flex flex-col items-start">
              <span className="text-sm text-text-primary font-medium leading-tight">
                {user?.email ?? 'user@example.com'}
              </span>
              <span className="text-xs text-primary bg-primary/10 px-2 py-0.5 rounded-full font-medium">
                {user?.role ?? 'User'}
              </span>
            </div>
            <KeyboardArrowDownIcon
              fontSize="small"
              className={`hidden md:block text-text-secondary transition-transform ${profileOpen ? 'rotate-180' : ''}`}
            />
          </button>

          {/* Dropdown menu */}
          {profileOpen && (
            <div className="absolute right-0 top-full mt-1 w-48 bg-surface rounded-default shadow-card border border-divider py-1 z-50">
              <button
                onClick={() => {
                  setProfileOpen(false);
                  onNavigate('/settings');
                }}
                className="flex items-center gap-2 w-full px-4 py-2.5 text-sm text-text-primary hover:bg-background cursor-pointer transition-colors"
              >
                <PersonIcon fontSize="small" />
                Edit Profile
              </button>
              <div className="border-t border-divider my-1" />
              <button
                onClick={() => {
                  setProfileOpen(false);
                  onLogout();
                }}
                className="flex items-center gap-2 w-full px-4 py-2.5 text-sm text-error hover:bg-error-bg cursor-pointer transition-colors"
              >
                <LogoutIcon fontSize="small" />
                Logout
              </button>
            </div>
          )}
        </div>

        {/* Notification bell (placeholder) */}
        <button
          className="p-2 rounded-full hover:bg-black/5 cursor-pointer relative"
          aria-label="Notifications"
        >
          <NotificationsNoneIcon className="text-text-secondary" />
        </button>
      </div>
    </header>
  );
}
