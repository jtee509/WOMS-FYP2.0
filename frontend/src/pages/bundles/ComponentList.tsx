import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import AddIcon from '@mui/icons-material/Add';
import RemoveIcon from '@mui/icons-material/Remove';

export interface ComponentRow {
  item_id: number;
  item_name: string;
  master_sku: string;
  image_url: string | null;
  quantity: number;
}

interface Props {
  components: ComponentRow[];
  onChange: (updated: ComponentRow[]) => void;
}

export default function ComponentList({ components, onChange }: Props) {
  const updateQty = (idx: number, delta: number) => {
    const next = [...components];
    next[idx] = { ...next[idx], quantity: Math.max(1, next[idx].quantity + delta) };
    onChange(next);
  };

  const setQty = (idx: number, value: number) => {
    const next = [...components];
    next[idx] = { ...next[idx], quantity: Math.max(1, value) };
    onChange(next);
  };

  const remove = (idx: number) => {
    onChange(components.filter((_, i) => i !== idx));
  };

  if (components.length === 0) {
    return (
      <div className="border-2 border-dashed border-divider rounded-default py-10 text-center">
        <p className="text-sm text-text-secondary">
          No components added yet. Use the search above to add items to this bundle.
        </p>
      </div>
    );
  }

  const totalItems = components.reduce((sum, c) => sum + c.quantity, 0);

  return (
    <div>
      {/* Table */}
      <div className="border border-divider rounded-default overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-background text-text-secondary text-xs uppercase tracking-wider">
              <th className="text-left px-4 py-2.5 font-medium w-12">#</th>
              <th className="text-left px-4 py-2.5 font-medium">Item</th>
              <th className="text-left px-4 py-2.5 font-medium w-28">SKU</th>
              <th className="text-center px-4 py-2.5 font-medium w-40">Quantity</th>
              <th className="text-center px-4 py-2.5 font-medium w-16"></th>
            </tr>
          </thead>
          <tbody>
            {components.map((comp, idx) => (
              <tr
                key={comp.item_id}
                className="border-t border-divider hover:bg-background/50 transition-colors"
              >
                {/* Row number */}
                <td className="px-4 py-3 text-text-secondary">{idx + 1}</td>

                {/* Item name + thumbnail */}
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded bg-background flex items-center justify-center shrink-0 overflow-hidden">
                      {comp.image_url ? (
                        <img src={comp.image_url} alt="" className="w-full h-full object-cover" />
                      ) : (
                        <span className="text-[10px] text-text-secondary font-medium">IMG</span>
                      )}
                    </div>
                    <span className="font-medium text-text-primary truncate max-w-[240px]">
                      {comp.item_name}
                    </span>
                  </div>
                </td>

                {/* SKU */}
                <td className="px-4 py-3 text-text-secondary font-mono text-xs">
                  {comp.master_sku}
                </td>

                {/* Quantity stepper */}
                <td className="px-4 py-3">
                  <div className="flex items-center justify-center gap-1">
                    <button
                      type="button"
                      onClick={() => updateQty(idx, -1)}
                      disabled={comp.quantity <= 1}
                      className="w-7 h-7 flex items-center justify-center rounded border border-divider hover:bg-background disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer transition-colors"
                    >
                      <RemoveIcon style={{ fontSize: 16 }} />
                    </button>
                    <input
                      type="number"
                      min={1}
                      value={comp.quantity}
                      onChange={(e) => setQty(idx, parseInt(e.target.value, 10) || 1)}
                      className="w-14 h-7 text-center border border-divider rounded text-sm font-medium focus:border-primary focus:outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
                    />
                    <button
                      type="button"
                      onClick={() => updateQty(idx, 1)}
                      className="w-7 h-7 flex items-center justify-center rounded border border-divider hover:bg-background cursor-pointer transition-colors"
                    >
                      <AddIcon style={{ fontSize: 16 }} />
                    </button>
                  </div>
                </td>

                {/* Delete */}
                <td className="px-4 py-3 text-center">
                  <button
                    type="button"
                    onClick={() => remove(idx)}
                    className="p-1 rounded hover:bg-error-bg text-text-secondary hover:text-error cursor-pointer transition-colors"
                    title="Remove component"
                  >
                    <DeleteOutlineIcon style={{ fontSize: 18 }} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Summary bar */}
      <div className="mt-3 flex items-center justify-between px-1">
        <p className="text-xs text-text-secondary">
          {components.length} component{components.length !== 1 ? 's' : ''}
        </p>
        <p className="text-sm font-medium text-text-primary">
          Total items in bundle: <span className="text-primary">{totalItems}</span>
        </p>
      </div>
    </div>
  );
}
