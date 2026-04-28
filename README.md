# DeepEcho

**Cetacean Acoustic & Bio-logging Tracking Dashboard**

DeepEcho is an interactive web platform for analyzing cetacean (whale, dolphin, orca) behavior from
multi-sensor bio-logging tags (CATS-style). It synchronizes streaming hydrophone audio with 3D
orientation, depth, speed, and accelerometer data to reveal foraging, diving, and acoustic
behavior — all in the browser, in real time, on multi-gigabyte deployments.

> Developed by **Associazione Cecilia Bellezza**.
> Inspired by the MATLAB CATS Toolbox `plot_dynamic_creak()` workflow, rebuilt as a modern
> web stack: **FastAPI + NumPy** (backend) and **React + Plotly.js + Zustand** (frontend).

---

## Table of Contents

1. [What problem does it solve?](#what-problem-does-it-solve)
2. [Feature overview](#feature-overview)
3. [Architecture at a glance](#architecture-at-a-glance)
4. [Quick start](#quick-start)
5. [Data inputs](#data-inputs)
6. [Analysis pipeline (end-to-end)](#analysis-pipeline-end-to-end)
7. [Project layout](#project-layout)
8. [Configuration](#configuration)
9. [Testing](#testing)
10. [References & credits](#references--credits)

---

## What problem does it solve?

Bio-logging tags record **hours of multi-sensor data** per deployment:

- A single hydrophone WAV file (≥ 192 kHz, frequently > 1 GB).
- A 10 Hz CSV of pitch / roll / heading / depth / speed / IMU (`*_10Hzprh_smoothed.csv`).
- A list of acoustic events (clicks, creaks, whooshes) with sample-aligned indices.

Marine biologists need to **inspect short intervals** (a creak, a fluke stroke, a prey-capture
attempt) inside this haystack — synchronized across audio, motion, and 3D position. Existing
MATLAB workflows are powerful but slow, single-machine, and not shareable.

**DeepEcho** turns each deployment into a navigable, browser-based dashboard:
six synchronized plots, a 3D oriented cetacean mesh, automatic dive and prey-capture detection,
and on-the-fly audio playback of any selected interval — without ever loading the full audio
into RAM.

---

## Feature overview

### Visual analysis
- **9 synchronized panels** in a draggable / resizable grid (`react-grid-layout`):
  Spectrogram, Depth & Speed, Pitch / Roll / Heading, Jerk & Fluke Stroke, Audio Waveform,
  3D Trajectory, Statistics, Dive Profile + Table, Energy (ODBA / VeDBA / MSA).
- **Shared crosshair**: hover any chart → red dotted line on every chart at the same time.
- **Shared zoom**: zoom one time-axis chart → all others follow (epsilon-protected to prevent
  feedback loops).
- **3D species-specific cetacean mesh** (sperm, fin, humpback, blue, orca, dolphin) with
  countershaded body, dorsal fin, and fluke, oriented live by the current pitch / roll / heading.
- **Color-coded dive phases**: descent (blue), bottom (amber), ascent (green).
- **Prey capture markers** (3σ jerk peaks, 1 s refractory) plotted on the 3D trajectory.

### Workflow
- **Drag-and-drop upload** of WAV + PRH CSV + Events CSV, or auto-load demo files on first paint.
- **Event navigation**: click a creak / click in the sidebar → analysis interval auto-set →
  charts re-render.
- **Manual interval selection** in seconds, with keyboard scrubbing
  (Space = play/pause, ←/→ = step, Shift+arrow = 1 s, R = reset zoom, Esc = exit maximize).
- **Audio playback** of the analyzed slice via Web Audio API (streamed from backend on demand).
- **CSV export** of full analysis (depth, speed, pitch, roll, heading, jerk, ODBA, VeDBA, MSA)
  and dive table.
- **Persistent layout & settings** (panels, grid, species, theme) via `localStorage`.

### Performance
- Streamed WAV upload (8 MB chunks) — never read full audio into RAM.
- `soundfile.seek()` for O(1)-memory slice reads of multi-GB files.
- Spectrogram down-sampled and **cached per (deployment, interval, resolution)**.
- Min/max-envelope waveform downsample (preserves peaks at 2000 points).
- Pre-computed PRH metrics & jerk cached per deployment in a singleton `SessionCache`.
- WebGL `scattergl` traces for waveform.

---

## Architecture at a glance

```
┌──────────────────────── BROWSER ────────────────────────┐
│  React 18 + Zustand + Plotly.js + Tailwind 4           │
│                                                         │
│  Sidebar  ─►  upload / events / settings / panels       │
│  DashboardGrid (react-grid-layout, 9 panels)            │
│       │  useSyncedPlotly hook → crosshair + zoom        │
│  Timeline (scrubber + interval inputs)                  │
│  HoverReadout (live values at cursor)                   │
└─────────────────────────┬───────────────────────────────┘
                          │ HTTP / JSON  (Vite proxy /api)
┌─────────────────────────▼───────────────────────────────┐
│  FastAPI + NumPy + SciPy + soundfile + pandas          │
│                                                         │
│  POST /api/upload     — stream WAV+CSVs, parse PRH,    │
│                         pre-compute jerk, cache 30 s    │
│                         preview spectrogram             │
│  GET  /api/preview/:id                                  │
│  POST /api/analyze    — interval slice: spectrogram,   │
│                         downsampled waveform, ODBA,     │
│                         VeDBA, MSA, jerk, fluke         │
│  POST /api/trajectory — dead-reckoned 3D path          │
│  GET  /api/audio/:id  — stream WAV slice for playback  │
│                                                         │
│  SessionCache (singleton) ─ DeploymentMetrics + spec   │
│  Temp dir per session     ─ wav / prh / events on disk │
└─────────────────────────────────────────────────────────┘
```

For deeper dives:
- [`frontend/README.md`](frontend/README.md) — React app internals (stores, hooks, plot
  components, mesh generator, sync algorithm).
- [`backend/README.md`](backend/README.md) — FastAPI internals (endpoints, processing
  modules, caching strategy, formulas, units).
- [`docs/DATA_STRUCTURE.md`](docs/DATA_STRUCTURE.md) — exact CSV/WAV format spec.
- [`DEVELOPMENT.md`](DEVELOPMENT.md) — phase history, known limitations, roadmap.

---

## Quick start

### Option A — Docker (recommended)

```bash
git clone <repo-url> deepecho
cd deepecho
docker-compose up
```

- Frontend: <http://localhost:3000>
- Backend Swagger UI: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

Ports overridable via `BACKEND_PORT` / `FRONTEND_PORT` (see `.env.example`).

### Option B — Local dev

**Backend** (Python ≥ 3.11):
```bash
cd backend
pip install -e ".[dev]"
uvicorn src.main:app --reload --port 8000
```

**Frontend** (Node ≥ 20):
```bash
cd frontend
npm install
npm run dev   # Vite on :3000, proxies /api → :8000
```

### First run

Drop a deployment's three files into `frontend/public/` named:
- `audio_demo.wav`
- `prh_demo.csv`
- `events_demo.csv`

…and they'll auto-load on page mount. Or use the **Upload** section in the sidebar.

---

## Data inputs

| File                          | Purpose                                            | Sampling     |
|-------------------------------|----------------------------------------------------|--------------|
| `*.wav`                       | Hydrophone audio (mono or stereo, downmixed)       | 96–250 kHz   |
| `pm*_10Hzprh_smoothed.csv`    | Filtered PRH + IMU (depth, speed, accel, gyro)     | 10 Hz        |
| `AllSignals_DP*.csv`          | Acoustic events with 10 Hz sample indices          | event-based  |

PRH columns the backend expects:
`pitch_smoothed`, `roll_smoothed_wrapped`, `heading_smoothed_wrapped`, `depth_smoothed`,
`speed_smoothed`, `Ax_Filt`, `Ay_Filt`, `Az_Filt`, `Gy_Filt`.

Events columns: `Type`, `DN_start_idx`, `DN_end_idx`, `Deployment_ID`.

Full spec — including unit conventions, time alignment, and naming — in
[`docs/DATA_STRUCTURE.md`](docs/DATA_STRUCTURE.md).

---

## Analysis pipeline (end-to-end)

1. **Upload** (`POST /api/upload`)
   WAV streamed to disk in 8 MB chunks. PRH parsed once, jerk and acceleration cached in the
   in-memory `SessionCache`. Preview spectrogram computed from first ≤ 30 s, downsampled to
   64×64, cached.

2. **Browse** — frontend renders the preview spectrogram + the events list. The user clicks
   an event (e.g. `creak #3`) or types a manual interval into the timeline.

3. **Analyze** (`POST /api/analyze`)
   Backend extracts the PRH slice from cache, reads the corresponding WAV samples directly
   from disk (`soundfile.seek/read`), computes a high-resolution spectrogram (downsampled to
   256×256 and cached per interval), down-envelopes the waveform to 2000 points, and computes
   ODBA / VeDBA / MSA via running-mean high-pass filter (3 s window) + raw + normalized
   fluke-stroke from `Gy_Filt`.

4. **Render** — analyzed JSON populates `deploymentStore.analysisData`; every plot
   component reads only the slices it needs and re-renders in `useMemo`. The
   `useSyncedPlotly` hook wires `plotly_hover` and `plotly_relayout` to a shared
   `timelineStore` so crosshair and zoom propagate to every chart.

5. **Trajectory** (`POST /api/trajectory`) — dead-reckoned 3D path via
   `cumsum(speed × cos(pitch) × {cos,sin}(-heading))` for x/y, `depth_smoothed` for z.
   3D mesh oriented per-frame from current `pitch`, `roll`, `heading`.

6. **Audio playback** (`GET /api/audio/:id`) — streams a 16-bit WAV of the requested
   sample range; frontend decodes via Web Audio API and animates a moving cursor.

7. **Local enrichment** — `diveDetect.js` segments depth into descent/bottom/ascent
   phases (≥ 5 m, 80 % bottom threshold). `preyDetection.js` flags jerk peaks > μ + 3σ
   with a 1 s refractory.

---

## Project layout

```
DeepEcho/
├── README.md                # ← this file
├── DEVELOPMENT.md           # phase history, roadmap, known limits
├── LICENSE                  # GNU GPL v3.0
├── docker-compose.yml       # backend + frontend (dev mode w/ live reload)
├── .env.example             # BACKEND_PORT / FRONTEND_PORT / PYTHONUNBUFFERED
├── .tool-versions           # asdf / mise pinned versions
│
├── backend/
│   ├── README.md            # ← deep technical doc
│   ├── Dockerfile           # python:3.11-slim, pip install -e .
│   ├── pyproject.toml       # fastapi, numpy, scipy, soundfile, pandas, pytest
│   ├── src/
│   │   ├── main.py          # FastAPI app, CORS, router wiring
│   │   ├── models.py        # Pydantic request/response schemas
│   │   ├── api/             # upload, preview, analyze, trajectory, audio_stream
│   │   ├── processing/      # wav_loader, prh_parser, spectrogram, metrics
│   │   └── cache/           # SessionCache + SpectrogramCache (singleton)
│   └── tests/               # pytest suite (60+ tests)
│
├── frontend/
│   ├── README.md            # ← deep technical doc
│   ├── Dockerfile           # node:20-alpine, vite dev
│   ├── package.json         # react 18, plotly.js, zustand, tailwind 4
│   ├── vite.config.js       # /api proxy → backend
│   ├── public/              # auto-loaded demo files
│   └── src/
│       ├── App.jsx          # keyboard shortcuts, layout shell
│       ├── components/      # Sidebar, DashboardGrid, Timeline, HoverReadout, plots/
│       ├── stores/          # deploymentStore, timelineStore, layoutStore, settingsStore
│       ├── hooks/           # useSyncedPlotly (crosshair + zoom + ResizeObserver)
│       └── lib/             # cetaceanMesh, diveDetect, preyDetection, utils
│
├── docs/
│   ├── DATA_STRUCTURE.md    # CSV/WAV format spec + alignment conventions
│   └── superpowers/
│
├── data/                    # sample/test data (gitignored when large)
└── risorse/                 # MATLAB references, original CATS toolbox docs
```

---

## Configuration

Copy `.env.example` to `.env` to override defaults:

| Var               | Default | Purpose                              |
|-------------------|---------|--------------------------------------|
| `BACKEND_PORT`    | `8000`  | Host port for FastAPI                |
| `FRONTEND_PORT`   | `3000`  | Host port for Vite dev server        |
| `VITE_API_TARGET` | `http://backend:8000` (Docker) / `http://localhost:8000` (local) | Target for `/api` proxy |
| `PYTHONUNBUFFERED`| `1`     | Flush Python stdout in containers    |

Front-end persistent settings (`zustand/persist` → `localStorage`):
- `deepecho-layout` — panels visibility + grid positions
- `deepecho-settings` — species, species lock, theme

---

## Testing

```bash
# Backend (pytest, 60+ tests)
cd backend && pytest -v

# Specific module
pytest tests/test_metrics.py -v
pytest tests/test_integration.py -v
```

Test suite covers: WAV loader (slice/seek), PRH parser (column flexibility), spectrogram
(low/medium/high-res, downsampling), metrics (jerk, trajectory, fluke), `SessionCache`
(load/extract/clamp), upload + analyze API (integration).

Frontend has no automated tests yet — use the dev server to iterate visually.

---

## References & credits

- **AnimalTags.org** — biologging metric formulas:
  <https://animaltags.org/biologging-tools-project/metrics-computation/>
- **CATS Toolbox** — original MATLAB visualizer that inspired the data model:
  <https://animaltags.org/biologging-tools-project/cats-tag/>
- **MATLAB script** of reference: `risorse/Dynamic Plot Tag Data/Matlab Script/DynamicPlot_Script.m`

Built with: React 18 · Plotly.js · Zustand · Tailwind 4 · FastAPI · NumPy · SciPy · SoundFile.

Developed by **Associazione Cecilia Bellezza**.
Licensed under [GNU GPL v3.0](LICENSE).
