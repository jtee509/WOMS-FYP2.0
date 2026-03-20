import { useLocation, useNavigate } from 'react-router-dom';
import ConstructionIcon from '@mui/icons-material/Construction';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { NAV_CONFIG, isNavSection } from '../components/layout/nav.config';

function getPageTitle(pathname: string): { section: string; title: string } | null {
  for (const item of NAV_CONFIG) {
    if (isNavSection(item)) {
      for (const leaf of item.children) {
        if (pathname === leaf.path || pathname.startsWith(leaf.path + '/')) {
          return { section: item.title, title: leaf.title };
        }
      }
    }
  }
  return null;
}

export default function PlaceholderPage() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const page = getPageTitle(pathname);

  return (
    <div className="flex flex-col items-center justify-center py-20 gap-6">
      <div className="bg-surface rounded-card shadow-card px-10 py-14 flex flex-col items-center text-center gap-5 max-w-lg w-full">
        <div className="w-16 h-16 rounded-full bg-primary/8 flex items-center justify-center">
          <ConstructionIcon style={{ fontSize: 32 }} className="text-primary" />
        </div>

        {page && (
          <p className="text-xs font-semibold uppercase tracking-widest text-text-secondary">
            {page.section}
          </p>
        )}

        <h1 className="text-2xl font-semibold text-text-primary">
          {page?.title ?? 'Page Not Found'}
        </h1>

        <p className="text-sm text-text-secondary leading-relaxed max-w-xs">
          This module is under active development and will be available in a future release.
        </p>

        <div className="h-px w-full bg-divider" />

        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-sm text-primary hover:text-primary/80 cursor-pointer transition-colors"
        >
          <ArrowBackIcon fontSize="small" />
          Go back
        </button>
      </div>
    </div>
  );
}
