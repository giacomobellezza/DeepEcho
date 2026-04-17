import React, { useMemo } from 'react'
import { useDeploymentStore } from '../../stores/deploymentStore'

function stats(arr) {
  if (!arr?.length) return null
  let min = Infinity, max = -Infinity, sum = 0
  for (let i = 0; i < arr.length; i++) {
    const v = arr[i]
    if (v < min) min = v
    if (v > max) max = v
    sum += v
  }
  return { min, max, mean: sum / arr.length }
}

function Row({ label, value, unit = '', tip }) {
  return (
    <div
      className="flex justify-between items-baseline py-1 border-b border-border/40"
      title={tip}
    >
      <span className="text-xs text-muted-foreground cursor-help">{label}</span>
      <span className="text-sm font-mono text-foreground">
        {value}
        {unit && <span className="text-muted-foreground ml-1">{unit}</span>}
      </span>
    </div>
  )
}

export default function StatsPanel() {
  const { analysisData } = useDeploymentStore()

  const s = useMemo(() => {
    if (!analysisData) return null
    const duration = (analysisData.end_idx - analysisData.start_idx) / 10
    const depth = stats(analysisData.depth)
    const speed = stats(analysisData.speed)
    const jerk = stats(analysisData.jerk)
    const pitch = stats(analysisData.pitch)
    const odba = stats(analysisData.odba)

    let distance = 0
    if (analysisData.speed?.length > 1) {
      const dt = duration / analysisData.speed.length
      for (const v of analysisData.speed) distance += Math.abs(v) * dt
    }

    // Energy expenditure proxy: integral of ODBA over time
    let odbaIntegral = null
    if (analysisData.odba?.length) {
      const dt = duration / analysisData.odba.length
      let sum = 0
      for (const v of analysisData.odba) sum += v * dt
      odbaIntegral = sum
    }

    return { duration, depth, speed, jerk, pitch, odba, distance, odbaIntegral }
  }, [analysisData])

  if (!s) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        Run analysis to see statistics
      </div>
    )
  }

  const fmt = (v, d = 2) => (v == null ? '—' : v.toFixed(d))

  return (
    <div className="p-3 overflow-y-auto h-full text-sm">
      <div className="grid grid-cols-1 gap-0">
        <Row label="Duration" value={fmt(s.duration, 1)} unit="s"
          tip="Length of the analysed interval" />
        <Row label="Distance traveled" value={fmt(s.distance, 1)} unit="m"
          tip="Integral of |speed| over time" />
        {s.depth && (
          <>
            <Row label="Depth min / max" value={`${fmt(s.depth.min, 1)} / ${fmt(s.depth.max, 1)}`} unit="m"
              tip="Minimum and maximum depth in the interval" />
            <Row label="Depth mean" value={fmt(s.depth.mean, 1)} unit="m"
              tip="Average depth" />
          </>
        )}
        {s.speed && (
          <>
            <Row label="Speed max" value={fmt(s.speed.max, 2)} unit="m/s"
              tip="Peak swim speed" />
            <Row label="Speed mean" value={fmt(s.speed.mean, 2)} unit="m/s"
              tip="Average swim speed" />
          </>
        )}
        {s.jerk && (
          <Row label="Jerk peak" value={fmt(s.jerk.max, 3)}
            tip="Peak magnitude of d(acceleration)/dt — proxy for prey-capture strikes" />
        )}
        {s.pitch && (
          <Row label="Pitch range" value={`${fmt(s.pitch.min, 1)} / ${fmt(s.pitch.max, 1)}`} unit="°"
            tip="Minimum and maximum body pitch" />
        )}
        {s.odba && (
          <Row label="ODBA mean" value={fmt(s.odba.mean, 3)} unit="g"
            tip="Overall Dynamic Body Acceleration: |Ax'|+|Ay'|+|Az'| after high-pass. Proxy for energy expenditure." />
        )}
        {s.odbaIntegral != null && (
          <Row label="∫ ODBA dt" value={fmt(s.odbaIntegral, 2)} unit="g·s"
            tip="Time-integrated ODBA — cumulative activity budget for the interval" />
        )}
        <Row label="Samples" value={analysisData.depth?.length ?? 0}
          tip="Number of PRH samples (10 Hz)" />
      </div>
    </div>
  )
}
