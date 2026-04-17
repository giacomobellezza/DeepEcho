# Data Structure - DeepEcho Tag Data

Documentazione della struttura dei dati da dispositivi bio-logging utilizzati in DeepEcho.

## Overview

I dati sono organizzati in tre file principali per deployment:

1. **AllSignals_DP*.csv** - Metadata degli eventi acustici
2. **pm*_10Hzprh_smoothed.csv** - Dati locomotori e orientamento (10 Hz)
3. **Audio WAV** - File audio grezzo dall'idrofono

---

## 1. AllSignals_DP*.csv

**Descrizione**: Lista degli eventi acustici rilevati durante il deployment.

**Colonne**:
- `Deployment_ID`: ID del tag (es. pm240701-CD3)
- `Start_duration_timestamp`: Timestamp inizio evento (HH:MM:SS.ms)
- `End_duration_timestamp`: Timestamp fine evento
- `Mean_duration_timestamp`: Timestamp medio evento
- `Type`: Tipo di evento
  - `regular_click`: Click regolare
  - `creak`: Vocalizzo di creaking (importante per analisi comportamento)
  - `whoosh`: Suono di trasferimento vocale
  - `pause`: Pausa tra sequenze
- `DN_start_idx`: Indice inizio evento (nel PRH dataset a 10 Hz)
- `DN_end_idx`: Indice fine evento
- `DN_mean_idx`: Indice medio

**Uso nel sistema**:
- Definisce gli intervalli di analisi (user seleziona un creak/click per analizzare)
- Sincronizza con l'audio WAV e i dati PRH attraverso timestamp/indici

**Esempio**:
```
pm240701-CD3,13:14:17.304000,13:14:24.291000,13:14:20.797,creak,7366,7436,7401
```

---

## 2. pm*_10Hzprh_smoothed.csv

**Descrizione**: Dati locomotori e sensoriali campionati a 10 Hz. Versione "smoothed" (filtrata/levigata).

**Sampling**: 10 Hz (un campione ogni 100 ms)

**Colonne** (18 sensori):

### Locomotion & Orientation
- `speed_smoothed`: Velocità stimata (m/s)
- `depth`: Profondità istantanea (m)
- `depth_smoothed`: Profondità filtrata (m)
- `pitch_smoothed`: Inclinazione longitudinale (gradi, -180 a 180)
- `roll_smoothed`: Inclinazione laterale (gradi)
- `heading_smoothed`: Rotta/direzione (gradi, 0-360)
- `roll_smoothed_wrapped`: Roll "wrapped" (angoli continui)
- `heading_smoothed_wrapped`: Heading "wrapped"
- `pitch_stroke`: Componente di stroke del pitch (movimento flutto)

### IMU - Accelerometro (m/s²)
- `Ax_Filt`, `Ay_Filt`, `Az_Filt`: Accelerazione X, Y, Z (filtrata)

### IMU - Magnetometro (µT)
- `Mx_Filt`, `My_Filt`, `Mz_Filt`: Campo magnetico X, Y, Z (filtrato)

### IMU - Giroscopio (rad/s)
- `Gx_Filt`, `Gy_Filt`, `Gz_Filt`: Velocità angolare X, Y, Z (filtrata)

**Uso nel sistema**:
- **Plot 1 (Depth & Speed)**: Usa `depth_smoothed` e `speed_smoothed`
- **Plot 2 (PRH)**: Usa `pitch_smoothed`, `roll_smoothed_wrapped`, `heading_smoothed_wrapped`
- **Plot 3 (Jerk & Fluke)**: Calcola jerk da accelerometro; usa `Gy_Filt` per fluke stroke
- **3D Trajectory** (fase 2): Integra velocità + heading per posizione XYZ

**Indici e Timestamp**:
- Ogni riga = 100 ms
- Indice N = timestamp N * 0.1 secondi
- Sincronizzato con AllSignals_DP*.csv tramite DN_start_idx/DN_end_idx

---

## 3. Audio WAV

**Descrizione**: File audio grezzo dall'idrofono montato sul tag.

**Formato**: WAV stereo/mono, sample rate varia (tipicamente 192 kHz or 250 kHz)

**Uso nel sistema**:
- **Spettrogramma**: FFT su segmenti audio per visualizzare frequenza nel tempo
- **Sincronizzazione**: Allineato con PRH data tramite timestamp di inizio deployment

**Calibrazione**: 
- Usa fattore di calibrazione per convertire in pressione acustica (µPa)
- Nella versione MATLAB: `calib_factor = 10^(-165/20)` (tag-specific)

---

## 4. Dati Grezzi (Phase 2)

Nel MATLAB script, vengono caricati anche:
- `StructDP*.mat`: Struct MATLAB con dati acustici elaborati (AOL, peak-to-peak, etc.)
- `pm*_10Hzprh.mat`: Versione raw (non smoothed) del PRH

**Fase 1**: Non necessitiamo di questi (useremo dati già puliti CSV)
**Fase 2**: Possiamo parsare i .mat per automatizzare preprocessing

---

## File di Calibrazione (CATS Toolbox)

- `.cal`: File di calibrazione (binario, specifico del tag)
- `.csv`: Dati di calibrazione in formato testuale
- `.cfg`, `.ini`: Configurazione
- `.ubx`: Raw GNSS data (opzionale)

**Uso**: Non necessario per fase 1 (assumiamo dati già calibrati nei CSV)

---

## Naming Convention

```
pm<YYYYMMDD>-<TAG_ID>_10Hz<variant>.<ext>
```

Esempio:
- `pm240701-CD3_10Hzprh_smoothed.csv` → 2024-07-01, tag CD3, dati PRH smoothed
- `pm240716-CD3_10Hzprh.mat` → 2024-07-16, tag CD3, dati PRH raw

---

## Alignment & Synchronization

### Timeline Unificata
- **Ancor**: WAV file start time (es. 13:02:00.820 nel MATLAB script)
- **Indici**: PRH data è sempre 10 Hz → indice N = N * 100 ms da start
- **Events**: AllSignals usa same timeline

### Mapping
```
Audio timestamp T_wav 
  ↓
PRH index N = T_wav * 10 Hz
  ↓
AllSignals DN_start_idx = same N
```

---

## Formato Nuovo (.mat → Custom JSON/HDF5)

**Fase 2**: Rimpiazzare .mat binaries con:
- **JSON** per piccoli dataset (metadata, events)
- **HDF5** per time-series numeriche (migliore performance)

Esempio struttura:
```json
{
  "metadata": {
    "deployment_id": "pm240701-CD3",
    "tag_type": "CATS",
    "start_time": "2024-07-01T13:02:00.820Z",
    "duration_seconds": 3600,
    "calibration_factor": 0.0003162
  },
  "sensors": {
    "prh": "path/to/data.h5",
    "audio": "path/to/audio.wav"
  }
}
```

---

## Data Quality Notes

- **Smoothed vs Raw**: Dati smoothed hanno filter applicato (migliore per visualizzazione)
- **Missing values**: CSV ha 0.0 all'inizio del deployment (tag in superficie); non sono true measurements
- **Timestamp alignment**: Attenzione ai millisecondi quando sincronizzi WAV + PRH

---

## References

- CATS Toolbox documentation: `/risorse/Dynamic Plot Tag Data/CATS Toolbox/CATS Visualizer v1.1.30 instructions.pdf`
- MATLAB script: `/Matlab Script/DynamicPlot_Script.m` (vedere sezioni preprocessing)
- AnimalTags.org metrics: https://animaltags.org/biologging-tools-project/metrics-computation/
