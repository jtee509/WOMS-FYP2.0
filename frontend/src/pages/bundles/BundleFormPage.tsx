import { useState, useEffect, useRef, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import SaveIcon from '@mui/icons-material/Save';
import ImageIcon from '@mui/icons-material/Image';
import CloseIcon from '@mui/icons-material/Close';
import LayersIcon from '@mui/icons-material/Layers';
import type { AttributeItem, ItemRead, BundleComponentRead } from '../../api/base_types/items';
import {
  getItem,
  getBundle,
  createBundle,
  updateBundle,
  listCategories,
  listBrands,
  listUOMs,
  listItemTypes,
  uploadItemImage,
} from '../../api/base/items';
import ComponentSearch from './ComponentSearch';
import ComponentList from './ComponentList';
import type { ComponentRow } from './ComponentList';

/* ------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------ */

interface FormValues {
  item_name: string;
  master_sku: string;
  sku_name: string;
  description: string;
  category_id: number | '';
  brand_id: number | '';
  uom_id: number | '';
  is_active: boolean;
}

interface DropdownOptions {
  categories: AttributeItem[];
  brands: AttributeItem[];
  uoms: AttributeItem[];
}

/* ------------------------------------------------------------------
 * Helpers
 * ------------------------------------------------------------------ */

function extractErrorMessage(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const e = err as { response?: { data?: { detail?: string } } };
    return e.response?.data?.detail ?? 'Operation failed.';
  }
  return 'Operation failed.';
}

/* ------------------------------------------------------------------
 * Component
 * ------------------------------------------------------------------ */

