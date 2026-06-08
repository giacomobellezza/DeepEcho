# Phase 1 — Priority Set Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the prioritized refinement set — working light mode, improved spectrogram, timestamp handling + flexible time display, and folder-based upload with metadata — and update the README.

**Architecture:** Backend is FastAPI + NumPy/SciPy/pandas; frontend is React 18 + Zustand + Plotly.js + Tailwind 4. Light mode is made runtime-switchable via CSS custom properties consumed by Tailwind `@theme` tokens, plus a `usePlotTheme` hook feeding Plotly colors. A new `metadata_parser` module auto-detects JSON vs plain-text deployment metadata. The upload endpoint gains an optional metadata file and carries event timestamps through.

**Tech Stack:** Python 3.11, FastAPI, pytest, NumPy/SciPy/pandas, soundfile; React 18, Zustand, Plotly.js (`react-plotly.js`), Tailwind 4, Vite.

**Reference spec:** `docs/superpowers/specs/2026-06-08-phase1-priority-set-design.md`

**Conventions:**
- Backend tests: `cd backend && pytest tests/<file>::<test> -v`.
- Frontend has no automated tests; frontend tasks are verified manually via `cd frontend && npm run dev` (Vite on :3000). Each frontend task lists exact manual checks.
- Commit after each task.

---

## Task 1: Light mode CSS foundation

Make Tailwind tokens reference runtime CSS variables that switch on the `.dark` class. Default the app to dark.

**Files:**
- Modify: `frontend/src/index.css:3-16`
- Modify: `frontend/src/App.jsx:18-21`

- [ ] **Step 1: Rewrite the `@theme` block + add `:root` / `.dark` color sets**

Replace `frontend/src/index.css` lines 1-24 (the `@import`, `@theme` block, and `body` rule) with:

```css
@import "tailwindcss";

@theme {
  --color-background: var(--bg);
  --color-foreground: var(--fg);
  --color-card: var(--card);
  --color-card-foreground: var(--card-fg);
  --color-border: var(--border);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-fg);
  --color-accent: #3b82f6;
  --color-accent-foreground: #fafafa;
  --color-destructive: #ef4444;
  --color-ring: #3b82f6;
  --radius: 0.5rem;
}

:root {
  /* light theme (default values) */
  --bg: #ffffff;
  --fg: #0a0a0a;
  --card: #f4f4f5;
  --card-fg: #0a0a0a;
  --border: #e4e4e7;
  --muted: #f4f4f5;
  --muted-fg: #52525b;
}

.dark {
  --bg: #09090b;
  --fg: #fafafa;
  --card: #0a0a0f;
  --card-fg: #fafafa;
  --border: #27272a;
  --muted: #18181b;
  --muted-fg: #a1a1aa;
}

body {
  font-family: system-ui, -apple-system, sans-serif;
  background-color: var(--color-background);
  color: var(--color-foreground);
  margin: 0;
  padding: 0;
}
```

Leave the rest of the file (scrollbar, react-grid-layout, keyframes) unchanged — those already use `var(--color-*)` tokens and will follow automatically.

- [ ] **Step 2: Ensure App applies `.dark` from persisted theme on mount**

`frontend/src/App.jsx` already has the effect at lines 18-21. Confirm it reads `theme` from `useSettingsStore` (it does, line 15) and toggles `.dark`. No code change needed if present; if the effect is missing, add:

```jsx
useEffect(() => {
  document.documentElement.classList.toggle('dark', theme === 'dark')
}, [theme])
```

- [ ] **Step 3: Manual verification**

Run: `cd frontend && npm run dev`
Expected: App loads dark by default. Toggle "Light mode" in Settings → background turns white, text dark, sidebar/cards light. Reload page → light mode persists (was previously lost). Toggle back → dark restored.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/index.css frontend/src/App.jsx
git commit -m "feat(theme): runtime-switchable light/dark via CSS variables"
```

---

## Task 2: Theme-aware Plotly colors (`usePlotTheme`) across all plots

Plots hardcode dark hex. Introduce a hook and apply it everywhere so light mode (and white-background exports) work.

**Files:**
- Create: `frontend/src/hooks/usePlotTheme.js`
- Modify: every plot in `frontend/src/components/plots/`: `SpectrogramPlot.jsx`, `PRHPlot.jsx`, `DepthSpeedPlot.jsx`, `JerkFlukePlot.jsx`, `WaveformPlot.jsx`, `EnergyPlot.jsx`, `TrajectoryPlot.jsx`, `DivePanel.jsx`

- [ ] **Step 1: Create the hook**

Create `frontend/src/hooks/usePlotTheme.js`:

```js
import { useSettingsStore } from '../stores/settingsStore'

