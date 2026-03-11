/**
 * BulkCreationWizard — Pattern Generator sidebar
 *
 * UX v2 enhancements
 * ──────────────────
 * • Section selection: pick existing section OR type a new one
 * • Auto-preview: onPreview called via useEffect on every level change
 *   (no manual "Full Preview" button — preview tree updates live)
 * • Compact collapsible level cards — sidebar fits viewport, no scroll
 * • Review & Confirm step before actual save (unchanged)
 */

import { useState, useMemo, useCallback, useEffect } from 'react';
import { Save, AlertTriangle, ChevronRight, RotateCcw, ChevronDown, Plus } from 'lucide-react';
import type { BulkGenerateRequest, SegmentRangeInput } from '../../../api/base_types/warehouse';

/* ------------------------------------------------------------------
 * PreviewLocation
 * ------------------------------------------------------------------ */

export interface PreviewLocation {
  section?: string;
  zone?:    string;
  aisle?:   string;
  rack?:    string;
  bin?:     string;
}

/* ------------------------------------------------------------------
 * Hierarchy levels
 * ------------------------------------------------------------------ */

type Level = 'section' | 'zone' | 'aisle' | 'rack' | 'bin';
const LEVELS: Level[] = ['section', 'zone', 'aisle', 'rack', 'bin'];
const LEVEL_LABELS: Record<Level, string> = {
  section: 'Section',
  zone:    'Zone',
  aisle:   'Aisle',
  rack:    'Rack',
  bin:     'Bin',
};

/* ------------------------------------------------------------------
 * LevelState
 * ------------------------------------------------------------------ */

interface LevelState {
  enabled:  boolean;
  prefix:   string;
  useRange: boolean;
  start:    string;
  end:      string;
  pad:      string;
  values:   string;
}

function emptyLevel(defaultEnabled = false): LevelState {
  return { enabled: defaultEnabled, prefix: '', useRange: true, start: '1', end: '5', pad: '0', values: '' };
}

/* ------------------------------------------------------------------
 * Helpers
 * ------------------------------------------------------------------ */

function toSegmentRange(s: LevelState): SegmentRangeInput {
  if (s.useRange) {
    return {
      prefix: s.prefix,
      start:  s.start !== '' ? Number(s.start) : null,
      end:    s.end   !== '' ? Number(s.end)   : null,
      pad:    s.pad   !== '' ? Number(s.pad)   : 0,
      values: null,
    };
  }
  return {
    prefix: s.prefix,
    start:  null,
    end:    null,
    pad:    0,
    values: s.values.split(',').map(v => v.trim()).filter(Boolean),
  };
}

function generateValues(s: LevelState): string[] {
  if (!s.enabled) return [];
  if (s.useRange) {
    const start = parseInt(s.start, 10);
    const end   = parseInt(s.end,   10);
    const pad   = parseInt(s.pad,   10) || 0;
    if (isNaN(start) || isNaN(end) || start > end) return [];
    const out: string[] = [];
    for (let i = start; i <= end; i++) {
      out.push(s.prefix + (pad > 0 ? String(i).padStart(pad, '0') : String(i)));
    }
    return out;
  }
  return s.values.split(',').map(v => v.trim()).filter(Boolean).map(v => s.prefix + v);
}

/**
 * Build up to maxSamples cartesian combos + exact total count.
 * fixedSection overrides the section level config.
 */
