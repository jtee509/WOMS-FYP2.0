import { useState } from 'react';
import AddIcon from '@mui/icons-material/Add';
import CloseIcon from '@mui/icons-material/Close';
import DeleteIcon from '@mui/icons-material/Delete';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import ImageIcon from '@mui/icons-material/Image';
import type {
  VariationAttribute,
  VariationCombination,
  VariationBuilderProps,
} from './VariationBuilder.types';
import { syncCombinations } from './VariationBuilder.utils';

const MAX_ATTR_NAME_LEN = 14;
const MAX_OPTION_LEN = 20;
const MAX_OPTIONS = 20;
const MAX_ATTRIBUTES = 5;

/* ------------------------------------------------------------------
 * VariationLevel — one variation dimension with 2-column option grid
 * ------------------------------------------------------------------ */

interface VariationLevelProps {
  levelIndex: number;
  attribute: VariationAttribute;
  onChangeName: (name: string) => void;
  onChangeValues: (values: string[]) => void;
  onRemove: () => void;
}

function VariationLevel({
  levelIndex,
  attribute,
  onChangeName,
  onChangeValues,
  onRemove,
}: VariationLevelProps) {
  const [draftOption, setDraftOption] = useState('');

  const commitOption = () => {
    const trimmed = draftOption.trim();
    if (!trimmed || attribute.values.length >= MAX_OPTIONS) return;
    onChangeValues([...attribute.values, trimmed]);
    setDraftOption('');
  };

  const removeOption = (idx: number) => {
    onChangeValues(attribute.values.filter((_, i) => i !== idx));
  };

  const updateOption = (idx: number, val: string) => {
    const next = [...attribute.values];
    next[idx] = val;
    onChangeValues(next);
  };

  const canAddMore = attribute.values.length < MAX_OPTIONS;

  return (
    <div className="border border-divider rounded-default p-4">
      {/* Variation name row */}
      <div className="flex items-center gap-3 mb-4">
        <span className="text-sm font-semibold text-text-primary whitespace-nowrap shrink-0">
          Variation {levelIndex + 1}
        </span>

        {/* Name input with inline character counter */}
        <div className="relative flex-1">
          <input
            type="text"
            value={attribute.name}
            onChange={(e) => onChangeName(e.target.value.slice(0, MAX_ATTR_NAME_LEN))}
            className="form-input w-full !pr-12"
            placeholder={levelIndex === 0 ? 'e.g. Colour' : 'e.g. Size'}
            maxLength={MAX_ATTR_NAME_LEN}
          />
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-text-secondary pointer-events-none">
            {attribute.name.length}/{MAX_ATTR_NAME_LEN}
          </span>
        </div>

        <button
          type="button"
          onClick={onRemove}
          className="p-1 text-text-secondary hover:text-error cursor-pointer shrink-0"
          title="Remove variation"
        >
          <DeleteIcon fontSize="small" />
        </button>
      </div>

      {/* Options list */}
      <div>
        <span className="form-label text-xs">Options</span>
        <div className="flex flex-col gap-2">
          {/* Committed option inputs */}
          {attribute.values.map((val, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <DragIndicatorIcon
                className="text-text-secondary/50 cursor-grab shrink-0"
                style={{ fontSize: 18 }}
              />
              <div className="relative flex-1 min-w-0">
                <input
                  type="text"
                  value={val}
                  onChange={(e) =>
                    updateOption(idx, e.target.value.slice(0, MAX_OPTION_LEN))
                  }
                  className="form-input w-full !py-1.5 !pr-14 text-sm"
                  maxLength={MAX_OPTION_LEN}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-text-secondary pointer-events-none">
                  {val.length}/{MAX_OPTION_LEN}
                </span>
              </div>
              <button
                type="button"
                onClick={() => removeOption(idx)}
                className="p-0.5 text-text-secondary hover:text-error cursor-pointer shrink-0"
                title="Remove option"
              >
                <CloseIcon style={{ fontSize: 16 }} />
              </button>
            </div>
          ))}

          {/* Draft "Input" slot — full-width, aligned with committed rows */}
          {canAddMore && (
            <div className="flex items-center gap-2">
              <span className="shrink-0" style={{ width: 18 }} />
              <div className="relative flex-1 min-w-0">
                <input
                  type="text"
                  value={draftOption}
                  onChange={(e) =>
                    setDraftOption(e.target.value.slice(0, MAX_OPTION_LEN))
                  }
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      commitOption();
                    }
                  }}
                  onBlur={commitOption}
                  className="form-input w-full !py-1.5 !pr-14 text-sm"
                  placeholder="Input"
                  maxLength={MAX_OPTION_LEN}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-text-secondary pointer-events-none">
                  {draftOption.length}/{MAX_OPTION_LEN}
                </span>
              </div>
              <span className="shrink-0" style={{ width: 20 }} />
            </div>
          )}
        </div>

        {/* Hints */}
        {attribute.values.length === 0 && !draftOption && (
          <p className="text-xs text-text-secondary mt-2">
            Type an option and press Enter to add (max {MAX_OPTIONS})
          </p>
        )}
        {attribute.values.length >= MAX_OPTIONS && (
          <p className="text-xs text-warning mt-2">
            Maximum {MAX_OPTIONS} options reached
          </p>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------
 * CombinationTable — Image + variation values + SKU only (no price/stock)
 * ------------------------------------------------------------------ */

interface CombinationTableProps {
  attributes: VariationAttribute[];
  combinations: VariationCombination[];
  onCombinationsChange: (combos: VariationCombination[]) => void;
}

function CombinationTable({
  attributes,
  combinations,
  onCombinationsChange,
}: CombinationTableProps) {
  const [batchSku, setBatchSku] = useState('');

  if (combinations.length === 0) return null;

  const attrNames = attributes.map((a) => a.name || 'Variation');

  const handleBatchApply = () => {
    if (batchSku === '') return;
    onCombinationsChange(combinations.map((c) => ({ ...c, sku: batchSku })));
    setBatchSku('');
  };

  const updateCombo = (idx: number, sku: string) => {
    const updated = [...combinations];
    updated[idx] = { ...updated[idx], sku };
    onCombinationsChange(updated);
  };

  return (
    <div className="mt-5 border border-divider rounded-default overflow-hidden">
      <div className="overflow-x-auto w-full">
        <table className="w-full text-sm">
          {/* Header */}
          <thead className="border-b border-divider bg-background">
            <tr>
              <th className="px-3 py-2.5 text-left font-semibold text-text-secondary whitespace-nowrap">
                Image
              </th>
              {attrNames.map((name, i) => (
                <th
                  key={i}
                  className="px-3 py-2.5 text-left font-semibold text-text-secondary whitespace-nowrap"
                >
                  {name}
                </th>
              ))}
              <th className="px-3 py-2.5 text-left font-semibold text-text-secondary min-w-[180px]">
                SKU
              </th>
            </tr>
          </thead>

          <tbody className="divide-y divide-divider">
            {/* Batch apply row */}
            <tr className="bg-background/50">
              <td className="px-3 py-2" />
              {attrNames.map((_, i) => (
                <td key={i} className="px-3 py-2">
                  {i === 0 && (
                    <span className="text-xs font-medium text-text-secondary">
                      Batch Apply:
                    </span>
                  )}
                </td>
              ))}
              <td className="px-3 py-2">
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={batchSku}
                    onChange={(e) => setBatchSku(e.target.value)}
                    className="form-input !py-1.5 !px-2 !w-full min-w-0 flex-1 text-sm"
                    placeholder="SKU"
                  />
                  <button
                    type="button"
                    onClick={handleBatchApply}
                    className="px-3 py-1.5 bg-primary text-white text-xs font-medium rounded-default hover:bg-primary-dark cursor-pointer whitespace-nowrap shrink-0"
                  >
                    Apply
                  </button>
                </div>
              </td>
            </tr>

            {/* Combination rows */}
            {combinations.map((combo, idx) => (
              <tr
                key={JSON.stringify(combo.values)}
                className="hover:bg-background/30 transition-colors"
              >
                {/* Image placeholder */}
                <td className="px-3 py-2">
                  <button
                    type="button"
                    className="w-11 h-11 border border-dashed border-divider rounded-default flex items-center justify-center text-text-secondary hover:border-primary hover:text-primary cursor-pointer transition-colors"
                    title="Image upload coming soon"
                  >
                    <ImageIcon style={{ fontSize: 18 }} />
                  </button>
                </td>
                {/* Variation values */}
                {combo.values.map((val, i) => (
                  <td key={i} className="px-3 py-2 text-text-primary whitespace-nowrap">
                    {val}
                  </td>
                ))}
                {/* SKU */}
                <td className="px-3 py-2">
                  <input
                    type="text"
                    value={combo.sku}
                    onChange={(e) => updateCombo(idx, e.target.value)}
                    className="form-input !py-1.5 !px-2 !w-full text-sm"
                    placeholder="SKU"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="px-3 py-2 border-t border-divider bg-background/30 text-xs text-text-secondary">
        {combinations.length} variation{combinations.length !== 1 ? 's' : ''} total
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------
 * VariationBuilder — main orchestrator (default export)
 * ------------------------------------------------------------------ */

export default function VariationBuilder({
  value,
  onChange,
}: VariationBuilderProps) {
  const attributes = value?.attributes ?? [];
  const combinations = value?.combinations ?? [];

  const hasNonEmptyValues = attributes.some(
    (a) => a.values.filter((v) => v.trim()).length > 0,
  );

  /* ---- Handlers ---- */

  const emitChange = (
    newAttrs: VariationAttribute[],
    existingCombos: VariationCombination[],
  ) => {
    if (newAttrs.length === 0) {
      onChange(null);
      return;
    }
    const newCombos = syncCombinations(newAttrs, existingCombos);
    onChange({ attributes: newAttrs, combinations: newCombos });
  };

  const handleAddAttribute = () => {
    if (attributes.length >= MAX_ATTRIBUTES) return;
    const newAttrs = [...attributes, { name: '', values: [] }];
    emitChange(newAttrs, combinations);
  };

  const handleRemoveAttribute = (idx: number) => {
    const newAttrs = attributes.filter((_, i) => i !== idx);
    emitChange(newAttrs, combinations);
  };

  const handleNameChange = (idx: number, name: string) => {
    const newAttrs = [...attributes];
    newAttrs[idx] = { ...newAttrs[idx], name };
    // Name change doesn't affect combination keys (only values matter)
    onChange({ attributes: newAttrs, combinations });
  };

  const handleValuesChange = (idx: number, values: string[]) => {
    const newAttrs = [...attributes];
    newAttrs[idx] = { ...newAttrs[idx], values };
    emitChange(newAttrs, combinations);
  };

  const handleCombinationsChange = (combos: VariationCombination[]) => {
    onChange({ attributes, combinations: combos });
  };

  /* ---- Render ---- */

  return (
    <div className="mt-4 space-y-4">
      {/* Section header */}
      <p className="text-sm font-semibold text-text-primary flex items-center gap-1.5">
        <span className="text-primary">•</span> Variations
      </p>

      {/* Variation levels */}
      {attributes.map((attr, idx) => (
        <VariationLevel
          key={idx}
          levelIndex={idx}
          attribute={attr}
          onChangeName={(name) => handleNameChange(idx, name)}
          onChangeValues={(vals) => handleValuesChange(idx, vals)}
          onRemove={() => handleRemoveAttribute(idx)}
        />
      ))}

      {/* Add Variation button */}
      {attributes.length < MAX_ATTRIBUTES && (
        <button
          type="button"
          onClick={handleAddAttribute}
          className="flex items-center gap-1 text-sm text-primary hover:underline cursor-pointer"
        >
          <AddIcon fontSize="small" />
          {attributes.length === 0 ? 'Add Variation' : 'Add Variation 2'}
        </button>
      )}

      {/* Combination table — only shown when at least one option exists */}
      {hasNonEmptyValues && (
        <CombinationTable
          attributes={attributes}
          combinations={combinations}
          onCombinationsChange={handleCombinationsChange}
        />
      )}
    </div>
  );
}