const THEMES = {
  dark: {
    paper: 'rgba(0,0,0,0)',
    plot: '#09090b',
    grid: '#27272a',
    axis: '#a1a1aa',
    zeroLine: '#52525b',
  },
  light: {
    paper: '#ffffff',
    plot: '#ffffff',
    grid: '#e4e4e7',
    axis: '#3f3f46',
    zeroLine: '#a1a1aa',
  },
}

export function usePlotTheme() {
  const theme = useSettingsStore((s) => s.theme)
  return THEMES[theme] || THEMES.dark
}
```

- [ ] **Step 2: Apply the hook in `PRHPlot.jsx`**

In `frontend/src/components/plots/PRHPlot.jsx`:
1. Add import at top: `import { usePlotTheme } from '../../hooks/usePlotTheme'`
2. Inside the component, after the `useSyncedPlotly()` line, add: `const theme = usePlotTheme()`
3. Add `theme` to the `useMemo` dependency array (currently `[analysisData, currentTime, xRange]` → `[analysisData, currentTime, xRange, theme]`).
4. Replace the hardcoded colors in `layout`:
   - `font: { size: 10, color: '#a1a1aa' }` → `font: { size: 10, color: theme.axis }` (both axis titles)
   - `color: '#a1a1aa'` → `color: theme.axis` (both axes)
   - `gridcolor: '#27272a'` → `gridcolor: theme.grid` (both axes)
   - `plot_bgcolor: '#09090b'` → `plot_bgcolor: theme.plot`
   - `paper_bgcolor: 'rgba(0,0,0,0)'` → `paper_bgcolor: theme.paper`
   - legend `font: { size: 10, color: '#a1a1aa' }` → `color: theme.axis`
   - zero-line shape `line: { color: '#52525b', ... }` → `color: theme.zeroLine`

- [ ] **Step 3: Apply the same mapping to the remaining plots**

For each of `SpectrogramPlot.jsx`, `DepthSpeedPlot.jsx`, `JerkFlukePlot.jsx`, `WaveformPlot.jsx`, `EnergyPlot.jsx`, `TrajectoryPlot.jsx`, `DivePanel.jsx`:
1. Add `import { usePlotTheme } from '../../hooks/usePlotTheme'`.
2. Add `const theme = usePlotTheme()` inside the component (before the `useMemo`/layout build).
3. Add `theme` to the relevant `useMemo` dependency array.
4. Apply this exact color mapping everywhere those literals appear in the layout:

| Hardcoded literal        | Replace with     |
|--------------------------|------------------|
| `'#09090b'` (plot_bgcolor)| `theme.plot`    |
| `'rgba(0,0,0,0)'` (paper_bgcolor) | `theme.paper` |
| `'#a1a1aa'` (axis/font/legend color) | `theme.axis` |
| `'#27272a'` (gridcolor)  | `theme.grid`     |
| `'#52525b'` (zero/baseline line) | `theme.zeroLine` |

Leave data-series colors (`#3b82f6`, `#22c55e`, `#ef4444`, `#a855f7`, crosshair colors, dive-phase colors) unchanged — those are intentional and read fine on both backgrounds. For `TrajectoryPlot.jsx` (3D `scene`), also set any `scene` axis `gridcolor`/`color`/`backgroundcolor` that use the dark literals to the mapped `theme.*` values; leave the 3D mesh colors unchanged.

- [ ] **Step 4: Manual verification**

Run: `cd frontend && npm run dev`
Expected: With a deployment loaded and an interval analyzed, toggle light mode → all 8 plots show white plot areas, dark axis text/grid; toggle dark → all revert. Open a plot's mode-bar camera/download (where available) in light mode and confirm a white (not transparent/black) background in the exported PNG.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/usePlotTheme.js frontend/src/components/plots/
git commit -m "feat(theme): theme-aware Plotly colors across all plots"
```

---

## Task 3: Spectrogram backend params (1024 FFT / 50% overlap)

**Files:**
- Modify: `backend/src/processing/spectrogram.py:119-131`
- Test: `backend/tests/test_spectrogram.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_spectrogram.py`:

```python
def test_detailed_spectrogram_uses_1024_fft():
    import numpy as np
    from scipy import signal
    from src.processing.spectrogram import compute_detailed_spectrogram

    sr = 48000
    audio = np.random.randn(sr).astype(np.float32)  # 1 second
    result = compute_detailed_spectrogram(audio, sr)

    # With nperseg=1024 the number of frequency bins is 1024//2 + 1 = 513
    expected_freqs = signal.spectrogram(audio, fs=sr, nperseg=1024, noverlap=512)[0]
    assert len(result["freqs"]) == len(expected_freqs) == 513
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_spectrogram.py::test_detailed_spectrogram_uses_1024_fft -v`
Expected: FAIL — current `nperseg=4096` yields 2049 freq bins, not 513.

- [ ] **Step 3: Change the detailed parameters**

In `backend/src/processing/spectrogram.py`, in `compute_detailed_spectrogram`, change lines 119-120:

```python
    # High resolution parameters: FFT 1024, 50% overlap
    nperseg = 1024
    noverlap = 512
