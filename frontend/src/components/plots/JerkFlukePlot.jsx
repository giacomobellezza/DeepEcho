import React, { useMemo } from 'react'
import Plot from 'react-plotly.js'
import { useDeploymentStore } from '../../stores/deploymentStore'
import { useSyncedPlotly } from '../../hooks/useSyncedPlotly'
import { detectPreyCaptures } from '../../lib/preyDetection'
import { usePlotTheme } from '../../hooks/usePlotTheme'

export default function JerkFlukePlot() {
  const { analysisData } = useDeploymentStore()
  const { plotRef, onHover, onRelayout, currentTime, xRange } = useSyncedPlotly()
  const theme = usePlotTheme()

  const { data, layout } = useMemo(() => {
    if (!analysisData?.jerk?.length) return { data: [], layout: {} }
    const n = analysisData.jerk.length
    const duration = (analysisData.end_idx - analysisData.start_idx) / 10 || n / 10
    const times = Array.from({ length: n }, (_, i) => (i / n) * duration)

    const jerk = analysisData.jerk
    const pcaIdx = detectPreyCaptures(jerk)
    const pcaTimes = pcaIdx.map((i) => times[i])
    const pcaVals = pcaIdx.map((i) => jerk[i])

    return {
      data: [
        {
          type: 'scatter', mode: 'lines', x: times, y: analysisData.jerk,
          name: 'Jerk', line: { color: '#f59e0b', width: 1.5 }, yaxis: 'y',
          hovertemplate: 'Time: %{x:.2f}s<br>Jerk: %{y:.3f}<extra>Jerk</extra>',
        },
        {
          type: 'scatter', mode: 'lines', x: times, y: analysisData.fluke_stroke,
          name: 'Fluke Stroke', line: { color: '#06b6d4', width: 1.5 }, yaxis: 'y2',
          hovertemplate: 'Time: %{x:.2f}s<br>Fluke: %{y:.3f}<extra>Fluke</extra>',
        },
        {
          type: 'scatter', mode: 'markers', x: pcaTimes, y: pcaVals,
          name: `Prey capture (${pcaIdx.length})`,
          marker: { color: '#ef4444', size: 9, symbol: 'x', line: { width: 1.5 } },
          hovertemplate: 'Time: %{x:.2f}s<br>Jerk: %{y:.2f}<extra>Prey capture</extra>',
        },
      ],
      layout: {
        xaxis: {
          title: { text: 'Time (s)', font: { size: 10, color: theme.axis } },
          color: theme.axis, gridcolor: theme.grid,
          ...(xRange ? { range: xRange } : {}),
        },
        yaxis: {
          title: { text: 'Jerk', font: { size: 10, color: '#f59e0b' } },
          color: '#f59e0b', gridcolor: theme.grid,
        },
        yaxis2: {
          title: { text: 'Fluke Stroke', font: { size: 10, color: '#06b6d4' } },
          color: '#06b6d4', overlaying: 'y', side: 'right',
        },
        margin: { t: 10, b: 40, l: 50, r: 50 },
        paper_bgcolor: theme.paper,
        plot_bgcolor: theme.plot,
        legend: {
          x: 0.5, y: 1.05, xanchor: 'center', orientation: 'h',
          font: { size: 10, color: theme.axis }, bgcolor: 'rgba(0,0,0,0)',
        },
        showlegend: true,
        shapes: currentTime > 0 ? [{
          type: 'line', x0: currentTime, x1: currentTime, y0: 0, y1: 1,
          yref: 'paper', line: { color: '#a855f7', width: 1.5, dash: 'dot' },
        }] : [],
      },
    }
  }, [analysisData, currentTime, xRange, theme])

  if (!analysisData?.jerk?.length) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        Run analysis to see jerk &amp; fluke stroke
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
