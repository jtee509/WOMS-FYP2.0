import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Menu, MenuItem, SubMenu } from 'react-pro-sidebar';
import {
  NAV_CONFIG,
  isNavSection,
  leafIsActive,
  sectionHasActiveChild,
} from './nav.config';

/* ------------------------------------------------------------------
 * Shared menuItemStyles — mirrors the existing active-state styling
 * ------------------------------------------------------------------ */

const menuItemStyles = {
  button: ({ active }: { active: boolean }) => ({
    backgroundColor: active ? 'var(--color-sidebar-active-bg)' : 'transparent',
    color: active ? 'var(--color-primary)' : 'var(--color-text-secondary)',
    fontWeight: active ? 600 : 400,
    borderLeft: active
      ? '3px solid var(--color-primary)'
      : '3px solid transparent',
    borderRadius: 0,
    '&:hover': {
      backgroundColor: 'color-mix(in srgb, var(--color-primary) 4%, transparent)',
      color: 'var(--color-primary)',
    },
  }),
};

/* ------------------------------------------------------------------
 * Props
 * ------------------------------------------------------------------ */

interface SidebarNavProps {
  collapsed: boolean;
  onNavigate: (path: string) => void;
}

/* ------------------------------------------------------------------
 * Component
 * ------------------------------------------------------------------ */

export default function SidebarNav({ collapsed, onNavigate }: SidebarNavProps) {
  const location = useLocation();
  const pathname = location.pathname;

  // Track which sections are open. Initialise based on current URL so the
  // correct section is already open when the user first lands on a page.
  const [openSections, setOpenSections] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    for (const item of NAV_CONFIG) {
      if (isNavSection(item)) {
        initial[item.title] = sectionHasActiveChild(item, pathname);
      }
    }
    return initial;
  });

  // When the route changes, ensure the active section auto-opens
  // (handles navigation via address bar or programmatic pushes).
  useEffect(() => {
    setOpenSections((prev) => {
      const next = { ...prev };
      for (const item of NAV_CONFIG) {
        if (isNavSection(item) && sectionHasActiveChild(item, pathname)) {
          next[item.title] = true;
        }
      }
      return next;
    });
  }, [pathname]);

  const toggleSection = (title: string) => {
    setOpenSections((prev) => ({ ...prev, [title]: !prev[title] }));
  };

  return (
    <Menu menuItemStyles={menuItemStyles}>
      {NAV_CONFIG.map((item) => {
        if (!isNavSection(item)) {
          /* Standalone leaf (none in current config, but supported) */
          return (
            <MenuItem
              key={item.path}
              icon={item.icon}
              active={leafIsActive(item, pathname)}
              onClick={() => onNavigate(item.path)}
            >
              {item.title}
            </MenuItem>
          );
        }

        /* Section with children */
        return (
          <SubMenu
            key={item.title}
            label={item.title}
            icon={item.icon}
            open={!collapsed && openSections[item.title]}
            onOpenChange={() => toggleSection(item.title)}
          >
            {item.children.map((leaf) => (
              <MenuItem
                key={leaf.path}
                icon={leaf.icon}
                active={leafIsActive(leaf, pathname)}
                onClick={() => onNavigate(leaf.path)}
              >
                {leaf.title}
              </MenuItem>
            ))}
          </SubMenu>
        );
      })}
    </Menu>
  );
}
