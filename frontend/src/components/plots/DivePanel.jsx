import React, { useMemo } from 'react'
import Plot from 'react-plotly.js'
import { useDeploymentStore } from '../../stores/deploymentStore'
import { useSyncedPlotly } from '../../hooks/useSyncedPlotly'
import { detectDives } from '../../lib/diveDetect'

export default function DivePanel() {
  const { analysisData } = useDeploymentStore()
  const { plotRef, onHover, onRelayout, currentTime, xRange } = useSyncedPlotly()

  const { data, layout, dives } = useMemo(() => {
    if (!analysisData?.depth?.length) return { data: [], layout: {}, dives: [] }
    const n = analysisData.depth.length
    const duration = (analysisData.end_idx - analysisData.start_idx) / 10 || n / 10
    const times = Array.from({ length: n }, (_, i) => (i / n) * duration)
    const dives = detectDives(analysisData.depth, duration)

    const shapes = dives.flatMap((d, idx) => [
      { type: 'rect', xref: 'x', yref: 'paper', x0: d.startTime, x1: d.bottomStart,
        y0: 0, y1: 1, fillcolor: '#3b82f6', opacity: 0.12, line: { width: 0 } },
      { type: 'rect', xref: 'x', yref: 'paper', x0: d.bottomStart, x1: d.bottomEnd,
        y0: 0, y1: 1, fillcolor: '#f59e0b', opacity: 0.18, line: { width: 0 } },
      { type: 'rect', xref: 'x', yref: 'paper', x0: d.bottomEnd, x1: d.endTime,
        y0: 0, y1: 1, fillcolor: '#22c55e', opacity: 0.12, line: { width: 0 } },
    ])
    if (currentTime > 0) {
      shapes.push({
        type: 'line', x0: currentTime, x1: currentTime, y0: 0, y1: 1,
        yref: 'paper', line: { color: '#a855f7', width: 1.5, dash: 'dot' },
      })
    }

    return {
      dives,
      data: [
        {
          type: 'scatter', mode: 'lines', x: times, y: analysisData.depth,
          name: 'Depth', line: { color: '#e2e8f0', width: 1.5 },
          hovertemplate: 'Time: %{x:.2f}s<br>Depth: %{y:.1f}m<extra></extra>',
        },
      ],
      layout: {
        xaxis: {
          title: { text: 'Time (s)', font: { size: 10, color: '#a1a1aa' } },
          color: '#a1a1aa', gridcolor: '#27272a',
          ...(xRange ? { range: xRange } : {}),
        },
        yaxis: {
          title: { text: 'Depth (m)', font: { size: 10, color: '#a1a1aa' } },
          color: '#a1a1aa', gridcolor: '#27272a', autorange: 'reversed',
        },
        margin: { t: 10, b: 40, l: 50, r: 10 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: '#09090b',
        showlegend: false,
        shapes,
      },
    }
  }, [analysisData, currentTime, xRange])

  if (!analysisData?.depth?.length) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        Run analysis to see dive profile
      </div>
    )
  }

  const exportCsv = () => {
    const rows = [
      ['dive', 'start_s', 'end_s', 'duration_s', 'max_depth_m', 'bottom_time_s', 'descent_rate', 'ascent_rate'],
      ...dives.map((d, i) => [
        i + 1, d.startTime.toFixed(2), d.endTime.toFixed(2), d.duration.toFixed(2),
        d.maxDepth.toFixed(2), d.bottomTime.toFixed(2),
        d.descentRate.toFixed(3), d.ascentRate.toFixed(3),
      ]),
    ]
    const csv = rows.map((r) => r.join(',')).join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
    const a = document.createElement('a')
    a.href = url
    a.download = 'dives.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-col h-full">
      <div style={{ flex: '1 1 60%' }} className="min-h-0">
        <Plot
          ref={plotRef}
          data={data} layout={layout}
          config={{ responsive: true, displayModeBar: false }}
          onHover={onHover} onRelayout={onRelayout}
          useResizeHandler style={{ width: '100%', height: '100%' }}
        />
      </div>
      <div style={{ flex: '1 1 40%' }} className="min-h-0 overflow-auto border-t border-border">
        <div className="flex items-center justify-between px-2 py-1 bg-muted/40 text-xs text-muted-foreground">
          <span>{dives.length} dive{dives.length === 1 ? '' : 's'} (≥5m)</span>
          {dives.length > 0 && (
            <button onClick={exportCsv} className="text-accent hover:underline">
              Export CSV
            </button>
          )}
        </div>
        {dives.length === 0 ? (
          <div className="p-2 text-xs text-muted-foreground">No dives detected in interval</div>
        ) : (
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-card">
              <tr className="text-muted-foreground text-left">
                <th className="px-2 py-1">#</th>
                <th className="px-2 py-1">Start</th>
                <th className="px-2 py-1">Dur</th>
                <th className="px-2 py-1">Max d</th>
                <th className="px-2 py-1">Bottom</th>
                <th className="px-2 py-1">↓ rate</th>
                <th className="px-2 py-1">↑ rate</th>
              </tr>
            </thead>
            <tbody>
              {dives.map((d, i) => (
                <tr key={i} className="border-t border-border/40 font-mono text-foreground">
                  <td className="px-2 py-0.5">{i + 1}</td>
                  <td className="px-2 py-0.5">{d.startTime.toFixed(1)}s</td>
                  <td className="px-2 py-0.5">{d.duration.toFixed(1)}s</td>
                  <td className="px-2 py-0.5">{d.maxDepth.toFixed(1)}m</td>
                  <td className="px-2 py-0.5">{d.bottomTime.toFixed(1)}s</td>
                  <td className="px-2 py-0.5">{d.descentRate.toFixed(2)}</td>
                  <td className="px-2 py-0.5">{d.ascentRate.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
