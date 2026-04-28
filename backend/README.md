# DeepEcho — Backend

FastAPI service that ingests bio-logging deployments (WAV + PRH CSV + Events CSV),
pre-computes motion metrics, and serves analysis slices to the React frontend.

Designed for **multi-gigabyte audio**: nothing is fully loaded into RAM. WAV files are
streamed to disk on upload and re-read with `soundfile.seek()` for any subsequent slice;
PRH metrics are pre-computed once per deployment and held in an in-memory singleton cache.

---

## Stack

| Layer            | Library                       |
|------------------|-------------------------------|
| Web framework    | FastAPI ≥ 0.104               |
| ASGI server      | Uvicorn (`[standard]`) ≥ 0.24 |
| Numerics         | NumPy ≥ 1.24, SciPy ≥ 1.11    |
| Audio I/O        | SoundFile ≥ 0.12              |
| CSV / DataFrames | pandas ≥ 1.5                  |
| Multipart upload | python-multipart ≥ 0.0.6      |
| Tests            | pytest ≥ 7.4 + pytest-asyncio |

Python ≥ **3.11** required (uses `tuple[ndarray, int]` typing, modern annotations).

---

## Running

### Local

```bash
cd backend
pip install -e ".[dev]"
uvicorn src.main:app --reload --port 8000
```

Swagger UI: <http://localhost:8000/docs>
Health:    <http://localhost:8000/health>

### Docker

`Dockerfile` uses `python:3.11-slim`, installs the package editable, runs uvicorn with `--reload`.
Bind-mounted in `docker-compose.yml` so source edits hot-reload.

---

## Module map

```
src/
├── main.py                  # FastAPI app, CORS (allow_origins=*), router wiring
├── models.py                # Pydantic schemas (UploadResponse, AnalyzeRequest/Response, …)
│
├── api/
│   ├── upload.py            # POST /api/upload          — ingest deployment
│   ├── preview.py           # GET  /api/preview/:id     — duration + events
│   ├── analyze.py           # POST /api/analyze         — interval analysis bundle
│   ├── trajectory.py        # POST /api/trajectory      — dead-reckoned 3D path
│   └── audio_stream.py      # GET  /api/audio/:id       — stream WAV slice
│
├── processing/
│   ├── wav_loader.py        # get_wav_info, read_wav_slice, load_wav (legacy)
│   ├── prh_parser.py        # parse_prh_csv, extract_prh_slice, compute_jerk, compute_fluke_stroke
│   ├── spectrogram.py       # compute_preview / compute_detailed / sample_spectrogram
│   └── metrics.py           # compute_jerk (PRH-style), compute_prh_metrics, compute_trajectory
│
└── cache/
    └── session_cache.py     # DeploymentMetrics + SpectrogramCache + SessionCache (singleton)
```

`api/upload.py` owns the global session map (`_session_data`); other API modules import it to
look up `wav_path`, `sr`, `prh_data`, `deployment_id` by `deployment_id`.

---

## HTTP API

All routes are mounted under `/api`. Request/response shapes live in `src/models.py`.

### `POST /api/upload`

Multipart form fields: `wav_file`, `prh_csv`, `events_csv`.

Pipeline:
1. Generate `session_id` (UUID4), create temp dir under `tempfile.gettempdir()`.
2. Stream each upload to disk in **8 MB chunks** (`_save_upload`) — never buffer full file.
3. `get_wav_info()` → `sample_rate`, `frames`, `duration_seconds` (no audio in RAM).
4. `parse_prh_csv()` → DataFrame.
5. Pre-compute jerk via `processing.metrics.compute_jerk(ax, ay, az, hz=10)`.
6. Resolve `deployment_id` from events CSV (`Deployment_ID` col) or fallback to
   `session_<uuid8>`.
7. `SessionCache.load_deployment(...)` stores `prh_data`, `acceleration` (N, 3), `jerk`, `hz=10`.
8. Compute a **preview spectrogram** from the first ≤ 30 s, downsample to 64×64, store in
   `SpectrogramCache` keyed by `deployment_id`.
9. Cache session metadata (paths, sr, total_frames, events list) in `_session_data`.

Response (`UploadResponse`):
```json
{
  "session_id": "uuid",
  "deployment_id": "pm240701-CD3",
  "duration_seconds": 3600.0,
  "spectrogram_preview": { "freqs": [...], "times": [...], "power": [[...]] },
  "events": [{ "type": "creak", "start_idx": 7366, "end_idx": 7436 }, …]
}
```

### `GET /api/preview/{deployment_id}`

Returns `{ deployment_id, duration_seconds, events }` — used by the frontend to repopulate
event navigation without re-uploading.

> Note: the lookup uses the deployment id as the session-map key; the upload route stores by
> `session_id`, so this route is currently a "second-chance" fallback. Most reads happen via
> the analyze/trajectory routes, which iterate `_session_data.values()` and match on
> `deployment_id`.

### `POST /api/analyze`

Body: `{ deployment_id, start_idx, end_idx }` (PRH-frame indices, 10 Hz).

