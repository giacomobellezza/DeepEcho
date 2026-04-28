# DeepEcho — Frontend

React 18 + Vite + Plotly.js single-page app that drives the cetacean dashboard. Renders nine
synchronized panels in a draggable / resizable grid, talks to the FastAPI backend over a
Vite proxy, and persists user layout and settings in `localStorage`.

The data flow is intentionally simple: **three Zustand stores own the state**, every panel
is a stateless `useMemo`-driven Plotly chart, and a single hook (`useSyncedPlotly`)
keeps the crosshair and zoom in lock-step across all charts.

---

## Stack

| Concern              | Library                            |
|----------------------|------------------------------------|
| UI framework         | React 18                           |
| Bundler / dev server | Vite 5                             |
| Charts               | Plotly.js (`plotly.js-dist-min`) via `react-plotly.js` |
| Layout               | `react-grid-layout` (responsive)   |
| State                | `zustand` ^5 + `zustand/middleware` (persist)  |
| Styling              | Tailwind CSS 4 (Vite plugin)       |
| Utilities            | `clsx`, `tailwind-merge`           |
| Audio playback       | Web Audio API (no library)         |

Node ≥ **20** required.

---

## Running

### Local

```bash
cd frontend
npm install
npm run dev          # Vite on :3000, /api proxied to localhost:8000
npm run build        # production bundle in dist/
npm run preview      # serve dist/ statically
```

`vite.config.js` proxies `/api/*` to `process.env.VITE_API_TARGET || http://localhost:8000`.

### Docker

`Dockerfile` runs `npm run dev` against `node:20-alpine`. `docker-compose.yml` mounts the
source for hot reload and sets `VITE_API_TARGET=http://backend:8000`.

---

## Module map

```
src/
├── App.jsx                 # shell: theme effect, keyboard shortcuts, layout
├── index.jsx               # ReactDOM.createRoot
├── index.css               # Tailwind layers + custom CSS vars (theme tokens)
│
├── components/
│   ├── Sidebar.jsx         # upload, settings, panels, events list, export CSV
│   ├── DashboardGrid.jsx   # ResponsiveGridLayout, panel registry, maximize mode
│   ├── PanelWrapper.jsx    # drag handle + export PNG + maximize/close
│   ├── Timeline.jsx        # scrubber + start/end interval inputs + reset zoom
│   ├── HoverReadout.jsx    # live numeric readout at currentTime
│   └── plots/              # one component per panel (see below)
│
├── stores/                 # Zustand
│   ├── deploymentStore.js  # API calls + analysisData + deployment metadata
│   ├── timelineStore.js    # currentTime, xRange, selectedInterval, isPlaying
│   ├── layoutStore.js      # panels visibility + grid layout (persisted)
│   └── settingsStore.js    # species, theme (persisted)
│
├── hooks/
│   └── useSyncedPlotly.js  # crosshair + zoom + ResizeObserver wiring
│
├── lib/
│   ├── cetaceanMesh.js     # procedural mesh3d trace (sperm/fin/orca/...)
│   ├── diveDetect.js       # ≥5m dive segmentation w/ phase splits
│   ├── preyDetection.js    # μ + 3σ jerk peaks, 1 s refractory
│   └── utils.js            # cn() — clsx + tailwind-merge helper
│
└── context/                # (currently unused, kept for future providers)
```

---

## State architecture

State is split across **four** stores so unrelated panels don't re-render when one updates.

### `deploymentStore` — server-truth, API actions

```js
{
  deployment,       // upload response: id, duration, preview spectrogram, events
  analysisData,     // analyze response: spec + audio + prh + odba + ...
  isLoading,
  error,

  upload(wavFile, prhCsv, eventsCsv),   // POST /api/upload
  analyze(deploymentId, start, end),    // POST /api/analyze
  fetchTrajectory(deploymentId, s, e),  // POST /api/trajectory
  reset(),
}
```