```

- [ ] **Step 4: Run the spectrogram tests**

Run: `cd backend && pytest tests/test_spectrogram.py -v`
Expected: PASS (new test + existing ones; if an existing test hardcodes 4096-derived bin counts for the *detailed* function, update its expectation to the 1024 equivalent).

- [ ] **Step 5: Commit**

```bash
git add backend/src/processing/spectrogram.py backend/tests/test_spectrogram.py
git commit -m "feat(spectrogram): detailed FFT 1024 / 50% overlap"
```

---

## Task 4: Spectrogram frontend controls (dB contrast, colorscale, colorbar)

Add persisted spectrogram view settings and bind them to the heatmap.

**Files:**
- Modify: `frontend/src/stores/settingsStore.js`
- Modify: `frontend/src/components/plots/SpectrogramPlot.jsx`
- Modify: `frontend/src/components/Sidebar.jsx` (Settings section)

- [ ] **Step 1: Add spectrogram settings to the store**

In `frontend/src/stores/settingsStore.js`, add inside the store object (after `setTheme`):

```js
      spectrogram: { colorscale: 'Viridis', dbMin: null, dbMax: null },
      setSpectrogram: (patch) =>
        set((s) => ({ spectrogram: { ...s.spectrogram, ...patch } })),
```

(`dbMin`/`dbMax` `null` = auto from data percentiles.)

- [ ] **Step 2: Compute auto dB range + apply controls in SpectrogramPlot**

In `frontend/src/components/plots/SpectrogramPlot.jsx`:
1. Import the store: `import { useSettingsStore } from '../../stores/settingsStore'`
2. Read settings: `const { spectrogram } = useSettingsStore()`
3. Compute auto percentiles from `spec.power` when `dbMin/dbMax` are null:

```js
  const [autoMin, autoMax] = useMemo(() => {
    if (!spec?.power?.length) return [-100, -20]
    const flat = spec.power.flat().filter((v) => Number.isFinite(v))
    if (!flat.length) return [-100, -20]
    flat.sort((a, b) => a - b)
    const p = (q) => flat[Math.min(flat.length - 1, Math.floor(q * flat.length))]
    return [p(0.05), p(0.99)]
  }, [spec])
  const zmin = spectrogram.dbMin ?? autoMin
  const zmax = spectrogram.dbMax ?? autoMax
```

4. In the heatmap trace, set: `colorscale: spectrogram.colorscale`, `zmin`, `zmax`, `showscale: true`, and add `colorbar: { title: { text: 'dB', font: { size: 10, color: theme.axis } }, tickfont: { color: theme.axis }, thickness: 10 }`. Adjust `layout.margin.r` from `10` to `60` so the colorbar fits.
5. Add `spectrogram`, `zmin`, `zmax` to the `useMemo` deps.

- [ ] **Step 3: Add spectrogram controls to the Settings section in Sidebar**

In `frontend/src/components/Sidebar.jsx`, read from the store (extend the existing destructure on line 38): add `spectrogram, setSpectrogram`. Inside the Settings `<Section>` (after the Light-mode label, before `</Section>`), add:

```jsx
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
```

- [ ] **Step 4: Manual verification**

Run: `cd frontend && npm run dev`
Expected: With a spectrogram visible, a colorbar (dB) appears on the right. Changing colorscale updates colors live. Entering dB min/max tightens/loosens contrast; clearing the fields (`auto`) restores percentile-based range. Settings persist across reload.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/settingsStore.js frontend/src/components/plots/SpectrogramPlot.jsx frontend/src/components/Sidebar.jsx
git commit -m "feat(spectrogram): adjustable dB contrast, colorscale selector, colorbar"
```

---

## Task 5: Metadata parser (JSON + plain-text auto-detect)

**Files:**
- Create: `backend/src/processing/metadata_parser.py`
- Create: `backend/tests/test_metadata_parser.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_metadata_parser.py`:

