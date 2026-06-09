# DeepEcho — Presentazione

**Piattaforma web per analisi comportamento cetacei da tag bio-logging.**
Sincronizza audio idrofono multi-GB con orientamento 3D (PRH), profondità, velocità,
accelerometro. Sviluppato per Associazione Cecilia Bellezza. Stack: FastAPI + NumPy / React + Plotly.js + Zustand.

---

## 1. Problema & motivazione

Tag bio-logging registrano ore di dati multi-sensore per deployment: WAV idrofono >1 GB a 192–250 kHz, CSV PRH 10 Hz (pitch/roll/heading/depth/speed/IMU), CSV eventi acustici (click, creak, whoosh). Biologi marini devono ispezionare intervalli brevi (un creak, una cattura preda) sincronizzati su audio + movimento + posizione 3D. Workflow MATLAB esistente è potente ma lento, mono-macchina, non condivisibile. DeepEcho trasforma deployment in dashboard browser navigabile.

**Q1: Perché non rifare in MATLAB?**
MATLAB licenza chiusa, single-user, no condivisione browser, no streaming WAV. DeepEcho gira in browser (zero install lato utente), backend FastAPI deployabile come servizio, frontend persistente con localStorage. Plus: stack Python/JS aperto = community più ampia.

**Q2: Perché 10 Hz per PRH e non sample rate audio?**
PRH viene già pre-filtrato dal toolbox CATS a 10 Hz (un sample/100 ms). Sufficiente per movimento (pitch/roll/heading cambiano lentamente vs audio). Audio resta a sample rate nativo (192 kHz). Conversione boundary: `audio_sample = prh_idx * sr / 10`.

**Q3: Quanto è grande tipico deployment?**
WAV 1–5 GB (ore audio 192 kHz), CSV PRH 36 000 righe/ora × 18 colonne (~10 MB), eventi ~100–1000 righe. Bottleneck = WAV. Soluzione: mai caricare full WAV in RAM, usare `soundfile.seek()` per slice O(1) memoria.

---

## 2. Architettura generale

Monorepo: `backend/` (FastAPI) + `frontend/` (React/Vite) + `docs/` + `risorse/` (riferimenti MATLAB). Docker compose per dev. Vite dev proxy `/api → backend:8000`.

**Q1: Perché due servizi separati e non un solo monolite?**
Separazione concerns: backend = numerica pesante (NumPy/SciPy/SoundFile, FFT, cache), frontend = rendering interattivo (Plotly, WebGL). Linguaggi specializzati. Permette scalare indipendentemente (frontend statico su CDN, backend GPU/multi-worker se serve). Plus: frontend testabile senza Python.

**Q2: Perché Zustand invece di Redux/Context?**
Bundle minore (~1 KB), API minimale (zero boilerplate), selettori granulari → re-render isolati. Esempio: panel Pitch/Roll legge solo `s.analysisData.pitch`, hover su altro panel non lo ri-renderizza. Redux Toolkit overkill per stato locale UI; Context API forza re-render di tutto il sub-tree.

**Q3: CORS aperto in produzione è sicuro?**
No. `allow_origins=["*"]` è dev-only. In prod restringere a dominio frontend. Inoltre sessioni in-memory (process-local) → crashano al restart uvicorn. Per multi-tenant: aggiungere Redis/SQLite per persistenza, auth header, rate limiting.

---

## 3. Dati di input

Tre file per deployment: `*.wav` (idrofono mono/stereo), `pm*_10Hzprh_smoothed.csv` (PRH 10 Hz, 18 colonne), `AllSignals_DP*.csv` (eventi tipizzati con `DN_start_idx`/`DN_end_idx` in spazio PRH).

**Q1: Cosa succede se manca colonna nel CSV PRH?**
`processing/prh_parser.py::extract_prh_slice` usa column-mapping flessibile: accetta varianti (`roll`, `roll_smoothed`, `roll_smoothed_wrapped`). Se nessuna trovata → `KeyError` con elenco colonne disponibili. Backend richiede minimo: `pitch_smoothed`, `roll_smoothed_wrapped`, `heading_smoothed_wrapped`, `depth_smoothed`, `speed_smoothed`, `Ax/Ay/Az_Filt`, `Gy_Filt`.

**Q2: Stereo come gestito?**
`wav_loader.read_wav_slice` legge con `dtype='float32'`, se `audio.ndim > 1` fa downmix mono via `mean(axis=1)`. Idrofoni cetacei spesso mono o due canali quasi identici → mean accettabile. Per analisi spaziale (TDOA tra canali) servirebbe pipeline separata.