function buildPreviewSample(
  levels: Record<Level, LevelState>,
  fixedSection: string,
  maxSamples = 200,
): { samples: PreviewLocation[]; total: number } {
  const levelValues: Array<{ level: Level; vals: string[] }> = [];

  if (fixedSection) {
    levelValues.push({ level: 'section', vals: [fixedSection] });
    for (const lvl of LEVELS.filter(l => l !== 'section')) {
      const s = levels[lvl];
      if (!s.enabled) continue;
      const vals = generateValues(s);
      if (vals.length > 0) levelValues.push({ level: lvl, vals });
    }
  } else {
    for (const lvl of LEVELS) {
      const s = levels[lvl];
      if (!s.enabled) continue;
      const vals = generateValues(s);
      if (vals.length > 0) levelValues.push({ level: lvl, vals });
    }
  }

  if (levelValues.length === 0) return { samples: [], total: 0 };

  const total = levelValues.reduce((acc, { vals }) => acc * vals.length, 1);

  let combos: PreviewLocation[] = [{}];
  for (const { level, vals } of levelValues) {
    const next: PreviewLocation[] = [];
    outer: for (const combo of combos) {
      for (const v of vals) {
        next.push({ ...combo, [level]: v });
        if (next.length >= maxSamples) break outer;
      }
    }
    combos = next;
  }

  return { samples: combos.slice(0, maxSamples), total };
}

export function locationCode(loc: PreviewLocation): string {
  return [loc.section, loc.zone, loc.aisle, loc.rack, loc.bin].filter(Boolean).join('.');
}

/* ------------------------------------------------------------------
 * Props
 * ------------------------------------------------------------------ */

interface Props {
  existingSections?: string[];
  onPreview:       (locations: PreviewLocation[], total: number) => void;
  onSectionSelect?: (section: string) => void;
  onSave:           (request: BulkGenerateRequest) => void;
  saving:           boolean;
}

/* ------------------------------------------------------------------
 * Component
 * ------------------------------------------------------------------ */

type WizardStep = 'form' | 'review';