Pipeline:
1. Find session by `deployment_id`.
2. `SessionCache.extract_interval()` — clamps indices, returns
   `(prh_slice: DataFrame, accel_slice: (M,3), jerk_slice: (M,))`.
3. Convert PRH indices to audio samples: `start_sample = start_idx * sr / 10`.
4. `read_wav_slice()` reads only the requested window directly from disk via `sf.seek`.
5. Min/max-envelope downsample audio to ≤ **2000 points** (preserves peaks → critical for
   visual click detection).
6. **Spectrogram cache lookup** at resolution 256×256 keyed by
   `(deployment_id, start_idx, end_idx, resolution)`. Miss → compute high-resolution
   spectrogram (`nperseg=4096, noverlap=2048`), bin-average to 256×256, linspace freq/time
   axes, store.
7. Extract pitch / roll / heading / depth / speed / `Gy_Filt` columns from the slice.
8. Compute fluke stroke = `|Gy_Filt|`, plus mean-centred `fluke_stroke_normalized`.
9. **Dynamic body acceleration** with a 3-second running-mean high-pass:
   - `dax = ax - rolling_mean(ax, 30)`, same for y, z
   - `ODBA = |dax| + |day| + |daz|`
   - `VeDBA = √(dax² + day² + daz²)`
   - `MSA = √(ax² + ay² + az²) − 1` (gravity-removed magnitude)
10. Return everything in a single JSON bundle (`AnalyzeResponse`).

### `POST /api/trajectory`

Body: `{ deployment_id, start_idx, end_idx }`.

Computes 3D dead-reckoned path from the cached PRH slice:

```
dt   = 1 / hz                            # 0.1 s
ds   = speed_smoothed * dt
hr   = -deg2rad(heading_smoothed_wrapped) # negate to align E=0°, N=90°
pr   =  deg2rad(pitch_smoothed)
dx   = cumsum(ds * cos(hr) * cos(pr))
dy   = cumsum(ds * sin(hr) * cos(pr))
dz   = depth_smoothed
```

Returns `{ dx: [...], dy: [...], dz: [...] }` in metres.

### `GET /api/audio/{deployment_id}?start_idx=…&end_idx=…`

Reads the requested PRH-index window from disk, encodes as 16-bit PCM WAV in-memory, and
returns it as `audio/wav` for `<audio>` / Web Audio API consumption. Indices are converted
to audio samples via `start_sample = start_idx * sr / 10`.

### `GET /health`

`{ "status": "ok" }`. Used by docker-compose / k8s liveness.

---

## Processing modules

### `processing/wav_loader.py`

- `get_wav_info(path)` → metadata only via `sf.info()` (no audio decoded).
- `read_wav_slice(path, start, end)` → opens with `sf.SoundFile`, `seek(start)`,
  `read(end-start, dtype='float32')`. Stereo is downmixed to mono via `mean(axis=1)`.
  **Bounds are clamped** so out-of-range requests degrade gracefully.

### `processing/prh_parser.py`

- `parse_prh_csv(path)` — `pd.read_csv` with `FileNotFoundError` / `ValueError` guards.
- `extract_prh_slice()` — column-name flexible (accepts both raw and `_smoothed` suffixes).
  Returns a dict of NumPy arrays keyed by canonical names.
- `compute_jerk(ax, ay, az, sample_rate=10)` — a **second** jerk implementation (returns a
  list, omits the leading zero, uses `diff/dt`). Kept for legacy callers; the canonical
  one for the upload pipeline is `processing.metrics.compute_jerk`.
- `compute_fluke_stroke(gy)` → `abs(gy)`.

### `processing/spectrogram.py`

- `compute_preview_spectrogram(audio, sr, resolution='low'|'medium'|'high')`
  - low: `nperseg=1024, noverlap=512`
  - medium: `nperseg=2048, noverlap=1024`
  - high: `nperseg=4096, noverlap=2048`
  - Decimates to ~50 freq bins / ~100 time bins for the preview.
- `compute_detailed_spectrogram(audio, sr)` — `nperseg=4096, noverlap=2048`, full output.
- `sample_spectrogram(power, target_freq_bins, target_time_bins)` — bin-mean downsample
  to an exact target size. Used at 64×64 (preview) and 256×256 (analysis).

All power is converted to dB: `10 · log10(Sxx + 1e-10)`.

### `processing/metrics.py`

- `compute_jerk(ax, ay, az, hz=10)` — implements the MATLAB
  `[0; sqrt(sum(diff(Aw_raw).^2, 2)) * hz]` formula. Output length matches input; first
  element is always `0.0`.
- `compute_prh_metrics(df)` — pulls canonical `_smoothed` columns from a DataFrame;
  raises `KeyError` listing missing columns.
- `compute_trajectory(speed, heading, pitch, depth, hz=10)` — see formula above.
  Returns a dict of NumPy arrays.

---

## Caching

