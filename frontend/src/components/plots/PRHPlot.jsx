import React, { useMemo } from 'react'
import Plot from 'react-plotly.js'
import { useDeploymentStore } from '../../stores/deploymentStore'
import { useSyncedPlotly } from '../../hooks/useSyncedPlotly'
import { usePlotTheme } from '../../hooks/usePlotTheme'

export default function PRHPlot() {
  const { analysisData } = useDeploymentStore()
  const { plotRef, onHover, onRelayout, currentTime, xRange } = useSyncedPlotly()
  const theme = usePlotTheme()

  const { data, layout } = useMemo(() => {
    if (!analysisData?.pitch?.length) return { data: [], layout: {} }
    const n = analysisData.pitch.length
    const duration = (analysisData.end_idx - analysisData.start_idx) / 10 || n / 10
    const times = Array.from({ length: n }, (_, i) => (i / n) * duration)

    return {
      data: [
        {
          type: 'scatter', mode: 'lines', x: times, y: analysisData.pitch,
          name: 'Pitch', line: { color: '#3b82f6', width: 1.5 },
          hovertemplate: 'Time: %{x:.2f}s<br>Pitch: %{y:.1f}&deg;<extra>Pitch</extra>',
        },
        {
          type: 'scatter', mode: 'lines', x: times, y: analysisData.roll,
          name: 'Roll', line: { color: '#22c55e', width: 1.5 },
          hovertemplate: 'Time: %{x:.2f}s<br>Roll: %{y:.1f}&deg;<extra>Roll</extra>',
        },
        {
          type: 'scatter', mode: 'lines', x: times, y: analysisData.heading,
          name: 'Heading', line: { color: '#ef4444', width: 1.5 },
          hovertemplate: 'Time: %{x:.2f}s<br>Heading: %{y:.1f}&deg;<extra>Heading</extra>',
        },
      ],
      layout: {
        xaxis: {
          title: { text: 'Time (s)', font: { size: 10, color: theme.axis } },
          color: theme.axis, gridcolor: theme.grid,
          ...(xRange ? { range: xRange } : {}),
        },
        yaxis: {
          title: { text: 'Degrees', font: { size: 10, color: theme.axis } },
          color: theme.axis, gridcolor: theme.grid, range: [-180, 180],
        },
        margin: { t: 10, b: 40, l: 50, r: 10 },
        paper_bgcolor: theme.paper,
        plot_bgcolor: theme.plot,
        legend: {
          x: 0.5, y: 1.05, xanchor: 'center', orientation: 'h',
          font: { size: 10, color: theme.axis }, bgcolor: 'rgba(0,0,0,0)',
        },
        showlegend: true,
        shapes: [
          { type: 'line', x0: 0, x1: 1, y0: 0, y1: 0,
            xref: 'paper', line: { color: theme.zeroLine, width: 1, dash: 'dash' } },
          ...(currentTime > 0 ? [{
            type: 'line', x0: currentTime, x1: currentTime, y0: 0, y1: 1,
            yref: 'paper', line: { color: '#a855f7', width: 1.5, dash: 'dot' },
          }] : []),
        ],
      },
    }
  }, [analysisData, currentTime, xRange, theme])

  if (!analysisData?.pitch?.length) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        Run analysis to see PRH data
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
