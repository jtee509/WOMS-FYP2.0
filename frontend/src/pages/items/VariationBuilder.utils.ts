import type {
  VariationAttribute,
  VariationCombination,
  VariationsData,
} from './VariationBuilder.types';

/**
 * Generate the cartesian product of all value arrays.
 * Example: [["Red","Blue"], ["S","M"]] => [["Red","S"],["Red","M"],["Blue","S"],["Blue","M"]]
 */
export function cartesianProduct(arrays: string[][]): string[][] {
  const filtered = arrays.filter((a) => a.length > 0);
  if (filtered.length === 0) return [];
  return filtered.reduce<string[][]>(
    (acc, curr) => acc.flatMap((combo) => curr.map((val) => [...combo, val])),
    [[]],
  );
}

/**
 * Regenerate combinations from current attributes, preserving
 * user-entered data (sku, price, stock, image) for matching value tuples.
 */
export function syncCombinations(
  attributes: VariationAttribute[],
  existingCombinations: VariationCombination[],
): VariationCombination[] {
  const existing = new Map<string, VariationCombination>();
  for (const combo of existingCombinations) {
    existing.set(JSON.stringify(combo.values), combo);
  }

  const valueSets = attributes.map((a) =>
    a.values.filter((v) => v.trim() !== ''),
  );
  const product = cartesianProduct(valueSets);

  return product.map((values) => {
    const key = JSON.stringify(values);
    const prev = existing.get(key);
    if (prev) return { ...prev, values };
    return { values, sku: '', image: null };
  });
}

/**
 * Convert old-format variations_data (attributes-only) to the new format
 * (attributes + combinations). If already new format, return as-is.
 */
export function migrateOldFormat(
  data: Record<string, unknown> | null | undefined,
): VariationsData | null {
  if (!data || typeof data !== 'object') return null;

  const attrs = data.attributes;
  if (!Array.isArray(attrs) || attrs.length === 0) return null;

  const attributes: VariationAttribute[] = attrs.map(
    (a: { name?: string; values?: string[] }) => ({
      name: a.name ?? '',
      values: Array.isArray(a.values) ? a.values : [],
    }),
  );

  if (Array.isArray(data.combinations) && data.combinations.length > 0) {
    const combinations: VariationCombination[] = (
      data.combinations as Array<Record<string, unknown>>
    ).map((c) => ({
      values: Array.isArray(c.values) ? (c.values as string[]) : [],
      sku: typeof c.sku === 'string' ? c.sku : '',
      image: typeof c.image === 'string' ? c.image : null,
    }));
    return { attributes, combinations };
  }

  return {
    attributes,
    combinations: syncCombinations(attributes, []),
  };
}
