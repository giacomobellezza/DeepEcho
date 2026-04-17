import React, { useMemo, useEffect, useState } from 'react'
import Plot from 'react-plotly.js'
import { useDeploymentStore } from '../../stores/deploymentStore'
import { useTimelineStore } from '../../stores/timelineStore'
import { useSettingsStore, SPECIES } from '../../stores/settingsStore'
import { buildCetaceanTrace, hasModel } from '../../lib/cetaceanMesh'
import { detectPreyCaptures } from '../../lib/preyDetection'

export default function TrajectoryPlot() {
  const { analysisData, fetchTrajectory } = useDeploymentStore()
  const { currentTime } = useTimelineStore()
  const { species } = useSettingsStore()
  const speciesName = SPECIES.find((s) => s.id === species)?.name ?? ''
  const [trajectoryData, setTrajectoryData] = useState(null)

  useEffect(() => {
    if (!analysisData?.deployment_id) return
    const load = async () => {
      const data = await fetchTrajectory(
        analysisData.deployment_id,
        analysisData.start_idx,
        analysisData.end_idx
      )
      setTrajectoryData(data)
    }
    load()
  }, [analysisData?.deployment_id, analysisData?.start_idx, analysisData?.end_idx])

  const { data, layout } = useMemo(() => {
    if (!trajectoryData?.dx?.length) {
      return { data: [], layout: {} }
    }

    const { dx, dy, dz } = trajectoryData
    const n = dx.length
    const duration = analysisData ? (analysisData.end_idx - analysisData.start_idx) / 10 : n / 10

    // Current position index from crosshair time
    const currentIdx = Math.min(
      Math.max(0, Math.floor((currentTime / duration) * n)),
      n - 1
    )

    // Map trajectory index to PRH index for orientation
    const prhLen = analysisData?.pitch?.length ?? 0
    const prhIdx = prhLen ? Math.min(Math.floor((currentIdx / n) * prhLen), prhLen - 1) : 0
    const pitch = analysisData?.pitch?.[prhIdx] ?? 0
    const roll = analysisData?.roll?.[prhIdx] ?? 0
    const heading = analysisData?.heading?.[prhIdx] ?? 0

    // Scale mesh relative to trajectory extent
    const extent = Math.max(
      Math.max(...dx) - Math.min(...dx),
      Math.max(...dy) - Math.min(...dy),
      Math.max(...dz) - Math.min(...dz),
      1
    )
    const meshScale = extent * 0.10

    // Cetacean mesh trace — pass raw PRH values, rotation handles conventions
    const currentTrace = hasModel(species)
      ? buildCetaceanTrace({
          species,
          scale: meshScale,
          position: [dx[currentIdx], dy[currentIdx], dz[currentIdx]],
          pitch, roll, heading,
        })
      : {
          type: 'scatter3d', mode: 'markers',
          x: [dx[currentIdx]], y: [dy[currentIdx]], z: [dz[currentIdx]],
          name: 'Current',
          marker: { color: '#ef4444', size: 8, symbol: 'circle' },
          hovertemplate: 'Current position<extra></extra>',
        }

    // Prey capture markers in 3D
    const pcaIndices = detectPreyCaptures(analysisData?.jerk)
    const pcaX = [], pcaY = [], pcaZ = []
    for (const jerkIdx of pcaIndices) {
      // Map PRH index to trajectory index
      const trajIdx = Math.min(Math.floor((jerkIdx / prhLen) * n), n - 1)
      pcaX.push(dx[trajIdx])
      pcaY.push(dy[trajIdx])
      pcaZ.push(dz[trajIdx])
    }

    const traces = [
      // Trajectory path — color gradient by time
      {
        type: 'scatter3d', mode: 'lines', x: dx, y: dy, z: dz,
        name: speciesName || 'Path',
        line: {
          color: Array.from({ length: n }, (_, i) => i / n),
          colorscale: [[0, '#1e40af'], [0.5, '#3b82f6'], [1, '#93c5fd']],
          width: 4,
        },
        hovertemplate: 'X: %{x:.1f}m<br>Y: %{y:.1f}m<br>Depth: %{z:.1f}m<extra></extra>',
      },
      // Cetacean mesh at current time
      currentTrace,
      // Start marker
      {
        type: 'scatter3d', mode: 'markers',
        x: [dx[0]], y: [dy[0]], z: [dz[0]],
        name: 'Start',
        marker: { color: '#22c55e', size: 6, symbol: 'diamond' },
        hovertemplate: 'Start<extra></extra>',
      },
    ]

    // Add prey capture markers if any
    if (pcaX.length > 0) {
      traces.push({
        type: 'scatter3d', mode: 'markers',
        x: pcaX, y: pcaY, z: pcaZ,
        name: `Prey (${pcaX.length})`,
        marker: {
          color: '#ef4444',
          size: 5,
          symbol: 'circle',
          line: { color: '#fca5a5', width: 1 },
        },
        hovertemplate: 'Prey capture attempt<br>Depth: %{z:.1f}m<extra></extra>',
      })
    }

    return {
      data: traces,
      layout: {
        scene: {
          xaxis: { title: 'East (m)', color: '#a1a1aa', gridcolor: '#27272a' },
          yaxis: { title: 'North (m)', color: '#a1a1aa', gridcolor: '#27272a' },
          zaxis: { title: 'Depth (m)', color: '#a1a1aa', gridcolor: '#27272a', autorange: 'reversed' },
          bgcolor: '#09090b',
          aspectmode: 'data',
        },
        margin: { t: 24, b: 10, l: 10, r: 10 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        showlegend: true,
        legend: {
          x: 0, y: 1, font: { size: 10, color: '#a1a1aa' },
          bgcolor: 'rgba(0,0,0,0)',
        },
      },
    }
  }, [trajectoryData, currentTime, analysisData, speciesName, species])

  if (!trajectoryData?.dx) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        {analysisData ? 'Loading trajectory...' : 'Run analysis to see 3D trajectory'}
      </div>
    )
  }

  return (
    <Plot
      data={data} layout={layout}
      config={{ responsive: true, displayModeBar: false }}
      useResizeHandler style={{ width: '100%', height: '100%' }}
    />
  )
}
