import React, { useMemo } from 'react'
import Plot from 'react-plotly.js'
import { useDeploymentStore } from '../../stores/deploymentStore'
import { useSyncedPlotly } from '../../hooks/useSyncedPlotly'

export default function DepthSpeedPlot() {
  const { analysisData } = useDeploymentStore()
  const { plotRef, onHover, onRelayout, currentTime, xRange } = useSyncedPlotly()

  const { data, layout } = useMemo(() => {
    if (!analysisData?.depth?.length) return { data: [], layout: {} }
    const n = analysisData.depth.length
    const duration = (analysisData.end_idx - analysisData.start_idx) / 10 || n / 10
    const times = Array.from({ length: n }, (_, i) => (i / n) * duration)

    return {
      data: [
        {
          type: 'scatter', mode: 'lines', x: times, y: analysisData.depth,
          name: 'Depth', line: { color: '#3b82f6', width: 1.5 }, yaxis: 'y',
          hovertemplate: 'Time: %{x:.2f}s<br>Depth: %{y:.1f}m<extra>Depth</extra>',
        },
        {
          type: 'scatter', mode: 'lines', x: times, y: analysisData.speed,
          name: 'Speed', line: { color: '#ef4444', width: 1.5 }, yaxis: 'y2',
          hovertemplate: 'Time: %{x:.2f}s<br>Speed: %{y:.2f}m/s<extra>Speed</extra>',
        },
      ],
      layout: {
        xaxis: {
          title: { text: 'Time (s)', font: { size: 10, color: '#a1a1aa' } },
          color: '#a1a1aa', gridcolor: '#27272a',
          ...(xRange ? { range: xRange } : {}),
        },
        yaxis: {
          title: { text: 'Depth (m)', font: { size: 10, color: '#3b82f6' } },
          color: '#3b82f6', gridcolor: '#27272a', autorange: 'reversed',
        },
        yaxis2: {
          title: { text: 'Speed (m/s)', font: { size: 10, color: '#ef4444' } },
          color: '#ef4444', overlaying: 'y', side: 'right',
        },
        margin: { t: 10, b: 40, l: 50, r: 50 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: '#09090b',
        legend: {
          x: 0.5, y: 1.05, xanchor: 'center', orientation: 'h',
          font: { size: 10, color: '#a1a1aa' }, bgcolor: 'rgba(0,0,0,0)',
        },
        showlegend: true,
        shapes: currentTime > 0 ? [{
          type: 'line', x0: currentTime, x1: currentTime, y0: 0, y1: 1,
          yref: 'paper', line: { color: '#a855f7', width: 1.5, dash: 'dot' },
        }] : [],
      },
    }
  }, [analysisData, currentTime, xRange])

  if (!analysisData?.depth?.length) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        Run analysis to see depth &amp; speed
      </div>
    )
  }

  return (
    <Plot
      ref={plotRef}
      data={data} layout={layout}
      config={{ responsive: true, displayModeBar: false }}
      onHover={onHover} onRelayout={onRelayout}
      useResizeHandler style={{ width: '100%', height: '100%' }}
    />
  )
}
