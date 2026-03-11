import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import LayersIcon from '@mui/icons-material/Layers';
import ItemsMassUploadPage from './ItemsMassUploadPage';
import BundlesMassUploadPage from './BundlesMassUploadPage';

type Tab = 'items' | 'bundles';

const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
  { key: 'items', label: 'Items', icon: <UploadFileIcon style={{ fontSize: 16 }} /> },
  { key: 'bundles', label: 'Bundles', icon: <LayersIcon style={{ fontSize: 16 }} /> },
];

export default function CatalogUploadPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>('items');

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
        <h1 className="text-2xl font-semibold text-text-primary">Mass Upload / Import</h1>
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

      {/* Content */}
      {tab === 'items' ? (
        <ItemsMassUploadPage hideHeader />
      ) : (
        <BundlesMassUploadPage hideHeader />
      )}
    </div>
  );
}