```python
import json
import os
import tempfile
import pytest
from src.processing.metadata_parser import parse_metadata


def _write(tmpdir, name, content):
    path = os.path.join(tmpdir, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def test_parse_json_metadata():
    with tempfile.TemporaryDirectory() as tmp:
        data = {
            "title": "Sperm whale deployment - DP2",
            "animal_id": "SW_001",
            "species": "Physeter macrocephalus",
            "deployment_start": "2026-05-28T14:05:06.860Z",
            "deployment_end": "2026-05-28T18:42:10.120Z",
            "timezone": "UTC+2",
            "gps_track": [
                {"timestamp": "2026-05-28T14:10:00.000Z", "latitude": 43.12345, "longitude": 10.54321}
            ],
            "research_group": "Project Name / Institution",
            "notes": "Optional deployment notes",
            "additional_metadata": {"tag_model": "DTAG-X", "sampling_rate_audio": 192000, "sampling_rate_sensors": 400},
        }
        path = _write(tmp, "meta.json", json.dumps(data))
        result = parse_metadata(path)

    assert result["title"] == "Sperm whale deployment - DP2"
    assert result["species"] == "Physeter macrocephalus"
    assert result["timezone"] == "UTC+2"
    assert result["deployment_start"] == "2026-05-28T14:05:06.860Z"
    assert len(result["gps_track"]) == 1
    assert result["gps_track"][0]["latitude"] == 43.12345
    assert result["additional_metadata"]["sampling_rate_audio"] == 192000


def test_parse_text_metadata_dp1():
    text = """--- GENERAL INFO ---
Deployment ID:    pm20240701-CD3
Species:          Physeter macrocephalus
Project:	  DIVES \\ SZN
Notes:            Photogrammetry\\Biopsy\\Blow

--- DATE ---
Deployment Start: 2024-07-01 13:02:00.820 (YY:MM:DD HH:SS:MM.FFF)
Deployment End:   2024-07-01 21:21:48.620
Timezone:         UTC+2

--- GPS TRACK LOG --- Timestamp in Local Time
Point 1: (Tag On)
  Timestamp: 13:03:01.000
  Latitude:  37.1118
  Longitude: 15.3438
Point 2: (Surface 1)
  Timestamp: 13:55:43.000
  Latitude:  37.1228
  Longitude: 15.3351

--- ADDITIONAL METADATA ---
Tag Model:            CATS Diary CD3
Sampling Rate Audio:  192000 Hz
Sampling Rate Sensors:400 Hz
"""
    with tempfile.TemporaryDirectory() as tmp:
        path = _write(tmp, "DP1.txt", text)
        result = parse_metadata(path)

    assert result["deployment_id"] == "pm20240701-CD3"
    assert result["species"] == "Physeter macrocephalus"
    assert result["timezone"] == "UTC+2"
    assert result["deployment_start"] == "2024-07-01 13:02:00.820"
    assert result["deployment_end"] == "2024-07-01 21:21:48.620"
    assert len(result["gps_track"]) == 2
    assert result["gps_track"][0]["label"] == "Tag On"
    assert result["gps_track"][0]["timestamp"] == "13:03:01.000"
    assert result["gps_track"][0]["latitude"] == pytest.approx(37.1118)
    assert result["gps_track"][1]["longitude"] == pytest.approx(15.3351)
    assert result["additional_metadata"]["tag_model"] == "CATS Diary CD3"
    assert result["additional_metadata"]["sampling_rate_audio"] == 192000
    assert result["additional_metadata"]["sampling_rate_sensors"] == 400


def test_parse_partial_text_does_not_raise():
    with tempfile.TemporaryDirectory() as tmp:
        path = _write(tmp, "partial.txt", "--- GENERAL INFO ---\nSpecies: Orcinus orca\n")
        result = parse_metadata(path)
    assert result["species"] == "Orcinus orca"
    assert result["deployment_start"] is None
    assert result["gps_track"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_metadata_parser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.processing.metadata_parser'`.

- [ ] **Step 3: Implement the parser**

Create `backend/src/processing/metadata_parser.py`:

```python
"""Parse deployment metadata from either a JSON file or the plain-text
`--- SECTION ---` format. Both are normalized to one dict shape."""

import json
import re
from typing import Optional


def _num(value: str) -> Optional[float]:
    m = re.search(r"-?\d+\.?\d*", value or "")
    return float(m.group()) if m else None


def _empty() -> dict:
    return {
        "title": None,
        "deployment_id": None,
        "species": None,
        "project": None,
        "notes": None,
        "deployment_start": None,
        "deployment_end": None,
        "timezone": None,
        "gps_track": [],
        "additional_metadata": {
            "tag_model": None,
            "sampling_rate_audio": None,
            "sampling_rate_sensors": None,
        },
    }


def parse_metadata(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    if raw.lstrip().startswith("{"):
        try:
            return _normalize_json(json.loads(raw))
        except json.JSONDecodeError:
            pass
    return _parse_text(raw)


def _normalize_json(d: dict) -> dict:
    add = d.get("additional_metadata") or {}
    result = _empty()
    result.update({
        "title": d.get("title"),
        "deployment_id": d.get("deployment_id") or d.get("animal_id"),
        "species": d.get("species"),
        "project": d.get("research_group") or d.get("project"),
        "notes": d.get("notes"),
        "deployment_start": d.get("deployment_start"),
        "deployment_end": d.get("deployment_end"),
        "timezone": d.get("timezone"),
        "gps_track": [
            {
                "label": p.get("label"),
                "timestamp": p.get("timestamp"),
                "latitude": p.get("latitude"),
                "longitude": p.get("longitude"),
            }
            for p in (d.get("gps_track") or [])
        ],
        "additional_metadata": {
            "tag_model": add.get("tag_model"),
            "sampling_rate_audio": add.get("sampling_rate_audio"),
            "sampling_rate_sensors": add.get("sampling_rate_sensors"),
        },
    })
    return result


def _parse_text(raw: str) -> dict:
    result = _empty()
    current_point = None
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("---") or set(s) == {"="}:
            continue
        m = re.match(r"Point\s+\d+:\s*(?:\(([^)]*)\))?", s)
        if m:
            current_point = {
                "label": (m.group(1) or "").strip() or None,
                "timestamp": None,
                "latitude": None,
                "longitude": None,
            }
            result["gps_track"].append(current_point)
            continue
        if ":" not in s:
            continue
        key, _, value = s.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if key in ("deployment start", "deployment end"):
            value = re.split(r"\s+\(", value)[0].strip()

        if key == "deployment id":
            result["deployment_id"] = value
        elif key == "species":
            result["species"] = value
        elif key == "project":
            result["project"] = value
        elif key == "notes":
            result["notes"] = value
        elif key == "deployment start":
            result["deployment_start"] = value
        elif key == "deployment end":
            result["deployment_end"] = value
        elif key == "timezone":
            result["timezone"] = value
        elif key == "tag model":
            result["additional_metadata"]["tag_model"] = value
        elif key == "sampling rate audio":
            result["additional_metadata"]["sampling_rate_audio"] = _num(value)
        elif key == "sampling rate sensors":
            result["additional_metadata"]["sampling_rate_sensors"] = _num(value)
        elif key == "timestamp" and current_point is not None:
            current_point["timestamp"] = value
        elif key == "latitude" and current_point is not None:
            current_point["latitude"] = _num(value)
        elif key == "longitude" and current_point is not None:
            current_point["longitude"] = _num(value)
    return result
```

