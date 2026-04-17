# DeepEcho — Cetacean Acoustic Tracking Dashboard

Interactive platform for analyzing cetacean behavior from bio-logging tags. Synchronize streaming audio, 3D orientation (PRH), motion metrics, and behavioral events across six interactive visualizations. Automatically detect prey capture events and explore multi-gigabyte deployments in real time. Built with React + Plotly.js (frontend) and FastAPI (backend).

Developed by **Associazione Cecilia Bellezza**.

## Features

- **Dashboard Grid**: Drag-and-drop resizable panels (react-grid-layout)
- **6 Chart Types**: Spectrogram, Depth/Speed, PRH (Pitch/Roll/Heading), Jerk/Fluke Stroke, 3D Trajectory, Waveform
- **3D Cetacean Mesh**: Countershaded mesh with species-specific profiles, oriented by PRH data
- **Prey Capture Detection**: Jerk-based detection (mean + 3σ) with 3D markers
- **Synchronized Crosshair**: Hover on any chart → all charts update
- **Streaming WAV**: Handles multi-GB audio files without loading into RAM
- **Event Navigation**: Click acoustic events to jump to interval and analyze
- **Dark Theme**: Optimized for spectrogram contrast

## Quick Start

### Docker

```bash
git clone <repo>
docker-compose up
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/docs

### Local Dev

**Backend**:
```bash
cd backend
pip install -e .
uvicorn src.main:app --reload
```

**Frontend**:
```bash
cd frontend
npm install
npm run dev
```

### Tests

```bash
cd backend && pytest tests/ -v
```

## Data Format

| File | Description |
|------|-------------|
| `*.wav` | Hydrophone audio (mono/stereo) |
| `*_10Hzprh_smoothed.csv` | PRH motion data at 10 Hz (depth, speed, pitch, roll, heading, accelerometer, gyroscope) |
| `AllSignals_DP*.csv` | Acoustic events (creaks, clicks) with sample indices |

See [docs/DATA_STRUCTURE.md](docs/DATA_STRUCTURE.md) for detailed format specs.

## Architecture

```
Frontend (React + Plotly.js + Zustand)     Backend (FastAPI + NumPy + SoundFile)
  ├─ Dashboard grid (react-grid-layout)      ├─ Streaming WAV upload/read
  ├─ 6 plot components (Plotly)              ├─ Spectrogram (FFT + sampling)
  ├─ 3D cetacean mesh (mesh3d)               ├─ Trajectory (dead reckoning)
  ├─ Zustand stores (state sync)             ├─ PRH metrics (jerk, ODBA, VeDBA)
  └─ Tailwind CSS (dark theme)               └─ Session cache
```

## References

- [AnimalTags.org — Metrics](https://animaltags.org/biologging-tools-project/metrics-computation/)
- [CATS Toolbox](https://animaltags.org/biologging-tools-project/cats-tag/)

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