**Q3: Come allineati WAV ed eventi?**
Eventi usano `DN_start_idx`/`DN_end_idx` in spazio PRH (10 Hz). Frontend riceve come `start_idx`/`end_idx`. Conversione audio: `start_sample = prh_idx * sr / 10`. Allineamento garantito dal toolbox CATS upstream (entrambi ancorati a timestamp inizio deployment).

---

## 4. Backend — FastAPI

`src/main.py` monta 5 router sotto `/api`: upload, preview, analyze, trajectory, audio_stream. Pydantic in `models.py`. Processing in `src/processing/` (wav_loader, prh_parser, spectrogram, metrics). Cache singleton in `src/cache/`.

**Q1: Come gestito upload di file >1 GB senza saturare RAM?**
`api/upload.py::_save_upload` legge `UploadFile` in chunk da 8 MB e scrive su disco temporaneo. Mai `await upload.read()` su tutto il file. Dopo: `get_wav_info()` legge solo header (sample_rate, frames, duration) via `sf.info()` — zero audio decodificato. Audio caricato solo per preview spettrogramma 30 s.

**Q2: Cache miss su `/analyze` quanto costa?**
Spettrogramma dominante: `scipy.signal.spectrogram` con `nperseg=4096, noverlap=2048` su slice da N secondi a 192 kHz → ~256 ms per secondo audio. Poi `sample_spectrogram` bin-mean a 256×256 = ~50 ms. Hit successivo = ~10 ms (lookup dict + serializzazione JSON). Cache key = `(deployment_id, start_idx, end_idx, resolution)`.

**Q3: Come computati ODBA / VeDBA / MSA?**
Filtro high-pass via running-mean 3 secondi (window=30 sample a 10 Hz):
```
dax = ax - convolve(ax, ones(30)/30, mode='same')
ODBA  = |dax| + |day| + |daz|
VeDBA = sqrt(dax² + day² + daz²)
MSA   = sqrt(ax² + ay² + az²) - 1.0       # rimuove gravità
```
Standard AnimalTags.org. Convolve è O(N) — su 600 sample (60 s) trascurabile.

---

## 5. Frontend — React + Plotly

App.jsx = shell (theme, shortcuts). Sidebar = upload/eventi/settings. DashboardGrid = 9 panel via `react-grid-layout`. Timeline = scrubber + interval inputs. HoverReadout = stat live al cursore. Quattro store Zustand: deployment, timeline, layout (persisted), settings (persisted).

**Q1: Come fatto rendering 9 chart senza lag?**
Tre tecniche combinate:
1. Selettori granulari Zustand: ogni panel sottoscrive solo slice che gli serve.
2. `useMemo` su `data`/`layout` Plotly: ricomputo solo se dipendenze cambiano.
3. `scattergl` (WebGL) per waveform — 2000 punti @ 60 fps.
Hover su un chart triggera re-render solo dei chart che dipendono da `currentTime`.

**Q2: Cosa fa `useSyncedPlotly`?**
Hook condiviso: ritorna `{plotRef, onHover, onRelayout, currentTime, xRange}`.
- `onHover` → legge `event.points[0].x`, scrive in `timelineStore.currentTime` → tutti chart mostrano linea verticale tratteggiata sincronizzata.
- `onRelayout` → legge `xaxis.range[0/1]`, scrive in `xRange` → tutti chart applicano stesso zoom.
- **Guard feedback loop**: confronta nuovo range con `xRangeRef.current` con epsilon 1e-6, salta scrittura se uguale. Senza, oscillazione infinita relayout→setState→relayout.
- ResizeObserver su `.react-grid-item` → fire `window.resize` event → Plotly `useResizeHandler` rescala.

**Q3: Come fatto auto-load demo file al mount?**
`Sidebar.jsx` ha `useEffect` che fa `Promise.all([fetch('/audio_demo.wav'), fetch('/prh_demo.csv'), fetch('/events_demo.csv')])`, costruisce `File` da blob, chiama `upload()`. 404 silenziati con try/catch. File vivono in `frontend/public/` → serviti staticamente da Vite.

---

## 6. Visualizzazione 3D — Cetacean mesh

`lib/cetaceanMesh.js` genera trace Plotly `mesh3d` runtime. Sei profili specie (sperm, fin, humpback, blue, orca, dolphin) con proporzioni custom. No GLTF, no asset esterni — pura geometria procedurale.

