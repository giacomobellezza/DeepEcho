import { useCallback, useEffect, useRef } from 'react'
import { useTimelineStore } from '../stores/timelineStore'

/**
 * Shared Plotly sync hook: returns plotRef, onHover, onRelayout handlers
 * that keep crosshair (currentTime) and zoom (xRange) synced across charts,
 * with feedback-loop protection.
 *
 * Also installs a ResizeObserver on the plot container that triggers
 * Plotly autosize — fixes panels that wouldn't rescale when the grid
 * cell resized (window-resize only doesn't fire for grid drag-resize).
 */
export function useSyncedPlotly() {
  const currentTime = useTimelineStore((s) => s.currentTime)
  const setCurrentTime = useTimelineStore((s) => s.setCurrentTime)
  const xRange = useTimelineStore((s) => s.xRange)
  const setXRange = useTimelineStore((s) => s.setXRange)

  const plotRef = useRef(null)
  const xRangeRef = useRef(xRange)
  xRangeRef.current = xRange

  const onHover = useCallback(
    (event) => {
      const x = event?.points?.[0]?.x
      if (typeof x === 'number') setCurrentTime(x)
    },
    [setCurrentTime]
  )

  const onRelayout = useCallback(
    (event) => {
      const r0 = event['xaxis.range[0]']
      const r1 = event['xaxis.range[1]']
      if (r0 != null && r1 != null) {
        const cur = xRangeRef.current
        // Skip if already matches current store range (breaks feedback loop)
        if (cur && Math.abs(r0 - cur[0]) < 1e-6 && Math.abs(r1 - cur[1]) < 1e-6) return
        setXRange([r0, r1])
      } else if (event['xaxis.autorange']) {
        if (xRangeRef.current !== null) setXRange(null)
      }
    },
    [setXRange]
  )

  // ResizeObserver: make plot follow container size (grid-resize fix)
  useEffect(() => {
    const node = plotRef.current?.el || plotRef.current
    if (!node || typeof ResizeObserver === 'undefined') return
    const container = node.closest?.('.react-grid-item') || node.parentElement
    if (!container) return
    const obs = new ResizeObserver(() => {
      // Trigger Plotly resize via window event (Plotly useResizeHandler listens)
      window.dispatchEvent(new Event('resize'))
    })
    obs.observe(container)
    return () => obs.disconnect()
  }, [])

  return { plotRef, onHover, onRelayout, currentTime, xRange }
}
