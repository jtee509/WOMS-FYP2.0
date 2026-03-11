/** A single variation dimension (e.g. "Colour" with ["Yellow", "Dark Grey"]) */
export interface VariationAttribute {
  name: string;
  values: string[];
}

/** One row in the combination table */
export interface VariationCombination {
  /** Ordered values matching attributes order, e.g. ["Yellow", "S"] */
  values: string[];
  sku: string;
  /** URL or null — placeholder for future image upload */
  image: string | null;
}

/**
 * The full JSONB shape stored in items.variations_data.
 * This is both the component's value type AND the API payload shape.
 */
export interface VariationsData {
  attributes: VariationAttribute[];
  combinations: VariationCombination[];
}

/** Props for the controlled VariationBuilder component */
export interface VariationBuilderProps {
  value: VariationsData | null;
  onChange: (data: VariationsData | null) => void;
}
