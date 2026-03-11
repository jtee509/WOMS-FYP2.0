import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import SaveIcon from '@mui/icons-material/Save';
import ImageIcon from '@mui/icons-material/Image';
import CloseIcon from '@mui/icons-material/Close';
import type { AttributeItem, ItemCreate } from '../../api/base_types/items';
import {
  getItem,
  createItem,
  updateItem,
  listItemTypes,
  listCategories,
  listBrands,
  listUOMs,
  uploadItemImage,
} from '../../api/base/items';
import VariationBuilder from './VariationBuilder';
import type { VariationsData } from './VariationBuilder.types';
import { migrateOldFormat } from './VariationBuilder.utils';

/* ------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------ */

interface FormValues extends Omit<ItemCreate, 'variations_data'> {}

interface DropdownOptions {
  itemTypes: AttributeItem[];
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

export default function ItemFormPage({ hideHeader = false }: { hideHeader?: boolean } = {}) {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = Boolean(id);

  const [options, setOptions] = useState<DropdownOptions>({
    itemTypes: [],
    categories: [],
    brands: [],
    uoms: [],
  });
  const [optionsLoading, setOptionsLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [itemLoading, setItemLoading] = useState(isEdit);
  const [variationsData, setVariationsData] = useState<VariationsData | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imageUploading, setImageUploading] = useState(false);
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
      is_active: true,
      has_variation: false,
    },
  });

  const hasVariation = watch('has_variation');
  const isActive = watch('is_active');

  // Load dropdown options
  useEffect(() => {
    const load = async () => {
      const [t, c, b, u] = await Promise.allSettled([
        listItemTypes(),
        listCategories(),
        listBrands(),
        listUOMs(),
      ]);
      setOptions({
        itemTypes: t.status === 'fulfilled' ? t.value : [],
        categories: c.status === 'fulfilled' ? c.value : [],
        brands: b.status === 'fulfilled' ? b.value : [],
        uoms: u.status === 'fulfilled' ? u.value : [],
      });
      setOptionsLoading(false);
    };
    load();
  }, []);

  // Load existing item in edit mode
  useEffect(() => {
    if (!isEdit || !id) return;
    const load = async () => {
      try {
        const item = await getItem(Number(id));
        reset({
          item_name: item.item_name,
          master_sku: item.master_sku,
          sku_name: item.sku_name ?? '',
          description: item.description ?? '',
          uom_id: item.uom_id ?? undefined,
          brand_id: item.brand_id ?? undefined,
          item_type_id: item.item_type_id ?? undefined,
          category_id: item.category_id ?? undefined,
          is_active: item.is_active,
          has_variation: item.has_variation,
        });
        setVariationsData(migrateOldFormat(item.variations_data));
        setImageUrl(item.image_url ?? null);
      } catch (err) {
        setSubmitError(extractErrorMessage(err));
      } finally {
        setItemLoading(false);
      }
    };
    load();
  }, [isEdit, id, reset]);

  const onSubmit = async (data: FormValues) => {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const payload: ItemCreate = {
        ...data,
        image_url: imageUrl ?? undefined,
        uom_id: data.uom_id ? Number(data.uom_id) : undefined,
        brand_id: data.brand_id ? Number(data.brand_id) : undefined,
        item_type_id: data.item_type_id ? Number(data.item_type_id) : undefined,
        category_id: data.category_id ? Number(data.category_id) : undefined,
        is_active: Boolean(data.is_active),
        variations_data: data.has_variation && variationsData
          ? (variationsData as unknown as Record<string, unknown>)
          : undefined,
      };

      if (isEdit && id) {
        await updateItem(Number(id), payload);
      } else {
        await createItem(payload);
      }
      navigate('/catalog/items');
    } catch (err) {
      setSubmitError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (itemLoading || optionsLoading) {
    return (
      <div className="flex justify-center py-16">
        <span className="inline-block w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

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
          <h1 className="text-2xl font-semibold text-text-primary">
            {isEdit ? 'Edit Item' : 'Create New Item'}
          </h1>
        </div>
      )}

      {/* Error */}
      {submitError && (
        <div className="mb-4 bg-error-bg text-error-text rounded-default px-4 py-3 text-sm">
          {submitError}
        </div>
      )}

      <form
        onSubmit={handleSubmit(onSubmit)}
      >
        <div className="bg-surface shadow-card p-6 rounded-card">
          {/* Product Image */}
          <div className="mb-6">
            <label className="form-label">Product Image</label>
            <div className="flex items-start gap-4">
              {/* Upload area / preview */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={imageUploading}
                className="relative w-32 h-32 border-2 border-dashed border-divider rounded-default flex items-center justify-center overflow-hidden hover:border-primary cursor-pointer transition-colors shrink-0"
              >
                {imageUrl ? (
                  <img
                    src={imageUrl}
                    alt="Product"
                    className="w-full h-full object-cover"
                  />
                ) : imageUploading ? (
                  <span className="inline-block w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                ) : (
                  <div className="flex flex-col items-center gap-1 text-text-secondary">
                    <ImageIcon />
                    <span className="text-xs">Upload</span>
                  </div>
                )}
              </button>

              {/* Helper text + remove */}
              <div className="flex flex-col gap-2 pt-1">
                <p className="text-xs text-text-secondary">
                  Click to upload product image.<br />
                  JPG, PNG, WebP or GIF (max 5 MB).
                </p>
                {imageUrl && (
                  <button
                    type="button"
                    onClick={() => setImageUrl(null)}
                    className="flex items-center gap-1 text-xs text-error hover:underline cursor-pointer w-fit"
                  >
                    <CloseIcon style={{ fontSize: 14 }} />
                    Remove image
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

          {/* Row 1: Item Name + Master SKU + SKU Name */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            <div>
              <label className="form-label">
                Item Name <span className="text-error">*</span>
              </label>
              <input
                {...register('item_name', {
                  required: 'Item name is required',
                  maxLength: { value: 500, message: 'Max 500 characters' },
                })}
                className={`form-input w-full ${errors.item_name ? 'form-input--error' : ''}`}
                placeholder="Item Name"
              />
              {errors.item_name && (
                <p className="form-helper text-error text-xs mt-1">{errors.item_name.message}</p>
              )}
            </div>
            <div>
              <label className="form-label">
                Master SKU <span className="text-error">*</span>
              </label>
              <input
                {...register('master_sku', {
                  required: 'Master SKU is required',
                  maxLength: { value: 100, message: 'Max 100 characters' },
                  validate: { noSpaces: (v) => !/\s/.test(v) || 'Master SKU must not contain spaces' },
                })}
                className={`form-input w-full ${errors.master_sku ? 'form-input--error' : ''}`}
                placeholder="Master SKU"
                readOnly={isEdit}
              />
              {errors.master_sku && (
                <p className="form-helper text-error text-xs mt-1">{errors.master_sku.message}</p>
              )}
              {isEdit && (
                <p className="text-xs text-text-secondary mt-1">SKU cannot be changed after creation</p>
              )}
            </div>
            <div>
              <label className="form-label">SKU Name</label>
              <input
                {...register('sku_name', {
                  maxLength: { value: 500, message: 'Max 500 characters' },
                })}
                className={`form-input w-full ${errors.sku_name ? 'form-input--error' : ''}`}
                placeholder="Display / variant label"
              />
              {errors.sku_name && (
                <p className="form-helper text-error text-xs mt-1">{errors.sku_name.message}</p>
              )}
            </div>
          </div>

          {/* Row 2: Description */}
          <div className="mt-5">
            <label className="form-label">Description</label>
            <textarea
              {...register('description')}
              className="form-input w-full min-h-[80px] resize-y"
              placeholder="Description"
              rows={3}
            />
          </div>

          {/* Row 3: Category + Brand */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mt-5">
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
          </div>

          {/* Row 4: Base UOM + Item Type (2 cols) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mt-5">
            <div>
              <label className="form-label">Base UOM</label>
              <select {...register('uom_id')} className="form-input w-full">
                <option value="">Select</option>
                {options.uoms.map((u) => (
                  <option key={u.id} value={u.id}>{u.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="form-label">Item Type</label>
              <select {...register('item_type_id')} className="form-input w-full">
                <option value="">Select</option>
                {options.itemTypes.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
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

          {/* Divider */}
          <hr className="border-divider my-6" />

          {/* Has Variation */}
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              {...register('has_variation')}
              className="w-4 h-4 rounded border-divider text-primary focus:ring-primary cursor-pointer"
            />
            <span className="text-sm font-medium text-text-primary">Has Variation</span>
          </label>

          {/* Variation Builder */}
          {hasVariation && (
            <VariationBuilder
              value={variationsData}
              onChange={setVariationsData}
            />
          )}
        </div>

        {/* Submit */}
        <div className="flex items-center gap-3 mt-6">
          <button
            type="submit"
            disabled={submitting}
            className="flex items-center gap-1.5 px-5 py-2.5 bg-secondary text-white rounded-default text-sm font-medium hover:bg-secondary-dark disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer shadow-button-hover"
          >
            <SaveIcon fontSize="small" />
            {submitting ? 'Saving...' : isEdit ? 'Update Item' : 'Save'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/catalog/items')}
            className="px-5 py-2.5 text-sm text-text-secondary hover:text-text-primary cursor-pointer border border-divider rounded-default"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