```
SessionCache (singleton, get_session_cache)
├── _cache:              { deployment_id → DeploymentMetrics(prh_data, accel, jerk, hz) }
└── _spectrogram_cache:  { deployment_id → SpectrogramCache(freqs, times, power, res, start, end) }
```

- **DeploymentMetrics**: full PRH + accel + jerk for the *entire* deployment, sliced on
  demand by `extract_interval(start, end)` (indices clamped to `[0, len)`, swapped if
  inverted).
- **SpectrogramCache**: stores **one** spectrogram per deployment. The `get()` lookup
  requires an exact `(start_idx, end_idx, resolution)` match — no LRU, no overlap detection.
  Sufficient because the frontend tends to re-request the same interval.
- **`_session_data`** (in `api/upload.py`) is a separate dict that holds file paths and
  raw metadata; it is the source of truth for "what file is on disk for this deployment?"

`get_cache()` is re-exported from `cache.__init__` and is an alias for `get_session_cache`,
so `analyze.py` and `upload.py` refer to the same singleton.

> ⚠️ Caches are **process-local** and live in RAM. Restarting uvicorn forgets every session.

---

## Pydantic models (`models.py`)

| Model               | Purpose                                              |
|---------------------|------------------------------------------------------|
| `UploadResponse`    | What `/upload` returns                               |
| `PreviewResponse`   | What `/preview/:id` returns                          |
| `AnalyzeRequest`    | `deployment_id, start_idx, end_idx`                  |
| `AnalyzeResponse`   | Full analysis bundle: spectrogram, audio, prh, derived metrics |
| `TrajectoryRequest` | Same shape as `AnalyzeRequest`                       |
| `TrajectoryResponse`| `{ dx, dy, dz }` lists                               |

Lists are float64 unless noted; the frontend treats every numeric array as `number[]`.

---

## Performance characteristics

| Operation                    | Cost                                        |
|------------------------------|---------------------------------------------|
| Upload (1 GB WAV)            | I/O bound (8 MB chunks); preview spec ≤ 30 s |
| `read_wav_slice` (any size)  | One `seek` + linear read of slice only       |
| Analyze with cache hit       | ~10 ms (slice + serialize)                   |
| Analyze with cache miss      | Spectrogram FFT dominates (256 ms / s of audio at 192 kHz typical) |
| Trajectory                   | Pure NumPy on 10 Hz arrays — milliseconds    |
| `/audio/:id`                 | Slice read + `sf.write` to BytesIO          |

Frontend long-poll / streaming is not used — all responses are single JSON / WAV blobs.

---

## Testing

```bash
cd backend
pytest -v                      # full suite
pytest tests/test_metrics.py   # one module
pytest -k jerk                 # one keyword
```

Suite covers:

| File                       | What                                                        |
|----------------------------|-------------------------------------------------------------|
| `test_wav_loader.py`       | `get_wav_info`, slice bounds, mono/stereo handling          |
| `test_prh_parser.py`       | column-mapping flexibility, missing-column errors           |
| `test_spectrogram.py`      | preview / detailed / `sample_spectrogram` shape correctness |
| `test_metrics.py`          | jerk formula, trajectory cumulative integration             |
| `test_session_cache.py`    | load / extract / clamp / spectrogram cache key match        |
| `test_upload.py`           | multipart upload path                                       |
| `test_analyze.py`          | analyze endpoint with cached session                        |
| `test_integration.py`      | end-to-end upload → analyze → trajectory                    |

> 60+ tests as of v1; see `DEVELOPMENT.md` for changelog.

---

## Conventions & gotchas

- **Index space**: PRH indices are at **10 Hz**. Audio samples = `prh_idx * sr / 10`.
  Always convert at the boundary; never mix the two.
- **CORS**: wide open (`allow_origins=["*"]`). Tighten in production.
- **Sessions**: keyed by `deployment_id`, looked up by linear scan of `_session_data.values()`
  in `analyze.py` / `trajectory.py` / `audio_stream.py`. Acceptable for single-user dev,
  swap for a dict-of-deployment-ids in multi-tenant setups.
- **Memory ceiling**: the in-memory `prh_data` (a pandas DataFrame) is the hard ceiling;
  for an hour-long deployment that's ~36 000 rows × ~20 cols — negligible. The expensive
  thing is the WAV, which is intentionally never loaded.
- **`/api/preview/:id` lookup mismatch**: the route uses the deployment id as the dict key,
  but `_session_data` is keyed by `session_id`. Frontend currently relies on the upload
  response and `/analyze` instead, so this hasn't surfaced. Fix when wiring multi-deployment
  flows.

---

## Roadmap (backend-side)

See [`../DEVELOPMENT.md`](../DEVELOPMENT.md) for the full picture. Backend-relevant items:

- [ ] Persistent cache (Redis / SQLite) so restarts don't drop sessions.
- [ ] Streaming spectrogram (chunk → FFT → emit) for > 60-min deployments.
- [ ] WebSocket push for long analyses (currently synchronous).
- [ ] Move `/api/preview` to look up by deployment id consistently.
- [ ] Calibration factor support (µPa conversion) per CATS toolbox metadata.
