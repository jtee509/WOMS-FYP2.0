import { useState, useEffect } from 'react';
import SearchBar from '../../components/common/SearchBar';
import type { AttributeItem } from '../../api/base_types/items';
import { listCategories, listBrands } from '../../api/base/items';

interface BundleFiltersProps {
  search: string;
  onSearchChange: (value: string) => void;
  categoryId: number | undefined;
  brandId: number | undefined;
  onCategoryChange: (id: number | undefined) => void;
  onBrandChange: (id: number | undefined) => void;
}

export default function BundleFilters({
  search,
  onSearchChange,
  categoryId,
  brandId,
  onCategoryChange,
  onBrandChange,
}: BundleFiltersProps) {
  const [categories, setCategories] = useState<AttributeItem[]>([]);
  const [brands, setBrands] = useState<AttributeItem[]>([]);

  useEffect(() => {
    const load = async () => {
      const [c, b] = await Promise.allSettled([
        listCategories(),
        listBrands(),
      ]);
      if (c.status === 'fulfilled') setCategories(c.value);
      if (b.status === 'fulfilled') setBrands(b.value);
    };
    load();
  }, []);

  return (
    <div className="flex flex-wrap items-center gap-3 px-6 py-4 border-b border-divider">
      {/* Search — left */}
      <SearchBar
        value={search}
        onChange={onSearchChange}
        placeholder="Search Bundle Name, SKU..."
        className="w-120"
      />

      {/* Category + Brand — pushed to right */}
      <div className="flex flex-wrap items-center gap-3 ml-auto">
        {/* Category */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-text-secondary whitespace-nowrap">Category :</span>
          <select
            value={categoryId ?? ''}
            onChange={(e) => onCategoryChange(e.target.value ? Number(e.target.value) : undefined)}
            className="form-input !w-auto !py-1.5 text-sm min-w-[130px]"
          >
            <option value="">Select</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>

        {/* Brand */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-text-secondary whitespace-nowrap">Brand :</span>
          <select
            value={brandId ?? ''}
            onChange={(e) => onBrandChange(e.target.value ? Number(e.target.value) : undefined)}
            className="form-input !w-auto !py-1.5 text-sm min-w-[130px]"
          >
            <option value="">Select</option>
            {brands.map((b) => (
              <option key={b.id} value={b.id}>{b.name}</option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