`API_BASE = '/api'` is exported from this module — the Vite proxy handles host routing.

### `timelineStore` — ephemeral interaction state

```js
{
  currentTime,            // crosshair x-value (seconds, relative to interval)
  selectedInterval,       // { start_idx, end_idx } in PRH-frame indices (10 Hz)
  activeEventLabel,       // e.g. "Creak #3" — banner above charts
  xRange,                 // [min, max] sec for synced zoom, null = auto
  isPlaying,

  setCurrentTime, setSelectedInterval, setActiveEventLabel, setXRange,
  play, pause, togglePlay,
}
```

Not persisted. Events fire from `useSyncedPlotly` and from the `Timeline` component.

### `layoutStore` — UI layout (persisted to `deepecho-layout`)

```js
{
  panels,        // [{ id, type, visible }]
  gridLayout,    // [{ i, x, y, w, h, minW, minH }]  ← react-grid-layout
  maximizedId,   // null | panel id  (focused panel, full-screen mode)

  togglePanel, updateLayout, setMaximized, toggleMaximized, resetLayout,
  getVisiblePanels(), getVisibleLayout(),
}
```

`PANEL_LABELS` is exported from the same module to keep panel id ↔ display string in sync.

### `settingsStore` — preferences (persisted to `deepecho-settings`)

```js
{
  species,        // 'sperm' | 'fin' | 'humpback' | 'blue' | 'orca' | 'dolphin' | 'unknown'
  speciesLock,    // bool — disable species select
  theme,          // 'dark' | 'light'

  setSpecies, setSpeciesLock, setTheme,
}
```

`SPECIES` constant exports id + display name for each profile.

---

## Synchronized charting (`useSyncedPlotly`)

Every plot component calls this hook to wire itself into the shared timeline:

```js
const { plotRef, onHover, onRelayout, currentTime, xRange } = useSyncedPlotly()
```

Behaviour:

1. **`onHover(event)`** → reads `event.points[0].x` (always seconds, since every chart's
   x-axis is time) and writes it to `timelineStore.currentTime`. Every other chart re-renders
   with a vertical dotted line at `currentTime`.

2. **`onRelayout(event)`** → triggered by Plotly when the user pans / zooms. Reads
   `xaxis.range[0]` / `xaxis.range[1]` and writes `[r0, r1]` to `timelineStore.xRange`.
   Other charts pick it up via `useMemo` and apply `range: xRange` to their axis layout.

3. **Feedback-loop guard** — before writing the new range, compares with `xRangeRef.current`
   (set every render) within a 1e-6 epsilon. If the values match, the hook returns early.
   Without this, every chart's relayout would fire `setXRange` → re-render → relayout →
   infinite oscillation.

4. **`xaxis.autorange`** in the relayout event → resets `xRange` to `null`.

5. **ResizeObserver** — watches the parent `.react-grid-item` and dispatches a synthetic
   `window.resize` event when the grid cell changes size. Plotly's `useResizeHandler`
   listens to that event but doesn't see grid drag-resizes natively, so without this the
   chart would render stale at the wrong size.

Add the hook return values to your Plot:

```jsx
<Plot
  ref={plotRef}
  data={data} layout={layout}
  onHover={onHover} onRelayout={onRelayout}
  useResizeHandler config={{ responsive: true, displayModeBar: false }}
  style={{ width: '100%', height: '100%' }}
/>
```

Charts with a non-time x-axis (3D trajectory) skip the hook for hover/zoom but still
participate via the shared `currentTime` (used to position the cetacean mesh).

---

## Panel registry (`DashboardGrid.jsx`)

```js
const PLOT_COMPONENTS = {
  spectrogram: SpectrogramPlot,
  depthSpeed:  DepthSpeedPlot,
  prh:         PRHPlot,
  jerkFluke:   JerkFlukePlot,
  waveform:    WaveformPlot,
  trajectory:  TrajectoryPlot,
  stats:       StatsPanel,
  dives:       DivePanel,
  energy:      EnergyPlot,
}
```