**Q1: Perché mesh procedurale e non modello 3D pre-fatto?**
Tre ragioni:
1. Bundle: GLTF/loader costerebbero MB, mesh JS ~10 KB.
2. Customizzabilità: cambiare specie = swap profilo, no re-export modello.
3. Plotly nativo: `mesh3d` integrato col resto della scena (scatter3d path), no Three.js extra.
Trade-off: aspetto stilizzato non foto-realistico. Accettabile per analisi scientifica (orientamento >> dettaglio).

**Q2: Come orientato il mesh per pitch/roll/heading?**
Eulero ZYX (roll → pitch → heading) applicato a ogni vertice. Body frame: x=naso(+)/coda(-), y=sx(+)/dx(-), z=dorso(+)/ventre(-). Dopo rotazione: body z **negato** per convertire da "dorso su" a "depth giù" (mondo). Convenzione coerente con `compute_trajectory` backend dove `dz = depth_smoothed`.

**Q3: Cos'è il countershading?**
Coloritura naturale cetacei: dorso scuro, ventre chiaro (camouflage da predatori sopra/sotto). Implementato con `lerpColor(ventral, dorsal, factor)` per vertice, dove `factor` deriva da `bodyZ` (z body-frame): vertici dorso → dorsalColor, ventre → ventralColor. Profilo `orca` = nero/bianco netto, `humpback` = grigio/bianco, etc.

---

## 7. Sync crosshair & zoom condivisi

Stato condiviso: `timelineStore.currentTime` (secondi) + `timelineStore.xRange` ([min, max] o null). Tutti i chart time-axis applicano `range: xRange` se non null, e shape `line` verticale a `currentTime`.

**Q1: Perché conversione `index → time` ovunque?**
Plotly time-axis gestisce naturalmente secondi (uniforme tra tutti i chart: spettrogramma, depth, PRH, jerk, waveform). Indici PRH (10 Hz) sono dominio backend; UI sempre in secondi relativi all'intervallo analizzato. Conversione: `time = (i / N) * duration` dove `duration = (end_idx - start_idx) / 10`.

**Q2: Come funziona "Reset sync" (tasto R)?**
Setta `xRange = null`. Tutti i chart in `useMemo` rimuovono il `range` esplicito → Plotly torna ad autorange. Hover handler ignorato perché reset zoom non triggera relayout sintetico. Anche `xaxis.autorange=true` nel relayout event resetta `xRange` a null (caso utente double-click su chart).

**Q3: Trajectory 3D partecipa al sync?**
Sì ma asimmetricamente. Non emette hover/zoom (asse non-time). Consuma `currentTime`: calcola `currentIdx = floor((currentTime/duration) * N)` per posizionare mesh cetaceo lungo path. Re-render via `useMemo([trajectoryData, currentTime, ...])`.

---

## 8. Performance & caching

Tre layer cache: in-memory backend `SessionCache` (DeploymentMetrics + SpectrogramCache), localStorage frontend (layout + settings), Vite browser cache (asset statici). Pattern: pre-compute heavy una volta, slice on-demand.

**Q1: Cosa contiene `SessionCache`?**
Singleton Python con due dict:
```
_cache:              { deployment_id → DeploymentMetrics(prh_data, accel, jerk, hz) }
_spectrogram_cache:  { deployment_id → SpectrogramCache(freqs, times, power, res, start, end) }
```
`extract_interval(start, end)` clampa indici e ritorna slice DataFrame + array. `SpectrogramCache.get()` richiede match esatto `(start, end, resolution)` — no LRU. Sufficiente perché frontend tende a ri-richiedere stesso intervallo.

**Q2: Limite memoria backend?**
`prh_data` DataFrame = ceiling effettivo. 1 ora deployment = 36 000 righe × ~20 col float64 ≈ 5 MB → trascurabile. WAV intenzionalmente mai caricato. SpectrogramCache 256×256 float = 256 KB per deployment. Singolo processo regge centinaia di deployment in RAM.

**Q3: Come downsample waveform preserva picchi?**
Min/max envelope: chunk = `N / (max_points/2)`, per ogni chunk push `min` poi `max`. 2000 punti finali = 1000 coppie min/max. Critico per click acustici brevi: media o decimazione semplice li perderebbe; min/max li preserva entrambi (positivo e negativo). Implementato in `api/analyze.py::downsample_waveform`.

