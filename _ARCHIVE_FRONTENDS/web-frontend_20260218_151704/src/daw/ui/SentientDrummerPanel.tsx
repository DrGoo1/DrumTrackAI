import React, { useMemo, useState } from 'react'

type SentientRun = {
  ts: number
  metadata: any
  config?: any
}

function fmtTs(ts: number): string {
  try {
    return new Date(ts).toLocaleString()
  } catch {
    return String(ts)
  }
}

function safeString(v: any): string {
  if (v === null || v === undefined) return ''
  if (typeof v === 'string') return v
  try {
    return JSON.stringify(v)
  } catch {
    return String(v)
  }
}

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

function downloadJson(filename: string, obj: any) {
  try {
    const text = JSON.stringify(obj, null, 2)
    const blob = new Blob([text], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch {
    // ignore
  }
}

export const SentientDrummerPanel: React.FC<{
  runs: SentientRun[]
  selectedIndex?: number
  onSelectIndex?: (idx: number) => void
}> = ({ runs, selectedIndex = 0, onSelectIndex }) => {
  const [openDetails, setOpenDetails] = useState(false)
  const [openWeights, setOpenWeights] = useState(false)
  const [copied, setCopied] = useState<string | null>(null)

  const selected = runs[selectedIndex] ?? null

  const block = selected?.metadata?.drummerBrain ?? null
  const prov = block?.provenance ?? null

  const enabled = Boolean(block?.enabled)
  const attempted = Boolean(prov?.attempted)
  const used = Boolean(prov?.used)
  const fallbackUsed = Boolean(prov?.fallback_used)
  const reason = safeString(prov?.reason || prov?.fallback_reason || '')
  const datasetId = safeString(prov?.dataset_id || '')
  const assetId = safeString(prov?.asset_id || '')
  const policyVersion = safeString(prov?.policy_version || '')
  const dbPath = safeString(prov?.db_path || '')
  const selectedGrooveSource = safeString(prov?.selected_groove_source || '')

  const weights = prov?.weights ?? null

  const badge = useMemo(() => {
    if (!enabled) return { text: 'Disabled', cls: 'bg-neutral-800 text-neutral-200 border-neutral-700' }
    if (!attempted) return { text: 'Not Attempted', cls: 'bg-neutral-800 text-neutral-200 border-neutral-700' }
    if (used) return { text: 'Used', cls: 'bg-emerald-500/20 text-emerald-200 border-emerald-400/40' }
    if (fallbackUsed) return { text: 'Fallback', cls: 'bg-amber-500/20 text-amber-200 border-amber-400/40' }
    return { text: 'No Match', cls: 'bg-neutral-800 text-neutral-200 border-neutral-700' }
  }, [enabled, attempted, used, fallbackUsed])

  if (!runs || runs.length === 0) {
    return (
      <div className="border border-neutral-800 rounded bg-neutral-950/60 p-2">
        <div className="text-[12px] font-semibold text-neutral-200">Sentient Drummer</div>
        <div className="text-[11px] text-neutral-400">No generations yet.</div>
      </div>
    )
  }

  const jsonText = selected ? JSON.stringify(block ?? {}, null, 2) : ''

  return (
    <div className="border border-neutral-800 rounded bg-neutral-950/60">
      <div className="flex items-center justify-between px-2 py-1 border-b border-neutral-800">
        <div className="flex items-center gap-2">
          <div className="text-[12px] font-semibold text-neutral-200">Sentient Drummer</div>
          <div className={`text-[10px] px-2 py-0.5 rounded border ${badge.cls}`}>{badge.text}</div>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="text-[10px] px-2 py-0.5 rounded bg-neutral-800 hover:bg-neutral-700"
            onClick={async () => {
              const ok = await copyText(jsonText)
              setCopied(ok ? 'Copied JSON' : 'Copy failed')
              setTimeout(() => setCopied(null), 1500)
            }}
          >
            Copy JSON
          </button>
          <button
            className="text-[10px] px-2 py-0.5 rounded bg-neutral-800 hover:bg-neutral-700"
            onClick={() => downloadJson('sentient_drummer_provenance.json', block ?? {})}
          >
            Download
          </button>
        </div>
      </div>

      <div className="p-2 space-y-2">
        {copied && <div className="text-[10px] text-neutral-300">{copied}</div>}

        <div className="grid grid-cols-2 gap-2 text-[11px]">
          <div className="text-neutral-500">Run</div>
          <div className="text-neutral-200">{fmtTs(selected?.ts ?? Date.now())}</div>

          <div className="text-neutral-500">Selected Source</div>
          <div className="text-neutral-200">{selectedGrooveSource || '-'}</div>

          <div className="text-neutral-500">Dataset</div>
          <div className="text-neutral-200">{datasetId || '-'}</div>

          <div className="text-neutral-500">Asset</div>
          <div className="text-neutral-200">{assetId || '-'}</div>

          <div className="text-neutral-500">Reason</div>
          <div className="text-neutral-200">{reason || '-'}</div>

          <div className="text-neutral-500">Policy</div>
          <div className="text-neutral-200">{policyVersion || '-'}</div>

          <div className="text-neutral-500">DB</div>
          <div className="text-neutral-200 truncate" title={dbPath}>{dbPath || '-'}</div>
        </div>

        <div className="flex items-center justify-between">
          <button
            className="text-[11px] px-2 py-1 rounded bg-neutral-900 hover:bg-neutral-800 border border-neutral-800"
            onClick={() => setOpenDetails(v => !v)}
          >
            {openDetails ? 'Hide Details' : 'Show Details'}
          </button>
          <button
            className="text-[11px] px-2 py-1 rounded bg-neutral-900 hover:bg-neutral-800 border border-neutral-800"
            onClick={() => setOpenWeights(v => !v)}
          >
            {openWeights ? 'Hide Weights' : 'Show Weights'}
          </button>
        </div>

        {openWeights && (
          <div className="text-[10px] bg-neutral-950 border border-neutral-800 rounded p-2 overflow-x-auto whitespace-pre">
            {JSON.stringify(weights ?? {}, null, 2)}
          </div>
        )}

        {openDetails && (
          <div className="text-[10px] bg-neutral-950 border border-neutral-800 rounded p-2 overflow-x-auto whitespace-pre max-h-56">
            {jsonText}
          </div>
        )}

        <div className="pt-1 border-t border-neutral-800">
          <div className="text-[11px] text-neutral-300 font-medium">History</div>
          <div className="mt-1 space-y-1 max-h-40 overflow-y-auto">
            {runs.map((r, idx) => {
              const b = r.metadata?.drummerBrain
              const p = b?.provenance
              const status = !b?.enabled
                ? 'Disabled'
                : p?.used
                  ? 'Used'
                  : p?.fallback_used
                    ? 'Fallback'
                    : 'No Match'

              const isSel = idx === selectedIndex
              return (
                <button
                  key={r.ts}
                  className={
                    'w-full text-left text-[10px] px-2 py-1 rounded border ' +
                    (isSel
                      ? 'bg-neutral-800/70 border-neutral-700'
                      : 'bg-neutral-950 border-neutral-800 hover:bg-neutral-900')
                  }
                  onClick={() => onSelectIndex?.(idx)}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-neutral-200 truncate">{fmtTs(r.ts)}</div>
                    <div className="text-neutral-400">{status}</div>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