The grid filters `panels` by `visible`, joins them with `gridLayout` (matched on `id`/`i`),
and renders each through `PanelWrapper`. Maximizing a panel takes a separate code path that
returns just that panel full-screen.

`onLayoutChange` writes the new positions back to the store; `onResize` / `onResizeStop`
fire a window resize so Plotly rescales mid-drag.

### Panel components

| File                  | Trace types               | Notes                                    |
|-----------------------|---------------------------|------------------------------------------|
| `SpectrogramPlot.jsx` | `heatmap` (Viridis)       | Uses preview spectrogram before analysis |
| `DepthSpeedPlot.jsx`  | dual-axis `scatter`       | Depth (reversed y) + Speed (y2)          |
| `PRHPlot.jsx`         | three `scatter` traces    | Pitch, roll, heading                     |
| `JerkFlukePlot.jsx`   | `scatter` + threshold line | μ+3σ horizontal line, prey-capture markers |
| `WaveformPlot.jsx`    | `scattergl` (WebGL)       | + Web Audio API playback button          |
| `TrajectoryPlot.jsx`  | `scatter3d` + `mesh3d`    | Path + start marker + cetacean mesh + prey |
| `DivePanel.jsx`       | `scatter` + `rect` shapes | + sortable HTML table + CSV export       |
| `EnergyPlot.jsx`      | three `scatter` traces    | ODBA / VeDBA / MSA                       |
| `StatsPanel.jsx`      | (no Plotly)               | Numeric summary card                     |

All time-domain charts apply `range: xRange` when set, and a vertical dotted line at
`currentTime`.

---

## 3D cetacean mesh (`lib/cetaceanMesh.js`)

Generates a Plotly `mesh3d` trace at runtime — no GLTF loader, no external assets.

- **Profiles** per species (`PROFILES` object) define proportions: `headRatio`, `maxWidth`,
  `maxHeight`, `headBulge`, `tailTaper`, `dorsalHeight`, `dorsalPos`, `flukeSpan`,
  `flukeLen`, plus dorsal/ventral colors for countershading.
- **Body** built as 16 rings × 14 slices ellipsoid, modulated by `bodyRadius(t)`
  (head bulge × tail taper × `sin(πt)` envelope).
- **Fluke** triangle pair at `x = -halfLen` spanning `flukeSpan × maxWidth`.
- **Dorsal fin** at `dorsalPos` along the body, height set by `dorsalHeight`.
- **Pectoral fins** at `pectoralPos`, length `pectoralLen`.
- **Countershading** — `lerpColor(ventral, dorsal, factor)` per vertex by `bodyZ`
  (negative = belly).
