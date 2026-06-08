import React, { useState } from 'react'
import { useDeploymentStore } from '../stores/deploymentStore'
import { useTimelineStore } from '../stores/timelineStore'
import { useSettingsStore } from '../stores/settingsStore'
import { formatTime } from '../lib/utils'

const PRH_HZ = 10

export default function Timeline() {
  const { deployment, analysisData } = useDeploymentStore()
  const { currentTime, setCurrentTime, selectedInterval, setSelectedInterval, xRange, setXRange } = useTimelineStore()
  const { timeFormat } = useSettingsStore()
  const deploymentStart = deployment?.metadata?.deployment_start || null
  // Unit for the interval Start/End inputs: seconds or minutes.
  const [unit, setUnit] = useState('s')
  const unitFactor = unit === 'min' ? 60 : 1
  const unitStep = unit === 'min' ? 0.01 : 0.1
  const fmtUnit = (sec) => (sec / unitFactor).toFixed(unit === 'min' ? 2 : 1)
  const toIdx = (val) => Math.round((parseFloat(val || 0) * unitFactor) * PRH_HZ)

  // Duration = current analyzed interval
  const intervalDuration = analysisData
    ? (analysisData.end_idx - analysisData.start_idx) / PRH_HZ
    : (selectedInterval.end_idx - selectedInterval.start_idx) / PRH_HZ

  const totalDuration = deployment?.duration_seconds || 0

  // Convert sample indices to seconds for display
  const startSec = selectedInterval.start_idx / PRH_HZ
  const endSec = selectedInterval.end_idx / PRH_HZ

  if (!deployment) return null

  return (
    <div className="border-t border-border bg-card px-4 py-3 space-y-2">
      {/* Time scrubber — relative to analyzed interval */}
      <div className="flex items-center gap-3">
        <span className="text-xs text-muted-foreground w-16 text-right">
          {formatTime(currentTime, timeFormat, deploymentStart)}
        </span>
        <input
          type="range"
          min={0}
          max={intervalDuration || 1}
          step={0.1}
          value={Math.min(currentTime, intervalDuration)}
          onChange={(e) => setCurrentTime(parseFloat(e.target.value))}
          className="flex-1 h-1.5 accent-accent cursor-pointer"
          aria-label={`Timeline scrubber, current time ${currentTime.toFixed(1)} seconds`}
        />
        <span className="text-xs text-muted-foreground w-16">
          {formatTime(intervalDuration, timeFormat, deploymentStart)}
        </span>
      </div>

      {/* Interval selector — seconds or minutes */}
      <div className="flex items-center gap-3 text-xs">
        <span className="text-muted-foreground">Interval:</span>
        <label className="flex items-center gap-1 text-muted-foreground">
          Start
          <input
            type="number"
            min={0}
            max={totalDuration / unitFactor}
            step={unitStep}
            value={fmtUnit(startSec)}
            onChange={(e) =>
              setSelectedInterval({
                ...selectedInterval,
                start_idx: toIdx(e.target.value),
              })
            }
            className="w-20 px-2 py-1 rounded bg-muted border border-border text-foreground text-xs"
            aria-label={`Interval start time in ${unit === 'min' ? 'minutes' : 'seconds'}`}
          />
        </label>
        <label className="flex items-center gap-1 text-muted-foreground">
          End
          <input
            type="number"
            min={0}
            max={totalDuration / unitFactor}
            step={unitStep}
            value={fmtUnit(endSec)}
            onChange={(e) =>
              setSelectedInterval({
                ...selectedInterval,
                end_idx: toIdx(e.target.value),
              })
            }
            className="w-20 px-2 py-1 rounded bg-muted border border-border text-foreground text-xs"
            aria-label={`Interval end time in ${unit === 'min' ? 'minutes' : 'seconds'}`}
          />
        </label>
        <select
          value={unit}
          onChange={(e) => setUnit(e.target.value)}
          className="px-1 py-1 rounded bg-muted border border-border text-foreground text-xs"
          aria-label="Interval input unit"
        >
          <option value="s">sec</option>
          <option value="min">min</option>
        </select>
        <span className="text-muted-foreground font-medium">
          ({intervalDuration.toFixed(1)}s)
        </span>
        <span className="ml-auto text-[10px] text-muted-foreground" title="Space: play/pause · ←/→: step (Shift = 1s) · R: reset sync · Esc: exit maximize">
          ⌨ shortcuts
        </span>
        <button
          onClick={() => setXRange(null)}
          disabled={!xRange}
          title="Reset zoom and re-sync all charts (R)"
          className="px-2 py-1 rounded bg-muted border border-border text-foreground hover:bg-accent hover:text-accent-foreground disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          aria-label="Reset zoom and synchronize all charts"
        >
          ↺ Reset sync
        </button>
      </div>
    </div>
  )
}