export default function BundleFormPage({ hideHeader = false }: { hideHeader?: boolean } = {}) {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = Boolean(id);

  /* ----- State ----- */
  const [options, setOptions] = useState<DropdownOptions>({
    categories: [], brands: [], uoms: [],
  });
  const [bundleTypeId, setBundleTypeId] = useState<number | null>(null);
  const [optionsLoading, setOptionsLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [itemLoading, setItemLoading] = useState(isEdit);
  const [components, setComponents] = useState<ComponentRow[]>([]);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageUploading, setImageUploading] = useState(false);
  const [existingListingId, setExistingListingId] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    defaultValues: {
      item_name: '',
      master_sku: '',
      sku_name: '',
      description: '',
      category_id: '',
      brand_id: '',
      uom_id: '',
      is_active: true,
    },
  });

  const isActive = watch('is_active');

  // Exclude IDs already in the component list
  const excludeIds = useMemo(
    () => new Set(components.map((c) => c.item_id)),
    [components],
  );

  /* ----- Load dropdown options ----- */
  useEffect(() => {
    const load = async () => {
      const [cat, brand, uom, types] = await Promise.allSettled([
        listCategories(),
        listBrands(),
        listUOMs(),
        listItemTypes(),
      ]);
      setOptions({
        categories: cat.status === 'fulfilled' ? cat.value : [],
        brands: brand.status === 'fulfilled' ? brand.value : [],
        uoms: uom.status === 'fulfilled' ? uom.value : [],
      });
      // Resolve "Bundle" type ID
      if (types.status === 'fulfilled') {
        const bt = types.value.find((t) => t.name === 'Bundle');
        if (bt) setBundleTypeId(bt.id);
      }
      setOptionsLoading(false);
    };
    load();
  }, []);

  /* ----- Load existing bundle in edit mode ----- */
  useEffect(() => {
    if (!isEdit || !id) return;
    const load = async () => {
      try {
        // Fetch bundle item — the PATCH response has components but
        // the GET /items/:id doesn't, so we need a workaround.
        // First fetch the item data, then call PATCH with empty body
        // to get the full BundleReadResponse.
        const item = await getItem(Number(id));
        reset({
          item_name: item.item_name,
          master_sku: item.master_sku,
          sku_name: item.sku_name ?? '',
          description: item.description ?? '',
          category_id: item.category_id ?? '',
          brand_id: item.brand_id ?? '',
          uom_id: item.uom_id ?? '',
          is_active: item.is_active,
        });
        setImageUrl(item.image_url ?? null);

        // Fetch bundle with components via the dedicated GET endpoint
        const bundleResp = await getBundle(Number(id));
        setExistingListingId(bundleResp.listing_id);
        setComponents(
          bundleResp.components.map((c: BundleComponentRead) => ({
            item_id: c.item_id,
            item_name: c.item_name,
            master_sku: c.master_sku,
            image_url: null,
            quantity: c.quantity,
          })),
        );
      } catch (err) {
        setSubmitError(extractErrorMessage(err));
      } finally {
        setItemLoading(false);
      }
    };
    load();
  }, [isEdit, id, reset]);

  /* ----- Add component from search ----- */
  const handleAddComponent = (item: ItemRead) => {
    setComponents((prev) => [
      ...prev,
      {
        item_id: item.item_id,
        item_name: item.item_name,
        master_sku: item.master_sku,
        image_url: item.image_url,
        quantity: 1,
      },
    ]);
  };

  /* ----- Validate bundle composition ----- */
  const validateComponents = (): string | null => {
    if (components.length === 0) return 'Add at least one component item to the bundle.';
    const distinctIds = new Set(components.map((c) => c.item_id));
    const maxQty = Math.max(...components.map((c) => c.quantity));
    if (distinctIds.size <= 1 && maxQty <= 1) {
      return 'A bundle must have more than one distinct item, or a single item with quantity > 1.';
    }
    return null;
  };

  /* ----- Submit ----- */
  const onSubmit = async (data: FormValues) => {
    const compError = validateComponents();
    if (compError) {
      setSubmitError(compError);
      return;
    }

    setSubmitting(true);
    setSubmitError(null);

    try {
      const componentPayload = components.map((c) => ({
        item_id: c.item_id,
        quantity: c.quantity,
      }));

      if (isEdit && id) {
        await updateBundle(Number(id), {
          item_name: data.item_name,
          master_sku: data.master_sku,
          sku_name: data.sku_name || undefined,
          description: data.description || undefined,
          image_url: imageUrl ?? undefined,
          category_id: data.category_id ? Number(data.category_id) : undefined,
          brand_id: data.brand_id ? Number(data.brand_id) : undefined,
          uom_id: data.uom_id ? Number(data.uom_id) : undefined,
          is_active: data.is_active,
          components: componentPayload,
        });
      } else {
        await createBundle({
          item_name: data.item_name,
          master_sku: data.master_sku,
          sku_name: data.sku_name || undefined,
          description: data.description || undefined,
          image_url: imageUrl ?? undefined,
          category_id: data.category_id ? Number(data.category_id) : undefined,
          brand_id: data.brand_id ? Number(data.brand_id) : undefined,
          uom_id: data.uom_id ? Number(data.uom_id) : undefined,
          is_active: data.is_active,
          components: componentPayload,
        });
      }
      navigate('/catalog/bundles');
    } catch (err) {
      setSubmitError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  /* ----- Loading state ----- */
  if (itemLoading || optionsLoading) {
    return (
      <div className="flex justify-center py-16">
        <span className="inline-block w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  const totalItems = components.reduce((sum, c) => sum + c.quantity, 0);

  return (
    <div>
      {/* Header */}
      {!hideHeader && (
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => navigate('/catalog/items')}
            className="p-1.5 rounded-default hover:bg-background text-text-secondary cursor-pointer"
          >
            <ArrowBackIcon fontSize="small" />
          </button>
          <LayersIcon className="text-primary" />
          <h1 className="text-2xl font-semibold text-text-primary">
            {isEdit ? 'Edit Bundle' : 'Create New Bundle'}
          </h1>
        </div>
      )}

      {/* Error */}
      {submitError && (
        <div className="mb-4 bg-error-bg text-error-text rounded-default px-4 py-3 text-sm">
          {submitError}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)}>
        {/* ---- Section 1: Bundle Details ---- */}
        <div className="bg-surface shadow-card p-6 rounded-card">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Bundle Details</h2>

          {/* Product Image */}
          <div className="mb-5">
            <label className="form-label">Bundle Image</label>
            <div className="flex items-start gap-4">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={imageUploading}
                className="relative w-28 h-28 border-2 border-dashed border-divider rounded-default flex items-center justify-center overflow-hidden hover:border-primary cursor-pointer transition-colors shrink-0"
              >
                {imageUrl ? (
                  <img src={imageUrl} alt="Bundle" className="w-full h-full object-cover" />
                ) : imageUploading ? (
                  <span className="inline-block w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                ) : (
                  <div className="flex flex-col items-center gap-1 text-text-secondary">
                    <ImageIcon />
                    <span className="text-xs">Upload</span>
                  </div>
                )}
              </button>
              <div className="flex flex-col gap-2 pt-1">
                <p className="text-xs text-text-secondary">
                  JPG, PNG, WebP or GIF (max 5 MB).
                </p>
                {imageUrl && (
                  <button
                    type="button"
                    onClick={() => setImageUrl(null)}
                    className="flex items-center gap-1 text-xs text-error hover:underline cursor-pointer w-fit"
                  >
                    <CloseIcon style={{ fontSize: 14 }} />
                    Remove
                  </button>
                )}
              </div>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              className="hidden"
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                setImageUploading(true);
                setSubmitError(null);
                try {
                  const result = await uploadItemImage(file);
                  setImageUrl(result.url);
                } catch (err) {
                  setSubmitError(extractErrorMessage(err));
                } finally {
                  setImageUploading(false);
                  e.target.value = '';
                }
              }}
            />
          </div>

          {/* Row 1: Bundle Name + Bundle SKU + SKU Name */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            <div>
              <label className="form-label">
                Bundle Name <span className="text-error">*</span>
              </label>
              <input
                {...register('item_name', {
                  required: 'Bundle name is required',
                  maxLength: { value: 500, message: 'Max 500 characters' },
                })}
                className={`form-input w-full ${errors.item_name ? 'form-input--error' : ''}`}
                placeholder="e.g. Summer Essentials Pack"
              />
              {errors.item_name && (
                <p className="form-helper text-error text-xs mt-1">{errors.item_name.message}</p>
              )}
            </div>
            <div>
              <label className="form-label">
                Bundle SKU <span className="text-error">*</span>
              </label>
              <input
                {...register('master_sku', {
                  required: 'Bundle SKU is required',
                  maxLength: { value: 100, message: 'Max 100 characters' },
                  validate: { noSpaces: (v) => !/\s/.test(v) || 'SKU must not contain spaces' },
                })}
                className={`form-input w-full ${errors.master_sku ? 'form-input--error' : ''}`}
                placeholder="e.g. BUNDLE-SUMMER-001"
              />
              {errors.master_sku && (
                <p className="form-helper text-error text-xs mt-1">{errors.master_sku.message}</p>
              )}
            </div>
            <div>
              <label className="form-label">SKU Display Name</label>
              <input
                {...register('sku_name', {
                  maxLength: { value: 500, message: 'Max 500 characters' },
                })}
                className="form-input w-full"
                placeholder="Optional display label"
              />
            </div>
          </div>

          {/* Row 2: Description */}
          <div className="mt-5">
            <label className="form-label">Description</label>
            <textarea
              {...register('description')}
              className="form-input w-full min-h-[80px] resize-y"
              placeholder="Describe this bundle..."
              rows={3}
            />
          </div>

          {/* Row 3: Category + Brand + UOM */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mt-5">
            <div>
              <label className="form-label">Category</label>
              <select {...register('category_id')} className="form-input w-full">
                <option value="">Select</option>
                {options.categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="form-label">Brand</label>
              <select {...register('brand_id')} className="form-input w-full">
                <option value="">Select</option>
                {options.brands.map((b) => (
                  <option key={b.id} value={b.id}>{b.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="form-label">Base UOM</label>
              <select {...register('uom_id')} className="form-input w-full">
                <option value="">Select</option>
                {options.uoms.map((u) => (
                  <option key={u.id} value={u.id}>{u.name}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Status toggle */}
          <div className="mt-5">
            <label className="form-label">Status</label>
            <div className="flex items-center gap-3">
              <button
                type="button"
                role="switch"
                aria-checked={Boolean(isActive)}
                onClick={() => setValue('is_active', !isActive, { shouldDirty: true })}
                className={`relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full transition-colors focus:outline-none cursor-pointer ${
                  isActive ? 'bg-primary' : 'bg-divider'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                    isActive ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
              <span className={`text-sm font-medium ${isActive ? 'text-success-text' : 'text-text-secondary'}`}>
                {isActive ? 'Active' : 'Inactive'}
              </span>
            </div>
          </div>
        </div>

        {/* ---- Section 2: Bundle Components ---- */}
        <div className="bg-surface shadow-card rounded-card mt-6">
          {/* Header row with search */}
          <div className="flex flex-wrap items-center gap-3 px-6 py-4 border-b border-divider">
            <ComponentSearch
              excludeIds={excludeIds}
              onSelect={handleAddComponent}
              excludeItemTypeId={bundleTypeId ?? undefined}
              className="w-80"
            />
            <div className="flex items-center gap-3 ml-auto">
              {components.length > 0 && (
                <span className="text-xs bg-primary/10 text-primary px-2.5 py-1 rounded-full font-medium">
                  {components.length} item{components.length !== 1 ? 's' : ''} / {totalItems} total qty
                </span>
              )}
            </div>
          </div>

          {/* Component Table */}
          <div className="p-6">
            <ComponentList components={components} onChange={setComponents} />
          </div>
        </div>

        {/* ---- Submit Bar ---- */}
        <div className="flex items-center gap-3 mt-6">
          <button
            type="submit"
            disabled={submitting}
            className="flex items-center gap-1.5 px-5 py-2.5 bg-secondary text-white rounded-default text-sm font-medium hover:bg-secondary-dark disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer shadow-button-hover"
          >
            <SaveIcon fontSize="small" />
            {submitting ? 'Saving...' : isEdit ? 'Update Bundle' : 'Create Bundle'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/catalog/bundles')}
            className="px-5 py-2.5 text-sm text-text-secondary hover:text-text-primary cursor-pointer border border-divider rounded-default"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
