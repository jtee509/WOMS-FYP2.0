import type { PreviewLocation } from './BulkCreationWizard';

interface Props {
  locations: PreviewLocation[];
}

export default function PreviewTable({ locations }: Props) {
  if (locations.length === 0) {
    return (
      <div>
        <h4 className="text-sm font-semibold text-text-primary mb-3 uppercase tracking-wide">
          Preview
        </h4>
        <p className="text-xs text-text-secondary">
          Configure ranges above and click <strong>Preview</strong> to see generated locations.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-text-primary uppercase tracking-wide">
          Preview
        </h4>
        <span className="text-xs text-text-secondary">
          {locations.length.toLocaleString()} location{locations.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="border border-divider rounded-default overflow-auto max-h-56">
        <table className="w-full text-xs whitespace-nowrap">
          <thead>
            <tr className="bg-background border-b border-divider">
              <th className="px-3 py-2 text-left font-semibold text-text-secondary">#</th>
              <th className="px-3 py-2 text-left font-semibold text-text-secondary">Section</th>
              <th className="px-3 py-2 text-left font-semibold text-text-secondary">Zone</th>
              <th className="px-3 py-2 text-left font-semibold text-text-secondary">Aisle</th>
              <th className="px-3 py-2 text-left font-semibold text-text-secondary">Rack</th>
              <th className="px-3 py-2 text-left font-semibold text-text-secondary">Bin</th>
            </tr>
          </thead>
          <tbody>
            {locations.slice(0, 100).map((loc, i) => (
              <tr key={i} className="border-b border-divider last:border-0">
                <td className="px-3 py-1.5 text-text-secondary">{i + 1}</td>
                <td className="px-3 py-1.5">{loc.section ?? <span className="text-text-secondary">—</span>}</td>
                <td className="px-3 py-1.5">{loc.zone    ?? <span className="text-text-secondary">—</span>}</td>
                <td className="px-3 py-1.5">{loc.aisle   ?? <span className="text-text-secondary">—</span>}</td>
                <td className="px-3 py-1.5">{loc.rack    ?? <span className="text-text-secondary">—</span>}</td>
                <td className="px-3 py-1.5">{loc.bin     ?? <span className="text-text-secondary">—</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {locations.length > 100 && (
          <p className="px-3 py-2 text-xs text-text-secondary text-center border-t border-divider">
            Showing first 100 of {locations.length.toLocaleString()} locations
          </p>
        )}
      </div>
    </div>
  );
}
