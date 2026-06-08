import React, { useMemo } from 'react'
import Plot from 'react-plotly.js'
import { useDeploymentStore } from '../../stores/deploymentStore'
import { useSettingsStore } from '../../stores/settingsStore'
import { useSyncedPlotly } from '../../hooks/useSyncedPlotly'
import { usePlotTheme } from '../../hooks/usePlotTheme'

export default function SpectrogramPlot() {
  const { deployment, analysisData } = useDeploymentStore()
  const { spectrogram } = useSettingsStore()
  const { plotRef, onHover, onRelayout, currentTime, xRange } = useSyncedPlotly()
  const theme = usePlotTheme()

  const spec = analysisData?.spectrogram || deployment?.spectrogram_preview

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

  const { data, layout } = useMemo(() => {
    if (!spec?.power?.length) return { data: [], layout: {} }
    return {
      data: [
        {
          type: 'heatmap',
          z: spec.power,
          x: spec.times || [],
          y: spec.freqs || [],
          colorscale: spectrogram.colorscale,
          zmin,
          zmax,
          showscale: true,
          colorbar: {
            title: { text: 'dB', font: { size: 10, color: theme.axis } },
            tickfont: { color: theme.axis },
            thickness: 10,
          },
          hovertemplate: 'Time: %{x:.2f}s<br>Freq: %{y:.0f}Hz<br>Power: %{z:.1f}dB<extra></extra>',
        },
      ],
      layout: {
        xaxis: {
          title: { text: 'Time (s)', font: { size: 10, color: theme.axis } },
          color: theme.axis,
          gridcolor: theme.grid,
          ...(xRange ? { range: xRange } : {}),
        },
        yaxis: {
          title: { text: 'Frequency (Hz)', font: { size: 10, color: theme.axis } },
          color: theme.axis,
          gridcolor: theme.grid,
        },
        margin: { t: 10, b: 40, l: 50, r: 60 },
        paper_bgcolor: theme.paper,
        plot_bgcolor: theme.plot,
        shapes: currentTime > 0 ? [{
          type: 'line',
          x0: currentTime, x1: currentTime, y0: 0, y1: 1,
          yref: 'paper',
          line: { color: '#ef4444', width: 1.5, dash: 'dot' },
        }] : [],
      },
    }
  }, [spec, currentTime, xRange, theme, spectrogram, zmin, zmax])

  if (!spec?.power?.length) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        No spectrogram data
      </div>
    )
  }

  return (
    <Plot
      ref={plotRef}
      data={data}
      layout={layout}
      config={{ responsive: true, displayModeBar: false }}
      onHover={onHover}
      onRelayout={onRelayout}
      useResizeHandler
      style={{ width: '100%', height: '100%' }}
    />
  )
}
