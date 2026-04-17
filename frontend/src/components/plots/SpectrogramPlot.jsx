import React, { useMemo } from 'react'
import Plot from 'react-plotly.js'
import { useDeploymentStore } from '../../stores/deploymentStore'
import { useSyncedPlotly } from '../../hooks/useSyncedPlotly'

export default function SpectrogramPlot() {
  const { deployment, analysisData } = useDeploymentStore()
  const { plotRef, onHover, onRelayout, currentTime, xRange } = useSyncedPlotly()

  const spec = analysisData?.spectrogram || deployment?.spectrogram_preview

  const { data, layout } = useMemo(() => {
    if (!spec?.power?.length) return { data: [], layout: {} }
    return {
      data: [
        {
          type: 'heatmap',
          z: spec.power,
          x: spec.times || [],
          y: spec.freqs || [],
          colorscale: 'Viridis',
          showscale: false,
          hovertemplate: 'Time: %{x:.2f}s<br>Freq: %{y:.0f}Hz<br>Power: %{z:.1f}dB<extra></extra>',
        },
      ],
      layout: {
        xaxis: {
          title: { text: 'Time (s)', font: { size: 10, color: '#a1a1aa' } },
          color: '#a1a1aa',
          gridcolor: '#27272a',
          ...(xRange ? { range: xRange } : {}),
        },
        yaxis: {
          title: { text: 'Frequency (Hz)', font: { size: 10, color: '#a1a1aa' } },
          color: '#a1a1aa',
          gridcolor: '#27272a',
        },
        margin: { t: 10, b: 40, l: 50, r: 10 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: '#09090b',
        shapes: currentTime > 0 ? [{
          type: 'line',
          x0: currentTime, x1: currentTime, y0: 0, y1: 1,
          yref: 'paper',
          line: { color: '#ef4444', width: 1.5, dash: 'dot' },
        }] : [],
      },
    }
  }, [spec, currentTime, xRange])

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