---

## 9. Testing

`backend/tests/` con pytest, 60+ test, 8 file. Frontend zero test automatici (iterazione visuale via dev server).

**Q1: Cosa coperto dai test?**
- `test_wav_loader.py`: bound clamping, mono/stereo, file mancante.
- `test_prh_parser.py`: column-mapping flessibile, missing column error.
- `test_spectrogram.py`: shape low/medium/high, sample_spectrogram size esatta.
- `test_metrics.py`: formula jerk (primo elemento 0, lunghezza match), trajectory cumsum.
- `test_session_cache.py`: load/extract/clamp, spec cache key match.
- `test_upload.py`/`test_analyze.py`: endpoint con mock multipart.
- `test_integration.py`: end-to-end upload→analyze→trajectory.

**Q2: Come testare frontend?**
Niente Vitest/Jest configurato. Strategia attuale: dev server + ispezione visiva. Per aggiungere: Vitest (compatibile Vite) + React Testing Library per componenti, Playwright per E2E. Priorità: `useSyncedPlotly` (logica feedback-loop), `diveDetect`, `preyDetection`, `cetaceanMesh` (rotazioni Euler).

**Q3: Test integrazione richiede WAV reale?**
Sì. Test usa fixture WAV piccolo (<1 s) sintetico generato runtime con `numpy` + `soundfile.write`. Stesso pattern per CSV PRH (DataFrame creato in fixture). Non dipende da file demo reali, gira in CI senza setup.

---

## 10. Deployment & dev workflow

Docker compose dev: backend con `--reload`, frontend `npm run dev`. Volumi montati per hot reload. Variabili: `BACKEND_PORT` (8000), `FRONTEND_PORT` (3000), `VITE_API_TARGET`, `PYTHONUNBUFFERED`.

**Q1: Come deploy in produzione?**
Frontend: `npm run build` → `dist/` statico → CDN (Cloudflare Pages, Netlify, S3+CloudFront). Backend: `uvicorn` con `--workers N` dietro reverse proxy (nginx/Caddy). TLS upstream. Variabile `VITE_API_TARGET` punta al backend pubblico. Da fare prima: stringere CORS, aggiungere auth, persistenza cache.

**Q2: Sessioni multi-utente?**
Attualmente process-local. Opzioni:
1. **Sticky session** + Redis: ogni utente sempre stesso worker, Redis condivide cache.
2. **Stateless full**: spostare `_session_data` + `SessionCache` su Redis/SQLite, recuperare ad ogni request.
3. **Session token**: aggiungere header `X-Session-ID`, namespace cache per token.
Opzione 2 più pulita ma costa: serializzare DataFrame Pandas → Parquet o Arrow.

**Q3: Come scalare per WAV >5 GB / sessione >1 h?**
Backend: streaming spectrogram (chunk → FFT → emit progressivo via SSE/WebSocket). Frontend: lazy load panels (intersection observer), virtualize event list. Backend persistente: cache su disco (LMDB/Parquet) per sopravvivere restart. Worker process-pool per FFT pesanti (concurrent.futures).

---

## 11. Roadmap

Phase 3 (in corso): polish & ottimizzazione. Lista da `DEVELOPMENT.md`.

**Q1: Cosa manca per v2?**
- Filtraggio avanzato eventi (tipo, soglie metriche).
- Batch analysis (più intervalli insieme).
- Audio playback con cursore live sul waveform (parzialmente done).
- Tool misurazione (distanza su depth, angolo su trajectory).
- Annotation marker eventi comportamentali.
- Layout responsive mobile.
- ARIA label review accessibilità.

**Q2: Limiti noti?**
- Sessioni ~60 min max (memoria limited, no streaming).
- Chart export statici (no animazione).
- Mesh trajectory ruota in screen space, non world space.
- Waveform parte solo da inizio sezione analizzata.
- `/api/preview/:id` lookup mismatch (key session_id vs deployment_id).

**Q3: Estensione naturale per v3?**
- ML detection: classificatore acustico (CNN su spettrogramma) per auto-tag eventi.
- Confronto multi-deployment (overlay metriche tra animali).
- GIS layer (mappa GPS reale invece di dead reckoning).
- Calibrazione µPa per analisi quantitativa intensità click.
- Export PDF report (HTML→PDF via Playwright).
- Collaborazione: annotation condivise, commenti su intervalli.

---

Fine presentazione. Sezioni: 11 · Q&A: 33.