- **Rotation** — Euler ZYX (roll → pitch → heading) applied to each vertex; the resulting
  body z is **negated** to convert "dorsal up" body frame to "depth down" world frame
  (matches `compute_trajectory`'s `dz = depth`).

Coordinate conventions (must stay consistent with the backend):
```
heading = 0°  →  +x      (East)
heading = 90° →  -y      (North)
depth (z)     →  +z down (zaxis autorange='reversed' visually flips)
```

---

## Local algorithms (`lib/`)

### `diveDetect.js`
Segments depth into dives ≥ 5 m, splits each into descent / bottom / ascent using a
**80 % threshold** of the dive's max depth. Returns
`{ startTime, endTime, duration, maxDepth, bottomTime, descentRate, ascentRate }`.

Used by `DivePanel` for the colored phase rectangles and the table; CSV export available
from the panel header.

### `preyDetection.js`
Single-pass mean / std → threshold `μ + 3σ`, walks the array, emits indices where
`jerk[i] > threshold` and at least 1 second has passed since the previous emission.

Used by `JerkFlukePlot` and `TrajectoryPlot` to mark prey-capture attempts.

---

## Keyboard shortcuts (`App.jsx`)

| Key       | Action                            |
|-----------|-----------------------------------|
| `Space`   | Play / pause (toggles `isPlaying`) |
| `←` / `→` | Step `currentTime` by 0.1 s       |
| `Shift+←/→` | Step by 1 s                     |
| `R`       | Reset shared zoom (`xRange = null`) |
| `Esc`     | Exit maximize mode                |

The handler ignores keypresses while focus is in `input / textarea / select`.

---

## Theming

- Tokens live in `index.css` as CSS variables (`--background`, `--foreground`, `--accent`,
  …) under `:root` and `.dark`.
- The shell toggles `<html class="dark">` based on `settingsStore.theme`.
- All Plotly colors are hand-picked to match the dark palette (`#09090b` plot bg, `#27272a`
  gridlines, `#a1a1aa` text). The light theme keeps the same accent set.

---

## Auto-load demo files

`Sidebar.jsx` runs an effect on mount that fetches:
- `/audio_demo.wav`
- `/prh_demo.csv`
- `/events_demo.csv`

…and POSTs them to `/api/upload` if all three exist (404s are silently ignored). Drop your
own files into `frontend/public/` to enable this.

---

## CSV export

The sidebar's "Export CSV" button reads `analysisData` and emits one row per PRH frame:
`time,depth,speed,pitch,roll,heading,jerk,odba,vedba,msa`. The dive table has its own
exporter (`dives.csv`) with one row per detected dive.

PNG export per panel: each `PanelWrapper` calls `Plotly.downloadImage()` at 2× the rendered
size with filename `cats-<type>.png`.

---

## Performance notes

- **Re-render isolation**: every plot subscribes only to the slice of state it needs
  (`useTimelineStore((s) => s.currentTime)`). Hovering one chart updates `currentTime`,
  which only re-renders the `useMemo`-wrapped `data/layout` of charts that depend on it.
- **`useMemo` everywhere**: data + layout objects are memoized so React doesn't recompute
  Plotly traces on parent re-renders.
- **`scattergl` for waveform**: WebGL keeps 60 fps even at 2000+ points.
- **Min/max envelope downsample** (waveform, server-side): preserves peaks at 2000 points
  regardless of slice length.
- **Persisted layout `partialize`**: only `panels` and `gridLayout` are serialized — the
  ephemeral `maximizedId` is excluded.

---

## Conventions & gotchas

- **Index space**: PRH indices are at **10 Hz**; `currentTime` is in **seconds within the
  analyzed interval** (relative to `analysisData.start_idx`). Always convert at the
  boundary (see `Timeline.jsx` and `HoverReadout.jsx`).
- **Drag handles**: only the panel header has `.drag-handle`. Buttons inside the header
  call `e.stopPropagation()` so clicks don't initiate a drag.
- **Maximize mode**: changes the render path entirely (a single panel replaces the grid).
  An effect dispatches `window.resize` after the swap so Plotly recomputes its layout.
- **Auto-loaded demo files** are not removed if upload fails partway — clear them via the
  sidebar reset / refresh.
- **Crosshair hover** writes on every Plotly hover event. If a chart is sluggish, check
  that its `useMemo` dependencies are tight (don't depend on the whole `analysisData`
  object when you only need `analysisData.depth`).

---

## Adding a new panel

1. Create `src/components/plots/MyPanel.jsx`. Use `useSyncedPlotly()` for time-axis charts
   or read directly from stores for non-time panels.
2. Add the entry to `DEFAULT_PANELS` and `DEFAULT_LAYOUT` in `stores/layoutStore.js`,
   plus a label in `PANEL_LABELS`.
3. Register the component in `PLOT_COMPONENTS` inside `components/DashboardGrid.jsx`.
4. (Optional) Add a stat to `HoverReadout` if it has a useful per-frame value.

Charts should:
- Accept zero props.
- Pull from stores via narrow selectors.
- Wrap data/layout in `useMemo`.
- Render a "no data" placeholder when `analysisData` (or `deployment`) is missing.
