import React from 'react'
import { useDeploymentStore } from '../stores/deploymentStore'
import { useTimelineStore } from '../stores/timelineStore'

function sampleAt(arr, t, duration) {
  if (!arr?.length || duration <= 0) return null
  const idx = Math.min(arr.length - 1, Math.max(0, Math.floor((t / duration) * arr.length)))
  return arr[idx]
}

function Stat({ label, value, unit, color }) {
  if (value == null || Number.isNaN(value)) return null
  return (
    <div className="flex items-baseline gap-1">
      <span className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="font-mono text-xs" style={{ color }}>
        {value.toFixed(2)}
        <span className="text-muted-foreground ml-0.5">{unit}</span>
      </span>
    </div>
  )
}

export default function HoverReadout() {
  const { analysisData } = useDeploymentStore()
  const { currentTime } = useTimelineStore()

  if (!analysisData?.depth?.length) return null
  const duration = (analysisData.end_idx - analysisData.start_idx) / 10 || 1

  const depth = sampleAt(analysisData.depth, currentTime, duration)
  const speed = sampleAt(analysisData.speed, currentTime, duration)
  const pitch = sampleAt(analysisData.pitch, currentTime, duration)
  const roll = sampleAt(analysisData.roll, currentTime, duration)
  const heading = sampleAt(analysisData.heading, currentTime, duration)
  const jerk = sampleAt(analysisData.jerk, currentTime, duration)
  const odba = sampleAt(analysisData.odba, currentTime, duration)

  return (
    <div className="border-t border-border bg-card/80 px-4 py-1.5 flex flex-wrap items-center gap-x-4 gap-y-1">
      <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
        t = <span className="font-mono text-foreground">{currentTime.toFixed(2)}s</span>
      </span>
      <Stat label="Depth" value={depth} unit="m" color="#3b82f6" />
      <Stat label="Speed" value={speed} unit="m/s" color="#ef4444" />
      <Stat label="Pitch" value={pitch} unit="°" color="#3b82f6" />
      <Stat label="Roll" value={roll} unit="°" color="#22c55e" />
      <Stat label="Heading" value={heading} unit="°" color="#ef4444" />
      <Stat label="Jerk" value={jerk} unit="" color="#f59e0b" />
      <Stat label="ODBA" value={odba} unit="g" color="#f59e0b" />
    </div>
  )
}
