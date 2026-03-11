import type { ReactNode } from 'react';
import DashboardIcon from '@mui/icons-material/Dashboard';
import BarChartIcon from '@mui/icons-material/BarChart';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import Inventory2Icon from '@mui/icons-material/Inventory2';
import ListAltIcon from '@mui/icons-material/ListAlt';
import AddBoxIcon from '@mui/icons-material/AddBox';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import TranslateIcon from '@mui/icons-material/Translate';
import HistoryIcon from '@mui/icons-material/History';
import InventoryIcon from '@mui/icons-material/Inventory';
import WarehouseIcon from '@mui/icons-material/Warehouse';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz';
import FactCheckIcon from '@mui/icons-material/FactCheck';
import ElectricBoltIcon from '@mui/icons-material/ElectricBolt';
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart';
import DescriptionIcon from '@mui/icons-material/Description';
import LocalShippingIcon from '@mui/icons-material/LocalShipping';
import CancelIcon from '@mui/icons-material/Cancel';
import ReplayIcon from '@mui/icons-material/Replay';
import AirportShuttleIcon from '@mui/icons-material/AirportShuttle';
import GroupWorkIcon from '@mui/icons-material/GroupWork';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import DirectionsCarIcon from '@mui/icons-material/DirectionsCar';
import StoreIcon from '@mui/icons-material/Store';
import PersonIcon from '@mui/icons-material/Person';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import AddShoppingCartIcon from '@mui/icons-material/AddShoppingCart';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import SettingsIcon from '@mui/icons-material/Settings';
import PeopleIcon from '@mui/icons-material/People';
import ManageAccountsIcon from '@mui/icons-material/ManageAccounts';
import AssignmentIcon from '@mui/icons-material/Assignment';

/* ------------------------------------------------------------------
 * Type definitions
 * ------------------------------------------------------------------ */

export interface NavLeaf {
  kind: 'leaf';
  title: string;
  path: string;
  icon: ReactNode;
  /** Optional override for active detection. Defaults to exact match or prefix match. */
  isActive?: (pathname: string) => boolean;
}

export interface NavSection {
  kind: 'section';
  title: string;
  icon: ReactNode;
  children: NavLeaf[];
}

export type NavItem = NavLeaf | NavSection;

/* ------------------------------------------------------------------
 * Type guards
 * ------------------------------------------------------------------ */

export function isNavSection(item: NavItem): item is NavSection {
  return item.kind === 'section';
}

/* ------------------------------------------------------------------
 * Active-state helpers
 * ------------------------------------------------------------------ */

export function leafIsActive(leaf: NavLeaf, pathname: string): boolean {
  if (leaf.isActive) return leaf.isActive(pathname);
  return pathname === leaf.path || pathname.startsWith(leaf.path + '/');
}

export function sectionHasActiveChild(section: NavSection, pathname: string): boolean {
  return section.children.some((leaf) => leafIsActive(leaf, pathname));
}

/* ------------------------------------------------------------------
 * Navigation config
 * ------------------------------------------------------------------ */

