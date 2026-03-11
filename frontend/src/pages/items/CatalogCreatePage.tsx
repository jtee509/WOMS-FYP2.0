import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ImageIcon from '@mui/icons-material/Image';
import LayersIcon from '@mui/icons-material/Layers';
import ItemFormPage from './ItemFormPage';
import BundleFormPage from '../bundles/BundleFormPage';

type Tab = 'item' | 'bundle';

const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
  { key: 'item', label: 'Item', icon: <ImageIcon style={{ fontSize: 16 }} /> },
  { key: 'bundle', label: 'Bundle', icon: <LayersIcon style={{ fontSize: 16 }} /> },
];

export default function CatalogCreatePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialTab = searchParams.get('type') === 'bundle' ? 'bundle' : 'item';
  const [tab, setTab] = useState<Tab>(initialTab as Tab);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <button
          onClick={() => navigate('/catalog/items')}
          className="p-1.5 rounded-default hover:bg-background text-text-secondary cursor-pointer"
        >
          <ArrowBackIcon fontSize="small" />
        </button>
        <h1 className="text-2xl font-semibold text-text-primary">Create New</h1>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 mb-6 bg-background rounded-lg p-1 w-fit">
        {TABS.map(({ key, label, icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium transition-all cursor-pointer ${
              tab === key
                ? 'bg-surface text-text-primary shadow-sm'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {icon}
            {label}
          </button>
        ))}
      </div>

      {/* Form content */}
      {tab === 'item' ? (
        <ItemFormPage hideHeader />
      ) : (
        <BundleFormPage hideHeader />
      )}
    </div>
  );
}