export default function BulkCreationWizard({ existingSections = [], onPreview, onSectionSelect, onSave, saving }: Props) {

  /* ── Section mode ──────────────────────────────────────────────── */
  const [sectionMode,    setSectionMode]    = useState<'existing' | 'new'>('new');
  const [existingSec,    setExistingSec]    = useState('');
  const [newSectionName, setNewSectionName] = useState('');
  const [secSearch,      setSecSearch]      = useState('');
  const [secDropOpen,    setSecDropOpen]    = useState(false);

  /* ── Level states ──────────────────────────────────────────────── */
  const [levels, setLevels] = useState<Record<Level, LevelState>>({
    section: emptyLevel(),
    zone:    emptyLevel(),
    aisle:   emptyLevel(),
    rack:    emptyLevel(),
    bin:     emptyLevel(true),
  });

  const [step,          setStep]          = useState<WizardStep>('form');
  const [reviewRequest, setReviewRequest] = useState<BulkGenerateRequest | null>(null);

  const setLevel = useCallback((lvl: Level, patch: Partial<LevelState>) => {
    setLevels(prev => ({ ...prev, [lvl]: { ...prev[lvl], ...patch } }));
  }, []);

  /* Resolved fixed section (existing pick or new typed name) */
  const fixedSection = sectionMode === 'existing' ? existingSec : newSectionName.trim();

  const anyEnabled = sectionMode === 'existing'
    ? (!!existingSec && LEVELS.filter(l => l !== 'section').some(l => levels[l].enabled))
    : (fixedSection
        ? LEVELS.filter(l => l !== 'section').some(l => levels[l].enabled)
        : LEVELS.some(l => levels[l].enabled));

  /* ── Auto-preview — reactive on every change ───────────────────── */
  const { samples: liveSamples, total: liveTotal } = useMemo(
    () => buildPreviewSample(levels, fixedSection, 200),
    [levels, fixedSection],
  );

  useEffect(() => {
    onPreview(liveSamples, liveTotal);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [liveSamples, liveTotal]);

  /* Also fire when section mode / name changes */
  useEffect(() => {
    const { samples, total } = buildPreviewSample(levels, fixedSection, 200);
    onPreview(samples, total);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sectionMode, existingSec, newSectionName]);

  /* Notify parent which existing section is selected */
  useEffect(() => {
    if (!onSectionSelect) return;
    onSectionSelect(sectionMode === 'existing' ? existingSec : '');
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sectionMode, existingSec]);

  /* Filtered existing sections */
  const filteredSections = useMemo(() => {
    const q = secSearch.toLowerCase();
    return existingSections.filter(s => s.toLowerCase().includes(q));
  }, [existingSections, secSearch]);

  /* ── Build API request ─────────────────────────────────────────── */
  const buildRequest = useCallback((): BulkGenerateRequest => {
    const req: BulkGenerateRequest = {};
    if (sectionMode === 'existing' && existingSec) {
      req.section = { prefix: '', start: null, end: null, pad: 0, values: [existingSec] };
    } else if (sectionMode === 'new' && newSectionName.trim()) {
      req.section = { prefix: '', start: null, end: null, pad: 0, values: [newSectionName.trim()] };
    } else if (sectionMode === 'new' && levels.section.enabled) {
      req.section = toSegmentRange(levels.section);
    }
    for (const lvl of LEVELS.filter(l => l !== 'section')) {
      if (levels[lvl].enabled) req[lvl] = toSegmentRange(levels[lvl]);
    }
    return req;
  }, [levels, sectionMode, existingSec, newSectionName]);

  /* ── Review step ───────────────────────────────────────────────── */
  if (step === 'review') {
    const sampleCodes = liveSamples.slice(0, 5).map(locationCode);
    return (
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-1.5 text-[10px] text-text-secondary">
          <span>Pattern Generator</span>
          <ChevronRight size={11} className="text-divider" />
          <span className="font-semibold text-primary">Review & Confirm</span>
        </div>

        <div className="border border-primary/20 rounded-default bg-primary/5 p-3 flex flex-col gap-3">
          <div className="flex items-start gap-2">
            <AlertTriangle size={14} className="text-warning-text flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-semibold text-text-primary">
                Create {liveTotal.toLocaleString()} location{liveTotal !== 1 ? 's' : ''}?
              </p>
              <p className="text-[11px] text-text-secondary mt-0.5">
                Existing codes are skipped — no duplicates.
              </p>
            </div>
          </div>

          {sampleCodes.length > 0 && (
            <div>
              <p className="text-[10px] text-text-secondary uppercase tracking-wide font-semibold mb-1.5">Sample codes</p>
              <div className="flex flex-wrap gap-1">
                {sampleCodes.map((code, i) => (
                  <code key={i} className="bg-white border border-divider text-primary font-mono text-[11px] px-1.5 py-0.5 rounded">
                    {code}
                  </code>
                ))}
                {liveTotal > 5 && (
                  <span className="text-[11px] text-text-secondary self-center">+{(liveTotal - 5).toLocaleString()} more</span>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button onClick={() => setStep('form')}
            className="flex items-center gap-1.5 px-3 py-1.5 border border-divider rounded-default text-xs text-text-secondary hover:bg-background transition-colors cursor-pointer">
            <RotateCcw size={11} /> Back
          </button>
          <button
            onClick={() => { if (reviewRequest) { onSave(reviewRequest); setStep('form'); } }}
            disabled={saving}
            className="flex-grow flex items-center justify-center gap-1.5 py-1.5 bg-secondary text-white rounded-default text-xs font-semibold hover:shadow-button-hover disabled:opacity-50 cursor-pointer">
            <Save size={11} />
            {saving ? 'Creating…' : `Confirm — ${liveTotal.toLocaleString()}`}
          </button>
        </div>
      </div>
    );
  }

  /* ────────────────────────────────────────────────────────────────
   * Form step
   * ──────────────────────────────────────────────────────────────── */
  return (
    <div className="flex flex-col gap-3">

      {/* ── Section ───────────────────────────────────────────────── */}
      <div>
        <p className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider mb-2">Section</p>

        {/* Mode toggle */}
        <div className="flex items-center border border-divider rounded-default overflow-hidden mb-2 text-[11px]">
          {(['existing', 'new'] as const).map(m => (
            <button
              key={m}
              onClick={() => { setSectionMode(m); if (m === 'new') setExistingSec(''); }}
              className={`flex-1 py-1.5 font-medium transition-colors cursor-pointer capitalize ${
                sectionMode === m ? 'bg-primary text-white' : 'text-text-secondary hover:bg-background'
              }`}
            >
              {m === 'existing' ? 'Existing' : 'New'}
            </button>
          ))}
        </div>

        {sectionMode === 'existing' ? (
          existingSections.length === 0 ? (
            <p className="text-[11px] text-text-secondary italic">No sections found — switch to "New".</p>
          ) : (
            <div className="relative">
              <button
                onClick={() => setSecDropOpen(v => !v)}
                className="w-full flex items-center justify-between px-2.5 py-1.5 border border-divider rounded-default bg-white text-[11px] hover:border-primary/40 transition-colors cursor-pointer"
              >
                <span className={existingSec ? 'text-text-primary font-medium' : 'text-text-secondary'}>
                  {existingSec || 'Select a section…'}
                </span>
                <ChevronDown size={11} className={`text-text-secondary transition-transform ${secDropOpen ? 'rotate-180' : ''}`} />
              </button>

              {secDropOpen && (
                <div className="absolute top-full left-0 right-0 mt-0.5 border border-divider rounded-default bg-white shadow-card z-30 overflow-hidden">
                  <div className="p-1.5 border-b border-divider">
                    <input
                      type="text"
                      value={secSearch}
                      onChange={e => setSecSearch(e.target.value)}
                      placeholder="Search…"
                      className="form-input w-full text-[11px] py-0.5"
                      autoFocus
                    />
                  </div>
                  <div className="max-h-36 overflow-y-auto">
                    {filteredSections.map(sec => (
                      <button
                        key={sec}
                        onClick={() => { setExistingSec(sec); setSecDropOpen(false); setSecSearch(''); }}
                        className={`w-full text-left px-2.5 py-1.5 text-[11px] hover:bg-background cursor-pointer transition-colors ${
                          sec === existingSec ? 'text-primary font-semibold bg-primary/5' : 'text-text-primary'
                        }`}
                      >
                        {sec}
                      </button>
                    ))}
                    {filteredSections.length === 0 && (
                      <p className="px-2.5 py-2 text-[11px] text-text-secondary">No match.</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          )
        ) : (
          /* New section input */
          <div className="flex items-center gap-1.5">
            <Plus size={12} className="text-text-secondary flex-shrink-0" />
            <input
              type="text"
              value={newSectionName}
              onChange={e => setNewSectionName(e.target.value)}
              placeholder="e.g. Sector01"
              className="form-input flex-grow text-[11px] py-1"
              maxLength={50}
            />
          </div>
        )}
      </div>

      <div className="border-t border-divider" />

      {/* ── Sub-levels (Zone, Aisle, Rack, Bin) ────────────────────── */}
      <div className="flex flex-col gap-1.5">
        {LEVELS.filter(lvl => lvl !== 'section').map(lvl => (
          <LevelCard
            key={lvl}
            label={LEVEL_LABELS[lvl]}
            state={levels[lvl]}
            onChange={patch => setLevel(lvl, patch)}
          />
        ))}

        {/* Section as level — only for "new" mode with no typed name */}
        {sectionMode === 'new' && !newSectionName.trim() && (
          <LevelCard
            label="Section (range)"
            state={levels.section}
            onChange={patch => setLevel('section', patch)}
          />
        )}
      </div>

      <div className="border-t border-divider" />

      {/* ── Total + actions ─────────────────────────────────────────── */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-text-secondary">
            {liveTotal > 0
              ? <><span className="font-semibold text-primary">{liveTotal.toLocaleString()}</span> locations</>
              : <span className="text-text-secondary/60">Configure levels above</span>}
          </span>
          <button onClick={() => {
            setLevels({ section: emptyLevel(), zone: emptyLevel(), aisle: emptyLevel(), rack: emptyLevel(), bin: emptyLevel(true) });
            setSectionMode('new'); setExistingSec(''); setNewSectionName('');
          }} className="text-[10px] text-text-secondary hover:text-text-primary hover:underline cursor-pointer flex items-center gap-0.5">
            <RotateCcw size={10} /> Reset
          </button>
        </div>

        <button
          onClick={() => { if (!anyEnabled || liveTotal === 0) return; setReviewRequest(buildRequest()); setStep('review'); }}
          disabled={!anyEnabled || liveTotal === 0}
          className="w-full flex items-center justify-center gap-1.5 py-2 bg-secondary text-white rounded-default text-xs font-semibold hover:shadow-button-hover transition-shadow disabled:opacity-40 cursor-pointer"
        >
          <Save size={12} />
          Create {liveTotal > 0 ? `(${liveTotal.toLocaleString()})` : 'Locations'}
        </button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------
 * LevelCard — compact collapsible level configurator
 * ------------------------------------------------------------------ */

interface LevelCardProps {
  label:    string;
  state:    LevelState;
  onChange: (patch: Partial<LevelState>) => void;
}

function LevelCard({ label, state: s, onChange }: LevelCardProps) {
  return (
    <div className={`rounded-default border transition-all ${
      s.enabled ? 'border-divider/80 bg-background/50' : 'border-transparent'
    }`}>
      {/* Toggle row */}
      <label className="flex items-center gap-2 cursor-pointer select-none px-2 py-1.5">
        <input
          type="checkbox"
          checked={s.enabled}
          onChange={e => onChange({ enabled: e.target.checked })}
          className="w-3.5 h-3.5 rounded border-divider text-primary focus:ring-primary cursor-pointer"
        />
        <span className={`text-xs font-semibold ${s.enabled ? 'text-text-primary' : 'text-text-secondary'}`}>
          {label}
        </span>
        {s.enabled && (
          <span className="ml-auto text-[10px] text-primary/70 font-mono">
            {s.useRange ? `${s.start}–${s.end}` : (s.values.slice(0, 12) || '…')}
          </span>
        )}
      </label>

      {/* Config — shown when enabled */}
      {s.enabled && (
        <div className="px-2 pb-2 flex flex-col gap-2 border-t border-divider/40 pt-1.5">
          {/* Prefix */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-text-secondary w-9 flex-shrink-0">Prefix</span>
            <input
              type="text"
              value={s.prefix}
              onChange={e => onChange({ prefix: e.target.value })}
              placeholder={label.charAt(0)}
              className="form-input flex-grow text-[11px] py-0.5"
              maxLength={20}
            />
          </div>

          {/* Range vs values */}
          <div className="flex gap-3">
            {(['Range', 'Values'] as const).map((opt, i) => (
              <label key={opt} className="flex items-center gap-1.5 cursor-pointer text-[11px] text-text-secondary">
                <input type="radio" checked={i === 0 ? s.useRange : !s.useRange} onChange={() => onChange({ useRange: i === 0 })} className="text-primary" />
                {opt}
              </label>
            ))}
          </div>

          {s.useRange ? (
            <div className="grid grid-cols-3 gap-1.5">
              {[
                ['Start', 'start', s.start],
                ['End',   'end',   s.end],
                ['Pad',   'pad',   s.pad],
              ].map(([lbl, field, val]) => (
                <div key={field as string}>
                  <span className="text-[10px] text-text-secondary block mb-0.5">{lbl as string}</span>
                  <input
                    type="number"
                    value={val as string}
                    onChange={e => onChange({ [field as string]: e.target.value } as Partial<LevelState>)}
                    className="form-input w-full text-[11px] py-0.5"
                    min={0} max={field === 'pad' ? 10 : undefined}
                  />
                </div>
              ))}
            </div>
          ) : (
            <div>
              <span className="text-[10px] text-text-secondary block mb-0.5">Comma-separated</span>
              <input
                type="text"
                value={s.values}
                onChange={e => onChange({ values: e.target.value })}
                placeholder="A, B, C"
                className="form-input w-full text-[11px] py-0.5"
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