Note: the JSON test expects `sampling_rate_audio == 192000` (int from JSON, preserved as-is); the text test expects `192000` and `400` as floats — `192000.0 == 192000` and `400.0 == 400` are both `True` in Python, so the assertions hold.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_metadata_parser.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/src/processing/metadata_parser.py backend/tests/test_metadata_parser.py
git commit -m "feat(metadata): JSON + plain-text deployment metadata parser"
```

---

## Task 6: Upload endpoint — metadata file + event timestamps

**Files:**
- Modify: `backend/src/models.py:5-11`
- Modify: `backend/src/api/upload.py`
- Test: `backend/tests/test_upload.py`

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_upload.py` (inside `TestUploadEndpoint`):

```python
    def test_upload_carries_event_timestamps_and_metadata(self):
        client = TestClient(app)
        with tempfile.TemporaryDirectory() as tmpdir:
            sr = 16000
            wav_path = os.path.join(tmpdir, "a.wav")
            wavfile.write(wav_path, sr, np.random.randn(2000).astype(np.float32))

            prh = pd.DataFrame({
                "pitch_smoothed": [1.0, 2.0],
                "roll_smoothed_wrapped": [1.0, 2.0],
                "heading_smoothed_wrapped": [1.0, 2.0],
                "depth_smoothed": [1.0, 2.0],
                "speed_smoothed": [0.1, 0.2],
                "Gy_Filt": [0.1, 0.2],
            })
            prh_path = os.path.join(tmpdir, "p.csv")
            prh.to_csv(prh_path, index=False)

            events = pd.DataFrame({
                "Deployment_ID": ["dep_ts"],
                "Type": ["creak"],
                "Start_duration_timestamp": ["13:14:17.304000"],
                "End_duration_timestamp": ["13:14:24.291000"],
                "Mean_duration_timestamp": ["13:14:20.797"],
                "DN_start_idx": [0],
                "DN_end_idx": [1],
            })
            events_path = os.path.join(tmpdir, "e.csv")
            events.to_csv(events_path, index=False)

            meta_path = os.path.join(tmpdir, "meta.txt")
            with open(meta_path, "w") as f:
                f.write("--- DATE ---\nDeployment Start: 2024-07-01 13:02:00.820\nTimezone: UTC+2\n")

            with open(wav_path, "rb") as wf, open(prh_path, "rb") as pf, \
                 open(events_path, "rb") as ef, open(meta_path, "rb") as mf:
                response = client.post(
                    "/api/upload",
                    files={
                        "wav_file": ("a.wav", wf, "audio/wav"),
                        "prh_csv": ("p.csv", pf, "text/csv"),
                        "events_csv": ("e.csv", ef, "text/csv"),
                        "metadata_file": ("meta.txt", mf, "text/plain"),
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["events"][0]["start_ts"] == "13:14:17.304000"
        assert data["events"][0]["mean_ts"] == "13:14:20.797"
        assert data["metadata"]["deployment_start"] == "2024-07-01 13:02:00.820"
        assert data["metadata"]["timezone"] == "UTC+2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_upload.py::TestUploadEndpoint::test_upload_carries_event_timestamps_and_metadata -v`