export const NAV_CONFIG: NavItem[] = [
  /* ---- Dashboard ---- */
  {
    kind: 'section',
    title: 'Dashboard',
    icon: <DashboardIcon />,
    children: [
      {
        kind: 'leaf',
        title: 'Performance Metrics',
        path: '/dashboard/metrics',
        icon: <BarChartIcon />,
        isActive: (p) => p === '/' || p === '/dashboard' || p.startsWith('/dashboard/metrics'),
      },
      {
        kind: 'leaf',
        title: 'System Alerts',
        path: '/dashboard/alerts',
        icon: <NotificationsActiveIcon />,
      },
    ],
  },

  /* ---- Catalog ---- */
  {
    kind: 'section',
    title: 'Catalog',
    icon: <Inventory2Icon />,
    children: [
      {
        kind: 'leaf',
        title: 'My Items',
        path: '/catalog/items',
        icon: <ListAltIcon />,
        // Active on list + edit (items & bundles) but NOT on /new or /upload
        isActive: (p) =>
          p === '/catalog/items' ||
          p === '/catalog/bundles' ||
          (p.startsWith('/catalog/items/') &&
            !p.startsWith('/catalog/items/new') &&
            !p.startsWith('/catalog/items/upload')) ||
          (p.startsWith('/catalog/bundles/') &&
            !p.startsWith('/catalog/bundles/new')),
      },
      {
        kind: 'leaf',
        title: 'Create New',
        path: '/catalog/items/new',
        icon: <AddBoxIcon />,
        isActive: (p) =>
          p === '/catalog/items/new' || p === '/catalog/bundles/new',
      },
      {
        kind: 'leaf',
        title: 'Mass Upload / Import',
        path: '/catalog/items/upload',
        icon: <UploadFileIcon />,
      },
      {
        kind: 'leaf',
        title: 'Translation',
        path: '/catalog/translation',
        icon: <TranslateIcon />,
      },
      {
        kind: 'leaf',
        title: 'Item History',
        path: '/catalog/history',
        icon: <HistoryIcon />,
      },
    ],
  },

  /* ---- Inventory ---- */
  {
    kind: 'section',
    title: 'Inventory',
    icon: <InventoryIcon />,
    children: [
      {
        kind: 'leaf',
        title: 'Stock Level',
        path: '/inventory/levels',
        icon: <WarehouseIcon />,
      },
      {
        kind: 'leaf',
        title: 'Movements',
        path: '/inventory/movements',
        icon: <SwapHorizIcon />,
      },
      {
        kind: 'leaf',
        title: 'Stock Check',
        path: '/inventory/stock-check',
        icon: <FactCheckIcon />,
      },
      {
        kind: 'leaf',
        title: 'Triggers',
        path: '/inventory/triggers',
        icon: <ElectricBoltIcon />,
      },
    ],
  },

  /* ---- Orders ---- */
  {
    kind: 'section',
    title: 'Orders',
    icon: <ShoppingCartIcon />,
    children: [
      {
        kind: 'leaf',
        title: 'Order Details',
        path: '/orders/details',
        icon: <DescriptionIcon />,
      },
      {
        kind: 'leaf',
        title: 'Mass Ship',
        path: '/orders/mass-ship',
        icon: <LocalShippingIcon />,
      },
      {
        kind: 'leaf',
        title: 'Cancellation',
        path: '/orders/cancellation',
        icon: <CancelIcon />,
      },
      {
        kind: 'leaf',
        title: 'Returns & Exchanges',
        path: '/orders/returns',
        icon: <ReplayIcon />,
      },
    ],
  },

  /* ---- Shipments ---- */
  {
    kind: 'section',
    title: 'Shipments',
    icon: <AirportShuttleIcon />,
    children: [
      {
        kind: 'leaf',
        title: 'Management',
        path: '/shipments/management',
        icon: <LocalShippingIcon />,
      },
      {
        kind: 'leaf',
        title: 'Group Order',
        path: '/shipments/group',
        icon: <GroupWorkIcon />,
      },
      {
        kind: 'leaf',
        title: 'Scheduling',
        path: '/shipments/schedule',
        icon: <CalendarMonthIcon />,
      },
      {
        kind: 'leaf',
        title: 'Fleet Management',
        path: '/shipments/fleet',
        icon: <DirectionsCarIcon />,
      },
    ],
  },

  /* ---- Seller Management ---- */
  {
    kind: 'section',
    title: 'Seller Management',
    icon: <StoreIcon />,
    children: [
      {
        kind: 'leaf',
        title: 'Seller Profiles',
        path: '/sellers/profiles',
        icon: <PersonIcon />,
      },
      {
        kind: 'leaf',
        title: 'Import Staging',
        path: '/sellers/import',
        icon: <CloudUploadIcon />,
      },
      {
        kind: 'leaf',
        title: 'Create New Order',
        path: '/sellers/new-order',
        icon: <AddShoppingCartIcon />,
      },
      {
        kind: 'leaf',
        title: 'Warehouse Allocation',
        path: '/sellers/allocation',
        icon: <AccountTreeIcon />,
      },
    ],
  },

  /* ---- Warehouse ---- */
  {
    kind: 'section',
    title: 'Warehouse',
    icon: <WarehouseIcon />,
    children: [
      {
        kind: 'leaf',
        title: 'Location Setup',
        path: '/warehouse/locations',
        icon: <AccountTreeIcon />,
        isActive: (p) => p === '/warehouse' || p === '/warehouse/locations',
      },
      {
        kind: 'leaf',
        title: 'Pattern Generator',
        path: '/warehouse/locations/generator',
        icon: <AutoFixHighIcon />,
      },
    ],
  },

  /* ---- Settings ---- */
  {
    kind: 'section',
    title: 'Settings',
    icon: <SettingsIcon />,
    children: [
      {
        kind: 'leaf',
        title: 'Master Settings',
        path: '/settings',
        icon: <SettingsIcon />,
        isActive: (p) =>
          p === '/settings' ||
          p.startsWith('/settings/items') ||
          p.startsWith('/settings/warehouse') ||
          p.startsWith('/settings/platforms'),
      },
      {
        kind: 'leaf',
        title: 'Users & Roles',
        path: '/settings/users',
        icon: <PeopleIcon />,
      },
      {
        kind: 'leaf',
        title: 'Audit Logs',
        path: '/settings/audit',
        icon: <AssignmentIcon />,
      },
      {
        kind: 'leaf',
        title: 'Platform Configurations',
        path: '/settings/platforms',
        icon: <ManageAccountsIcon />,
      },
    ],
  },

];
