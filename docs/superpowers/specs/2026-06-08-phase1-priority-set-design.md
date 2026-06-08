# Phase 1 — Priority Set Design

**Date:** 2026-06-08
**Source:** `docs/rifiniture.md` (email exchange with Giulian — call-notes priority section)
**Status:** Approved for implementation

## Goal

Implement the prioritized refinement set agreed during the call: working light mode,
improved spectrogram (dB contrast + colorscale), timestamp fixes, flexible time display,
and folder-based upload with a metadata file. Update the README to match.

This is the first of three planned iterations. Phase 2 (quick UX fixes) and Phase 3
(acoustic events on the 3D trajectory) follow with review checkpoints in between.

## Scope (in)

1. Light mode that actually works (incl. light-background plots for presentation export).
2. Spectrogram: FFT 1024 / 50% overlap, adjustable dB contrast, colorscale selector, colorbar.
3. Event timestamps carried through the backend; flexible time display (s / mm:ss / hh:mm:ss / absolute).
4. Folder-based upload with auto-detect + optional metadata file (JSON or plain-text, auto-detected).
5. Statistics panel shows parsed metadata as text.
6. README updated.

## Scope (out / deferred)

- **Phase 2:** event duration as `SS.FF` + timestamp on same line, upload button color states,
  PRH ±180° visual jump fix, bigger/contrasted 3D whale marker, "minutes" handling refinements.
- **Phase 3:** toggle acoustic events (creak/click/coda…) on the 3D trajectory.
- **Big features (later):** GPS map + bathymetry, play/animate trajectory + GIF export,
  multi-event selection, manual dive-phase UI, processed-file download/reupload.

## Design

### 1. Light mode

**Problem:** `index.css` hardcodes dark colors directly in Tailwind 4's `@theme` block with no
light variant. The Sidebar toggle calls `document.documentElement.classList.toggle('dark', …)`,
but nothing reads that class, and the persisted theme is never re-applied on reload. Every plot
component also hardcodes dark hex (`#09090b`, `#a1a1aa`, `#27272a`).

**Fix:**
- Refactor `index.css`: `@theme` tokens reference runtime CSS variables
  (`--color-background: var(--bg)` etc.). Define light values under `:root` and dark overrides
  under `.dark`. Default app to dark (apply `.dark` from `settingsStore.theme` on mount in `App.jsx`).
- Add `frontend/src/hooks/usePlotTheme.js` → returns `{ paper, plot, grid, axisColor, fontColor,
  crosshair }` derived from `settingsStore.theme`. All 9 plot components consume it instead of
  hardcoded hex. Plotly `paper_bgcolor`/`plot_bgcolor`/axis `color`/`gridcolor` come from the hook.
- Result: exported plot images have a white background in light mode.

### 2. Spectrogram

- **Backend** `processing/spectrogram.py`: `compute_detailed_spectrogram` uses `nperseg=1024`,
  `noverlap=512` (50%). dB conversion unchanged. Preview untouched.
- **Frontend** `SpectrogramPlot.jsx` + `settingsStore`:
  - `zmin`/`zmax` heatmap range bound to two numeric inputs ("dB min" / "dB max"). Defaults derived
    from data percentiles (e.g. p5/p99) on first render of an interval.
  - Colorscale selector: Viridis (default), Inferno, Jet, Greys.
  - Visible colorbar (`showscale: true`).
  - Spectrogram view settings persisted in `settingsStore` under a `spectrogram` key.

### 3. Timestamps + flexible time display

- **Backend** `api/upload.py`: when building `events_list`, carry `start_ts`, `end_ts`, `mean_ts`
  from `Start_duration_timestamp` / `End_duration_timestamp` / `Mean_duration_timestamp` when present.
  Return parsed metadata (see §4) in `UploadResponse` under a new optional `metadata` field
  (`models.py` updated).
- **Frontend**:
  - `settingsStore.timeFormat`: `'seconds' | 'mmss' | 'hms' | 'absolute'`.
  - `lib/utils.js`: `formatTime(seconds, mode, deploymentStart)` → string. Absolute mode adds
    `seconds` to `deploymentStart` (from metadata) and renders clock time; if no `deploymentStart`,
    the absolute option is disabled and it falls back to `hms`.
  - Time-format selector in Settings. Axis tick labels (time-axis plots) and Timeline readouts use
    `formatTime`.
  - Interval inputs gain a **s ⇄ min** unit toggle (display only; stored internally as indices).

### 4. Folder-based upload + metadata

- **Frontend** `Sidebar.jsx`:
  - Primary path: folder picker (`<input webkitdirectory>`). On selection, auto-detect:
    - `*.wav` → audio
    - filename matches `prh` or `10Hz` → PRH CSV
    - filename matches `signals` or `events` → events CSV
    - `*.json`, `*.txt`, or filename matches `meta` → metadata
  - Show the detected file→role mapping; user confirms and uploads.
  - Existing three manual file inputs retained as a collapsible fallback.
  - `deploymentStore.upload` accepts an optional `metadataFile` and appends it to the form data.
- **Backend**:
  - `api/upload.py`: add `metadata_file: UploadFile = File(None)`. Save and parse if present.
  - New `processing/metadata_parser.py`: `parse_metadata(path) -> dict`.
    - Auto-detect: attempt `json.load`; on failure, parse the plain-text `--- SECTION ---` format
      (GENERAL INFO / DATE / GPS TRACK LOG / ADDITIONAL METADATA).
    - Normalize both into one dict: `title`, `deployment_id`, `species`, `project`, `notes`,
      `deployment_start`, `deployment_end`, `timezone`, `gps_track` (list of
      `{label?, timestamp, latitude, longitude}`), `additional_metadata`
      (`tag_model`, `sampling_rate_audio`, `sampling_rate_sensors`).
    - Missing fields → `None`/empty; never raise on partial files.
  - Store parsed metadata in the session and return it in the response.

### 5. Statistics panel

`plots/StatsPanel.jsx`: render parsed metadata as a labelled text block — deployment ID, species,
project, notes, start/end, timezone, tag model, audio/sensor sampling rates, and GPS point count.
No map (deferred).

### 6. README

Update `README.md`: light mode is functional; spectrogram controls; flexible time display; new
folder upload + optional metadata file; metadata fields shown in Statistics. Update the "Data inputs"
table to include the optional metadata file (both formats).

## Components touched

- Backend: `processing/spectrogram.py`, `processing/metadata_parser.py` (new), `api/upload.py`,
  `models.py`.
- Frontend: `index.css`, `App.jsx`, `stores/settingsStore.js`, `stores/deploymentStore.js`,
  `components/Sidebar.jsx`, `components/Timeline.jsx`, `hooks/usePlotTheme.js` (new),
  `lib/utils.js`, all `components/plots/*.jsx`.
- Docs: `README.md`.

## Testing

- **Backend (pytest):**
  - `metadata_parser`: JSON file, plain-text DP1 file, missing/partial file, malformed file.
  - spectrogram: detailed uses 1024/512.
  - upload: event timestamps carried through; metadata returned when file present, absent otherwise.
- **Frontend:** manual via dev server — toggle light/dark and verify all plots + export bg;
  spectrogram dB/colorscale controls; each time-format mode; folder upload auto-detect with and
  without a metadata file.

## Risks / notes

- Tailwind 4 `@theme` + runtime CSS-var switching must be verified against the installed Tailwind
  version (light mode is the riskiest piece).
- `webkitdirectory` is Chromium/WebKit-friendly; the manual-input fallback covers other cases.
- Absolute-time correctness depends on the deployment-start timezone; we store and display the
  provided timezone string but do not convert across zones in Phase 1.
