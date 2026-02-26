import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Sidebar, Menu, MenuItem } from 'react-pro-sidebar';
import Box from '@mui/material/Box';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useTheme } from '@mui/material/styles';
import MenuIcon from '@mui/icons-material/Menu';
import DashboardIcon from '@mui/icons-material/Dashboard';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import StorageIcon from '@mui/icons-material/Storage';
import SyncIcon from '@mui/icons-material/Sync';

const NAV_ITEMS = [
  { label: 'Dashboard', path: '/', icon: <DashboardIcon /> },
  { label: 'Order Import', path: '/orders/import', icon: <UploadFileIcon /> },
  { label: 'Reference Data', path: '/reference', icon: <StorageIcon /> },
  { label: 'ML Staging', path: '/ml', icon: <SyncIcon /> },
];

const SIDEBAR_WIDTH = 260;
const SIDEBAR_COLLAPSED_WIDTH = 80;

export default function MainLayout() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
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
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <Sidebar
        collapsed={collapsed}
        toggled={toggled}
        onBackdropClick={() => setToggled(false)}
        breakPoint="md"
        backgroundColor={theme.palette.background.paper}
        rootStyles={{
          borderRight: `1px solid ${theme.palette.divider}`,
          height: '100vh',
          position: 'fixed',
          top: 0,
          left: 0,
          zIndex: theme.zIndex.drawer,
        }}
        width={`${SIDEBAR_WIDTH}px`}
        collapsedWidth={`${SIDEBAR_COLLAPSED_WIDTH}px`}
      >
        {/* Sidebar header */}
        <Box
          sx={{
            p: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            borderBottom: `1px solid ${theme.palette.divider}`,
            minHeight: 64,
          }}
        >
          <Typography
            variant="h6"
            sx={{
              fontWeight: 700,
              color: theme.palette.primary.main,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
            }}
          >
            {collapsed ? 'W' : 'WOMS'}
          </Typography>
        </Box>

        {/* Navigation menu */}
        <Menu
          menuItemStyles={{
            button: ({ active }) => ({
              backgroundColor: active
                ? theme.palette.primary.main + '14'
                : 'transparent',
              color: active
                ? theme.palette.primary.main
                : theme.palette.text.primary,
              fontWeight: active ? 600 : 400,
              '&:hover': {
                backgroundColor: theme.palette.primary.main + '0A',
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
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          ml: isMobile ? 0 : `${sidebarWidth}px`,
          transition: 'margin-left 0.3s',
          display: 'flex',
          flexDirection: 'column',
          minHeight: '100vh',
        }}
      >
        {/* Top bar */}
        <AppBar
          position="sticky"
          color="inherit"
          sx={{
            backgroundColor: theme.palette.background.paper,
          }}
        >
          <Toolbar>
            <IconButton edge="start" onClick={handleToggle} sx={{ mr: 2 }}>
              <MenuIcon />
            </IconButton>
            <Typography variant="h6" noWrap sx={{ flexGrow: 1 }}>
              Warehouse Order Management System
            </Typography>
          </Toolbar>
        </AppBar>

        {/* Page content */}
        <Box sx={{ p: 3, flexGrow: 1 }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}
