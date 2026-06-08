import React, { useRef, useEffect, useMemo, useState } from 'react'
import { useDeploymentStore } from '../stores/deploymentStore'
import { useTimelineStore } from '../stores/timelineStore'
import { useLayoutStore, PANEL_LABELS } from '../stores/layoutStore'
import { useSettingsStore, SPECIES } from '../stores/settingsStore'

const EVENT_COLORS = ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#a855f7', '#06b6d4', '#ec4899']
function eventColor(type) {
  let h = 0
  for (let i = 0; i < type.length; i++) h = (h * 31 + type.charCodeAt(i)) >>> 0
  return EVENT_COLORS[h % EVENT_COLORS.length]
}

function Section({ title, defaultOpen = false, extra, children }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border-b border-border">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-muted/50 transition-colors"
      >
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">{title}</h2>
        <div className="flex items-center gap-2">
          {extra}
          <span className="text-muted-foreground text-xs">{open ? '▾' : '▸'}</span>
        </div>
      </button>
      {open && <div className="px-4 pb-3 space-y-2">{children}</div>}
    </div>
  )
}

export default function Sidebar() {
  const { deployment, isLoading, error, upload, analyze } = useDeploymentStore()
  const { selectedInterval, setSelectedInterval } = useTimelineStore()
  const { panels, togglePanel, resetLayout } = useLayoutStore()
  const [eventFilter, setEventFilter] = useState('')
  const [detected, setDetected] = useState({ wav: null, prh: null, events: null, metadata: null })
  const { species, setSpecies, speciesLock, setSpeciesLock, theme, setTheme, spectrogram, setSpectrogram, timeFormat, setTimeFormat } = useSettingsStore()

  const wavRef = useRef(null)
  const prhRef = useRef(null)
  const eventsRef = useRef(null)
  const folderRef = useRef(null)

  // Enable directory selection on the folder input (non-standard attributes)
  useEffect(() => {
    if (folderRef.current) {
      folderRef.current.setAttribute('webkitdirectory', '')
      folderRef.current.setAttribute('directory', '')
    }
  }, [])

  // Auto-load demo files on mount
  useEffect(() => {
    const autoLoad = async () => {
      try {
        const [wavRes, prhRes, eventsRes] = await Promise.all([
          fetch('/audio_demo.wav'),
          fetch('/prh_demo.csv'),
          fetch('/events_demo.csv'),
        ])
        if (!wavRes.ok || !prhRes.ok || !eventsRes.ok) return

        const wavBlob = await wavRes.blob()
        const prhBlob = await prhRes.blob()
        const eventsBlob = await eventsRes.blob()

        const wavFile = new File([wavBlob], 'audio_demo.wav', { type: 'audio/wav' })
        const prhFile = new File([prhBlob], 'prh_demo.csv', { type: 'text/csv' })
        const eventsFile = new File([eventsBlob], 'events_demo.csv', { type: 'text/csv' })

        await upload(wavFile, prhFile, eventsFile)
      } catch {
        // Demo files not available, ignore
      }
    }
    autoLoad()
  }, [])

  const handleUpload = async () => {
    const wav = wavRef.current?.files?.[0]
    const prh = prhRef.current?.files?.[0]
    const events = eventsRef.current?.files?.[0]
    if (!wav || !prh || !events) return
    await upload(wav, prh, events)
  }

  const classifyFile = (file) => {
    const name = file.name.toLowerCase()
    if (name.endsWith('.wav')) return 'wav'
    if (name.endsWith('.json') || name.includes('meta')) return 'metadata'
    if (name.includes('prh') || name.includes('10hz')) return 'prh'
    if (name.includes('signal') || name.includes('event')) return 'events'
    if (name.endsWith('.txt')) return 'metadata'
    if (name.endsWith('.csv')) return 'events' // last-resort csv
    return null
  }

  const handleFolderSelect = (e) => {
    const files = Array.from(e.target.files || [])
    const next = { wav: null, prh: null, events: null, metadata: null }
    for (const f of files) {
      const role = classifyFile(f)
      if (role && !next[role]) next[role] = f
    }
    setDetected(next)
  }

  const handleFolderUpload = async () => {
    if (!detected.wav || !detected.prh || !detected.events) return
    await upload(detected.wav, detected.prh, detected.events, detected.metadata)
  }

  const handleAnalyze = async () => {
    if (!deployment) return
    useTimelineStore.getState().setXRange(null)
    useTimelineStore.getState().setCurrentTime(0)
    useTimelineStore.getState().setActiveEventLabel(null) // manual interval, no event label
    await analyze(
      deployment.deployment_id,
      selectedInterval.start_idx,
      selectedInterval.end_idx
    )
  }

  const filteredEvents = useMemo(() => {
    if (!deployment?.events) return []
    const q = eventFilter.trim().toLowerCase()
    if (!q) return deployment.events
    return deployment.events.filter((e) =>
      (e.Type || e.type || '').toLowerCase().includes(q)
    )
  }, [deployment, eventFilter])

  const handleEventClick = async (event, index) => {
    if (!deployment) return
    const startIdx = event.start_idx || event.DN_start_idx
    const endIdx = event.end_idx || event.DN_end_idx
    const type = event.Type || event.type || 'Event'
    setSelectedInterval({ start_idx: startIdx, end_idx: endIdx })
    useTimelineStore.getState().setActiveEventLabel(`${type} #${index + 1}`)
    useTimelineStore.getState().setXRange(null)
    useTimelineStore.getState().setCurrentTime(0)
    await analyze(deployment.deployment_id, startIdx, endIdx)
  }

  const handleExportCSV = () => {
    const analysisData = useDeploymentStore.getState().analysisData
    if (!analysisData || !deployment?.deployment_id) return

    const depth = analysisData.depth || []
    const speed = analysisData.speed || []
    const pitch = analysisData.pitch || []
    const roll = analysisData.roll || []
    const heading = analysisData.heading || []
    const jerk = analysisData.jerk || []
    const odba = analysisData.odba || []
    const vedba = analysisData.vedba || []
    const msa = analysisData.msa || []

    const duration = (analysisData.end_idx - analysisData.start_idx) / 10
    const n = depth.length

    const rows = ['time,depth,speed,pitch,roll,heading,jerk,odba,vedba,msa']
    for (let i = 0; i < n; i++) {
      const time = (i / n) * duration
      rows.push([
        time.toFixed(3),
        (depth[i] ?? '').toFixed(3),
        (speed[i] ?? '').toFixed(3),
        (pitch[i] ?? '').toFixed(3),
        (roll[i] ?? '').toFixed(3),
        (heading[i] ?? '').toFixed(3),
        (jerk[i] ?? '').toFixed(3),
        (odba[i] ?? '').toFixed(3),
        (vedba[i] ?? '').toFixed(3),
        (msa[i] ?? '').toFixed(3),
      ].join(','))
    }

    const csv = rows.join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${deployment.deployment_id}_analysis.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <aside className="w-72 bg-card border-r border-border flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <h1 className="text-lg font-bold text-foreground">DeepEcho</h1>
        <p className="text-xs text-muted-foreground">Cetacean Acoustic Tracking Dashboard</p>
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* Upload */}
        <Section title="Upload" defaultOpen={!deployment}>
          <label htmlFor="folder-input" className="block text-xs text-muted-foreground">Upload deployment folder</label>
          <input
            id="folder-input"
            ref={folderRef}
            type="file"
            multiple
            onChange={handleFolderSelect}
            className="block w-full text-xs text-muted-foreground file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:bg-muted file:text-foreground hover:file:bg-border cursor-pointer"
            aria-label="Select deployment folder"
          />
          {(detected.wav || detected.prh || detected.events || detected.metadata) && (
            <div className="text-[10px] text-muted-foreground space-y-0.5 mt-1">
              <div>WAV: {detected.wav?.name || <span className="text-destructive">missing</span>}</div>
              <div>PRH: {detected.prh?.name || <span className="text-destructive">missing</span>}</div>
              <div>Events: {detected.events?.name || <span className="text-destructive">missing</span>}</div>
              <div>Metadata: {detected.metadata?.name || <span className="italic">none (optional)</span>}</div>
            </div>
          )}
          <button
            onClick={handleFolderUpload}
            disabled={isLoading || !detected.wav || !detected.prh || !detected.events}
            className="w-full py-1.5 px-3 text-sm font-medium rounded bg-accent text-accent-foreground hover:bg-accent/80 disabled:opacity-50 transition-colors"
            aria-label="Upload detected deployment folder"
          >
            {isLoading ? 'Uploading...' : 'Upload folder'}
          </button>
          <p className="text-[10px] text-muted-foreground pt-1 border-t border-border/40">Or select files manually:</p>
          <div className="space-y-1.5">
            <label htmlFor="wav-input" className="block text-xs text-muted-foreground">WAV Audio</label>
            <input id="wav-input" ref={wavRef} type="file" accept=".wav" className="block w-full text-xs text-muted-foreground file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:bg-muted file:text-foreground hover:file:bg-border cursor-pointer" aria-label="Select WAV audio file" />
            <label htmlFor="prh-input" className="block text-xs text-muted-foreground">PRH CSV</label>
            <input id="prh-input" ref={prhRef} type="file" accept=".csv,.txt" className="block w-full text-xs text-muted-foreground file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:bg-muted file:text-foreground hover:file:bg-border cursor-pointer" aria-label="Select PRH motion data CSV" />
            <label htmlFor="events-input" className="block text-xs text-muted-foreground">Events CSV</label>
            <input id="events-input" ref={eventsRef} type="file" accept=".csv,.txt" className="block w-full text-xs text-muted-foreground file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:bg-muted file:text-foreground hover:file:bg-border cursor-pointer" aria-label="Select events CSV file" />
          </div>
          <button
            onClick={handleUpload}
            disabled={isLoading}
            className="w-full py-1.5 px-3 text-sm font-medium rounded bg-accent text-accent-foreground hover:bg-accent/80 disabled:opacity-50 transition-colors"
            aria-label="Upload WAV, PRH, and events files"
          >
            {isLoading ? 'Uploading...' : 'Upload Files'}
          </button>
          {error && <p className="text-xs text-destructive">{error}</p>}
          {deployment && (
            <p className="text-xs text-green-400">
              Loaded: {deployment.deployment_id} ({deployment.duration_seconds?.toFixed(1)}s)
            </p>
          )}
        </Section>

        {/* Settings */}
        <Section title="Settings">
          <label className="block text-xs text-muted-foreground">Species</label>
          <div className="flex gap-2">
            <select
              value={species}
              onChange={(e) => !speciesLock && setSpecies(e.target.value)}
              disabled={speciesLock}
              className="flex-1 px-2 py-1 rounded bg-muted border border-border text-foreground text-xs disabled:opacity-50"
              aria-label="Select cetacean species for 3D visualization"
            >
              {SPECIES.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
            <label className="flex items-center gap-1 text-xs text-muted-foreground cursor-pointer hover:text-foreground" title="Lock species selection">
              <input
                type="checkbox"
                checked={speciesLock}
                onChange={(e) => setSpeciesLock(e.target.checked)}
                className="rounded border-border accent-accent"
              />
              🔒
            </label>
          </div>
          <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer hover:text-foreground">
            <input
              type="checkbox"
              checked={theme === 'light'}
              onChange={(e) => {
                const newTheme = e.target.checked ? 'light' : 'dark'
                setTheme(newTheme)
                document.documentElement.classList.toggle('dark', newTheme === 'dark')
              }}
              className="rounded border-border accent-accent"
            />
            Light mode
          </label>
          <label className="block text-xs text-muted-foreground mt-2">Spectrogram colorscale</label>
          <select
            value={spectrogram.colorscale}
            onChange={(e) => setSpectrogram({ colorscale: e.target.value })}
            className="w-full px-2 py-1 rounded bg-muted border border-border text-foreground text-xs"
            aria-label="Spectrogram colorscale"
          >
            {['Viridis', 'Inferno', 'Jet', 'Greys'].map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <div className="flex gap-2 mt-1">
            <label className="flex-1 text-xs text-muted-foreground">
              dB min
              <input
                type="number" placeholder="auto"
                value={spectrogram.dbMin ?? ''}
                onChange={(e) => setSpectrogram({ dbMin: e.target.value === '' ? null : parseFloat(e.target.value) })}
                className="w-full px-2 py-1 rounded bg-muted border border-border text-foreground text-xs"
                aria-label="Spectrogram dB minimum"
              />
            </label>
            <label className="flex-1 text-xs text-muted-foreground">
              dB max
              <input
                type="number" placeholder="auto"
                value={spectrogram.dbMax ?? ''}
                onChange={(e) => setSpectrogram({ dbMax: e.target.value === '' ? null : parseFloat(e.target.value) })}
                className="w-full px-2 py-1 rounded bg-muted border border-border text-foreground text-xs"
                aria-label="Spectrogram dB maximum"
              />
            </label>
          </div>
          <label className="block text-xs text-muted-foreground mt-2">Time display</label>
          <select
            value={timeFormat}
            onChange={(e) => setTimeFormat(e.target.value)}
            className="w-full px-2 py-1 rounded bg-muted border border-border text-foreground text-xs"
            aria-label="Time display format"
          >
            <option value="seconds">Seconds</option>
            <option value="mmss">Minutes:Seconds</option>
            <option value="hms">Hours:Minutes:Seconds</option>
            <option value="absolute" disabled={!deployment?.metadata?.deployment_start}>
              Absolute clock time
            </option>
          </select>
        </Section>

        {/* Panels */}
        <Section title="Panels" extra={
          <button
            onClick={(e) => { e.stopPropagation(); resetLayout() }}
            className="text-[10px] text-muted-foreground hover:text-accent"
            title="Reset panels and layout to defaults"
          >
            Reset
          </button>
        }>
          <div className="space-y-1">
            {panels.map((panel) => (
              <label key={panel.id} className="flex items-center gap-2 text-sm cursor-pointer hover:text-foreground text-muted-foreground">
                <input
                  type="checkbox"
                  checked={panel.visible}
                  onChange={() => togglePanel(panel.id)}
                  className="rounded border-border accent-accent"
                />
                {PANEL_LABELS[panel.type]}
              </label>
            ))}
          </div>
        </Section>

        {/* Events */}
        <Section title={`Events${deployment?.events?.length ? ` (${filteredEvents.length}/${deployment.events.length})` : ''}`} defaultOpen={true}>
          {deployment?.events?.length > 0 && (
            <input
              type="text"
              placeholder="Filter by type..."
              value={eventFilter}
              onChange={(e) => setEventFilter(e.target.value)}
              className="w-full px-2 py-1 rounded bg-muted border border-border text-foreground text-xs placeholder:text-muted-foreground"
              aria-label="Filter events by type"
            />
          )}
          {deployment?.events?.length > 0 ? (
            <div className="space-y-1 max-h-64 overflow-y-auto">
              {filteredEvents.map((event, i) => {
                const type = event.Type || event.type || 'Event'
                const color = eventColor(type)
                const startIdx = event.DN_start_idx || event.start_idx
                const endIdx = event.DN_end_idx || event.end_idx
                const isActive = selectedInterval.start_idx === startIdx && selectedInterval.end_idx === endIdx
                return (
                  <button
                    key={i}
                    onClick={() => handleEventClick(event, i)}
                    className={`w-full text-left px-2 py-1.5 text-xs rounded transition-colors flex items-center gap-2 ${
                      isActive ? 'bg-accent/20 border border-accent/40' : 'hover:bg-muted'
                    }`}
                    aria-label={`Jump to ${type} event at samples ${startIdx}-${endIdx}`}
                  >
                    <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                    <span className="font-medium text-foreground">{type}</span>
                    <span className="text-muted-foreground ml-auto">
                      {((endIdx - startIdx) / 10).toFixed(0)}s
                    </span>
                  </button>
                )
              })}
              {filteredEvents.length === 0 && (
                <p className="text-xs text-muted-foreground italic">No match</p>
              )}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">No events loaded</p>
          )}
        </Section>
      </div>

      {/* Analyze & Export buttons */}
      {deployment && (
        <div className="p-4 border-t border-border space-y-2">
          <button
            onClick={handleAnalyze}
            disabled={isLoading}
            className="w-full py-2 px-3 text-sm font-medium rounded bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 transition-colors"
            aria-label="Analyze selected interval"
          >
            {isLoading ? 'Analyzing...' : 'Analyze Interval'}
          </button>
          <button
            onClick={handleExportCSV}
            disabled={!deployment}
            className="w-full py-2 px-3 text-sm font-medium rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
            title="Export analysis data as CSV"
            aria-label="Export analysis data as CSV"
          >
            ⬇ Export CSV
          </button>
        </div>
      )}

      {/* Credits */}
      <div className="p-3 border-t border-border text-center">
        <p className="text-[10px] text-muted-foreground leading-tight">
          Developed by
          <br />
          <span className="text-foreground font-medium">
            Associazione Cecilia Bellezza
          </span>
        </p>
      </div>
    </aside>
  )
}