Expected: FAIL — `metadata_file` not accepted / `start_ts` and `metadata` absent.

- [ ] **Step 3: Update the response model**

In `backend/src/models.py`, add to `UploadResponse` (and ensure `Optional` is imported — it is, line 2):

```python
class UploadResponse(BaseModel):
    session_id: str
    message: str
    deployment_id: str
    duration_seconds: float
    spectrogram_preview: Dict[str, Any]
    events: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None
```

- [ ] **Step 4: Accept the metadata file and carry timestamps in `upload.py`**

In `backend/src/api/upload.py`:
1. Add import near the others: `from src.processing.metadata_parser import parse_metadata`
2. Add the optional parameter to the endpoint signature (after `events_csv`):

```python
    events_csv: UploadFile = File(...),
    metadata_file: UploadFile = File(None),
```

3. After saving the events file (after line 58), parse metadata if present:

```python
    metadata = None
    if metadata_file is not None:
        meta_path = os.path.join(temp_dir, metadata_file.filename)
        await _save_upload(metadata_file, meta_path)
        try:
            metadata = parse_metadata(meta_path)
        except Exception as e:  # never fail upload on bad metadata
            print(f"Warning: metadata parse failed: {e}")
            metadata = None
```

4. Replace the events-conversion loop (lines 112-119) with one that carries timestamps:

```python
    events_list = []
    for _, row in events_df.iterrows():
        events_list.append({
            "type": row.get("Type", "unknown"),
            "start_idx": int(row.get("DN_start_idx", 0)),
            "end_idx": int(row.get("DN_end_idx", 0)),
            "start_ts": (str(row["Start_duration_timestamp"])
                         if "Start_duration_timestamp" in events_df.columns else None),
            "end_ts": (str(row["End_duration_timestamp"])
                       if "End_duration_timestamp" in events_df.columns else None),
            "mean_ts": (str(row["Mean_duration_timestamp"])
                        if "Mean_duration_timestamp" in events_df.columns else None),
        })
```

5. Store metadata in the session dict (add `"metadata": metadata,` to `_session_data[session_id]`).
6. Add `metadata=metadata,` to the `UploadResponse(...)` return.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_upload.py -v`
Expected: PASS — new test passes and the two existing tests still pass (metadata is optional; `start_ts` etc. are `None` when columns absent).

- [ ] **Step 6: Commit**

```bash
git add backend/src/models.py backend/src/api/upload.py backend/tests/test_upload.py
git commit -m "feat(upload): optional metadata file + event timestamp passthrough"
```

---

## Task 7: Frontend folder upload (auto-detect) + metadata in store

**Files:**
- Modify: `frontend/src/stores/deploymentStore.js:11-36`
- Modify: `frontend/src/components/Sidebar.jsx` (Upload section + `handleUpload`)

- [ ] **Step 1: Let the store's `upload` accept an optional metadata file**

In `frontend/src/stores/deploymentStore.js`, change the `upload` signature and body:

```js
  upload: async (wavFile, prhCsv, eventsCsv, metadataFile = null) => {
    set({ isLoading: true, error: null })
    try {
      const formData = new FormData()
      formData.append('wav_file', wavFile)
      formData.append('prh_csv', prhCsv)
      formData.append('events_csv', eventsCsv)
      if (metadataFile) formData.append('metadata_file', metadataFile)

      const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Upload failed')
      }
      const data = await res.json()
      set({ deployment: data, isLoading: false })
      return data
    } catch (err) {
      set({ error: err.message, isLoading: false })
      throw err
    }
  },
```

- [ ] **Step 2: Add folder auto-detect to the Upload section in Sidebar**

In `frontend/src/components/Sidebar.jsx`:
1. Add state near the other `useState` calls (top of component):

```js
  const [detected, setDetected] = useState({ wav: null, prh: null, events: null, metadata: null })
```

2. Add a folder-input handler (place beside `handleUpload`):

```js
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
```

3. At the very top of the existing Upload `<Section>` content (before the manual `<label>`s), add the folder picker + detected mapping + upload button:

```jsx
          <label htmlFor="folder-input" className="block text-xs text-muted-foreground">Upload deployment folder</label>
          <input
            id="folder-input"
            type="file"
            webkitdirectory=""
            directory=""
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
```

(`webkitdirectory` / `directory` are non-standard React attributes; in JSX, `webkitdirectory=""` renders the attribute. If React strips it, set it via a ref in a `useEffect`: `folderRef.current?.setAttribute('webkitdirectory', '')`.)

4. Leave the existing 3 manual file inputs and the existing "Upload Files" button below as the fallback path.

- [ ] **Step 3: Manual verification**

Run: `cd frontend && npm run dev`
Expected: In Upload, "Upload deployment folder" lets you pick a folder; the detected WAV/PRH/Events/Metadata names appear; "Upload folder" is enabled only when WAV+PRH+Events are present; uploading a folder that includes a metadata `.txt`/`.json` loads the deployment and (Task 9) shows metadata in Statistics. The manual 3-input path still works.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/stores/deploymentStore.js frontend/src/components/Sidebar.jsx
git commit -m "feat(upload): folder picker with file auto-detection + metadata"
```

---

## Task 8: Flexible time display (s / mm:ss / hh:mm:ss / absolute)

**Files:**
- Modify: `frontend/src/lib/utils.js`
- Modify: `frontend/src/stores/settingsStore.js`
- Modify: `frontend/src/components/Sidebar.jsx` (Settings: time-format selector)
- Modify: `frontend/src/components/Timeline.jsx`

- [ ] **Step 1: Add `formatTime` to utils**

Append to `frontend/src/lib/utils.js`:

```js
// Format an elapsed-seconds value according to the chosen mode.
// mode: 'seconds' | 'mmss' | 'hms' | 'absolute'
// deploymentStart: ISO-ish string (from metadata) used only for 'absolute'.
export function formatTime(seconds, mode = 'seconds', deploymentStart = null) {
  const s = Number.isFinite(seconds) ? seconds : 0
  if (mode === 'seconds') return `${s.toFixed(1)}s`
  if (mode === 'mmss') {
    const m = Math.floor(s / 60)
    const rem = s - m * 60
    return `${m}:${rem.toFixed(1).padStart(4, '0')}`
  }
  if (mode === 'hms') {
    const h = Math.floor(s / 3600)
    const m = Math.floor((s % 3600) / 60)
    const sec = Math.floor(s % 60)
    return `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  }
  if (mode === 'absolute') {
    const base = parseDeploymentStart(deploymentStart)
    if (!base) {
      // no anchor → fall back to hh:mm:ss elapsed
      return formatTime(s, 'hms')
    }
    const d = new Date(base.getTime() + s * 1000)
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    const ss = String(d.getSeconds()).padStart(2, '0')
    return `${hh}:${mm}:${ss}`
  }
  return `${s.toFixed(1)}s`
}

// Accept ISO ("2026-05-28T14:05:06.860Z") or "YYYY-MM-DD HH:MM:SS.mmm".
function parseDeploymentStart(value) {
  if (!value) return null
  let v = String(value).trim()
  if (v.includes(' ') && !v.includes('T')) v = v.replace(' ', 'T')
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? null : d
}
```

- [ ] **Step 2: Add `timeFormat` to the settings store**

In `frontend/src/stores/settingsStore.js`, add inside the store object:

```js
      timeFormat: 'seconds',
      setTimeFormat: (f) => set({ timeFormat: f }),
```

- [ ] **Step 3: Add a time-format selector to Settings in Sidebar**

In `frontend/src/components/Sidebar.jsx`, extend the settings destructure (line 38) with `timeFormat, setTimeFormat`, and inside the Settings `<Section>` add:

```jsx
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
```

(`deployment` is already destructured from `useDeploymentStore` at line 34.)

- [ ] **Step 4: Use `formatTime` in the Timeline readouts**

In `frontend/src/components/Timeline.jsx`:
1. Add imports: `import { formatTime } from '../lib/utils'` and `import { useSettingsStore } from '../stores/settingsStore'`.
2. Read: `const { timeFormat } = useSettingsStore()` and `const deploymentStart = deployment?.metadata?.deployment_start || null`.
3. Replace the scrubber readouts (lines 28-30 and 41-43):
   - current time span: `{formatTime(currentTime, timeFormat, deploymentStart)}`
   - interval duration span: `{formatTime(intervalDuration, timeFormat, deploymentStart)}`
4. Leave the numeric interval Start/End inputs as seconds (editing stays in seconds); the unit toggle is Phase 2.

- [ ] **Step 5: Manual verification**

Run: `cd frontend && npm run dev`
Expected: Changing "Time display" updates the scrubber readouts: `12.0s` → `0:12.0` → `0:00:12` → (with metadata loaded) clock time like `13:02:12`. Without metadata, "Absolute clock time" is disabled.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/utils.js frontend/src/stores/settingsStore.js frontend/src/components/Sidebar.jsx frontend/src/components/Timeline.jsx
git commit -m "feat(time): flexible time display (seconds/mm:ss/hh:mm:ss/absolute)"
```

---

## Task 9: Statistics panel shows deployment metadata

**Files:**
- Modify: `frontend/src/components/plots/StatsPanel.jsx`

- [ ] **Step 1: Render metadata block above the computed stats**

In `frontend/src/components/plots/StatsPanel.jsx`:
1. Read metadata: change line 32 to also pull `deployment`:

```js
  const { analysisData, deployment } = useDeploymentStore()
  const meta = deployment?.metadata
```

2. Move the early `if (!s)` return so it does NOT short-circuit when metadata exists. Replace the render body so the metadata block shows whenever `meta` is present, even before analysis. Concretely, change the `if (!s) return (...)` block (lines 61-67) to:

```js
  if (!s && !meta) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        Run analysis to see statistics
      </div>
    )
  }
```

3. At the top of the returned `<div className="p-3 ...">` content (before the computed-stats grid), add a metadata section that renders only when `meta` exists:

```jsx
        {meta && (
          <div className="mb-3 pb-2 border-b border-border">
            <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">Deployment</div>
            {meta.title && <Row label="Title" value={meta.title} tip="Deployment title" />}
            {meta.deployment_id && <Row label="ID" value={meta.deployment_id} tip="Deployment ID" />}
            {meta.species && <Row label="Species" value={meta.species} tip="Species" />}
            {meta.project && <Row label="Project" value={meta.project} tip="Project / institution" />}
            {meta.deployment_start && <Row label="Start" value={meta.deployment_start} tip="Deployment start" />}
            {meta.deployment_end && <Row label="End" value={meta.deployment_end} tip="Deployment end" />}
            {meta.timezone && <Row label="Timezone" value={meta.timezone} tip="Local timezone" />}
            {meta.additional_metadata?.tag_model && <Row label="Tag" value={meta.additional_metadata.tag_model} tip="Tag model" />}
            {meta.additional_metadata?.sampling_rate_audio != null && <Row label="Audio SR" value={meta.additional_metadata.sampling_rate_audio} unit="Hz" tip="Audio sampling rate" />}
            {meta.additional_metadata?.sampling_rate_sensors != null && <Row label="Sensor SR" value={meta.additional_metadata.sampling_rate_sensors} unit="Hz" tip="Sensor sampling rate" />}
            {meta.gps_track?.length > 0 && <Row label="GPS points" value={meta.gps_track.length} tip="Number of GPS fixes in metadata" />}
            {meta.notes && <Row label="Notes" value={meta.notes} tip="Deployment notes" />}
          </div>
        )}
```

4. Wrap the existing computed-stats grid so it only renders when `s` is truthy: `{s && (<div className="grid grid-cols-1 gap-0"> ... existing rows ... </div>)}`.

- [ ] **Step 2: Manual verification**

Run: `cd frontend && npm run dev`
Expected: After a folder upload that includes metadata, the Statistics panel shows a "Deployment" block (ID, species, start/end, timezone, tag, sampling rates, GPS point count) even before analysis; after analyzing an interval the computed stats appear below it. With no metadata, behavior is unchanged.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/plots/StatsPanel.jsx
git commit -m "feat(stats): show parsed deployment metadata in Statistics panel"
```

---

## Task 10: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update feature/workflow/data sections**

In `README.md`:
1. In **Workflow** (around line 73), update the persisted-settings line to note theme now switches the whole UI and plots (light mode functional), plus persisted spectrogram view + time-format settings.
2. In **Feature overview → Visual analysis**, add a bullet: spectrogram now has adjustable dB contrast, selectable colorscale, and a colorbar.
3. Add a bullet on flexible time display (seconds / mm:ss / hh:mm:ss / absolute clock time when metadata provides a start time).
4. In **Data inputs** (the table around lines 171-176), add a row for the optional metadata file:

```
| metadata (`.json` / `.txt`) | Deployment metadata: start/end, timezone, GPS track, tag info | optional |
```

5. In **Workflow → Drag-and-drop upload** (line 65), note that a whole deployment folder can be selected and files are auto-detected, with manual selection as a fallback.

- [ ] **Step 2: Verify the doc reads correctly**

Run: `grep -n "metadata" README.md`
Expected: the new metadata input row and folder-upload mention are present.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: README for light mode, spectrogram, time display, folder upload"
```

---

## Final verification

- [ ] **Backend regression:** `cd backend && pytest -v` → all tests pass (existing 60+ plus new spectrogram, metadata_parser, upload tests).
- [ ] **Frontend smoke:** `cd frontend && npm run dev` → load a deployment (folder with metadata), toggle light/dark across all panels, adjust spectrogram dB/colorscale, cycle time-format modes, confirm Statistics shows metadata.

---

## Self-review notes (coverage vs spec)

- Light mode → Tasks 1, 2. Spectrogram (FFT + dB + colorscale) → Tasks 3, 4. Event timestamps + metadata backend → Tasks 5, 6. Flexible time display → Task 8. Folder upload + auto-detect + metadata → Task 7. Statistics metadata → Task 9. README → Task 10.
- Deferred items (PRH ±180°, event SS.FF + same-line timestamp, button color states, bigger 3D marker, acoustic events on 3D, big features) are intentionally NOT in this plan (Phases 2/3).
- Type/name consistency: response field `metadata` (Task 6) is read as `deployment.metadata` in Tasks 7/8/9; event fields `start_ts`/`end_ts`/`mean_ts` (Task 6) are produced once and not consumed in Phase 1 UI (same-line display is Phase 2) — they are carried now so Phase 2 needs no backend change.
