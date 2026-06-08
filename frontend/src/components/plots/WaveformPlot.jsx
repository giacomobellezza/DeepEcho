import React, { useMemo, useRef, useState, useCallback, useEffect } from 'react'
import Plot from 'react-plotly.js'
import { useDeploymentStore, API_BASE } from '../../stores/deploymentStore'
import { useTimelineStore } from '../../stores/timelineStore'
import { useSyncedPlotly } from '../../hooks/useSyncedPlotly'
import { usePlotTheme } from '../../hooks/usePlotTheme'

export default function WaveformPlot() {
  const { analysisData } = useDeploymentStore()
  const { plotRef, onHover, onRelayout, currentTime, xRange } = useSyncedPlotly()
  const theme = usePlotTheme()
  const { setCurrentTime } = useTimelineStore()
  const audioCtxRef = useRef(null)
  const sourceRef = useRef(null)
  const startTimeRef = useRef(null)
  const [isPlaying, setIsPlaying] = useState(false)

  const stop = useCallback(() => {
    try { sourceRef.current?.stop() } catch {}
    sourceRef.current = null
    startTimeRef.current = null
    setIsPlaying(false)
  }, [])

  const play = useCallback(async () => {
    const deploymentId = analysisData?.deployment_id
    const startIdx = analysisData?.start_idx
    const endIdx = analysisData?.end_idx
    if (!deploymentId || startIdx == null || endIdx == null) return

    if (!audioCtxRef.current) {
      const Ctx = window.AudioContext || window.webkitAudioContext
      if (!Ctx) return
      audioCtxRef.current = new Ctx()
    }
    const ctx = audioCtxRef.current
    if (ctx.state === 'suspended') ctx.resume()

    try {
      const resp = await fetch(`${API_BASE}/audio/${deploymentId}?start_idx=${startIdx}&end_idx=${endIdx}`)
      if (!resp.ok) return
      const arrayBuf = await resp.arrayBuffer()
      const buf = await ctx.decodeAudioData(arrayBuf)
      const src = ctx.createBufferSource()
      src.buffer = buf
      src.connect(ctx.destination)
      startTimeRef.current = ctx.currentTime
      src.onended = () => {
        sourceRef.current = null
        startTimeRef.current = null
        setIsPlaying(false)
      }
      sourceRef.current = src
      src.start()
      setIsPlaying(true)
    } catch (e) {
      console.error('Audio playback failed:', e)
    }
  }, [analysisData])

  // Update currentTime during playback
  useEffect(() => {
    if (!isPlaying || !audioCtxRef.current || !startTimeRef.current) return
    let animId
    const update = () => {
      if (!sourceRef.current || !startTimeRef.current) return
      const elapsed = audioCtxRef.current.currentTime - startTimeRef.current
      setCurrentTime(Math.max(0, elapsed))
      animId = requestAnimationFrame(update)
    }
    animId = requestAnimationFrame(update)
    return () => cancelAnimationFrame(animId)
  }, [isPlaying, setCurrentTime])

  useEffect(() => () => { try { sourceRef.current?.stop() } catch {} }, [])

  const { data, layout } = useMemo(() => {
    if (!analysisData?.audio_slice?.length) return { data: [], layout: {} }

    const raw = analysisData.audio_slice
    const maxPoints = 2000
    const duration = (analysisData.end_idx - analysisData.start_idx) / 10 || 1

    let samples, times
    if (raw.length > maxPoints) {
      const stride = Math.max(1, Math.floor(raw.length / maxPoints))
      samples = []
      times = []
      for (let i = 0; i < raw.length; i += stride) {
        samples.push(raw[i])
        times.push((i / raw.length) * duration)
      }
    } else {
      samples = raw
      times = Array.from({ length: raw.length }, (_, i) => (i / raw.length) * duration)
    }

    return {
      data: [{
        type: 'scattergl', mode: 'lines', x: times, y: samples,
        name: 'Waveform', line: { color: '#8b5cf6', width: 1 },
        hovertemplate: 'Time: %{x:.3f}s<br>Amp: %{y:.4f}<extra></extra>',
      }],
      layout: {
        xaxis: {
          title: { text: 'Time (s)', font: { size: 10, color: theme.axis } },
          color: theme.axis, gridcolor: theme.grid,
          ...(xRange ? { range: xRange } : {}),
        },
        yaxis: {
          title: { text: 'Amplitude', font: { size: 10, color: theme.axis } },
          color: theme.axis, gridcolor: theme.grid,
        },
        margin: { t: 10, b: 40, l: 50, r: 10 },
        paper_bgcolor: theme.paper,
        plot_bgcolor: theme.plot,
        showlegend: false,
        shapes: currentTime > 0 ? [{
          type: 'line', x0: currentTime, x1: currentTime, y0: 0, y1: 1,
          yref: 'paper', line: { color: '#a855f7', width: 1.5, dash: 'dot' },
        }] : [],
      },
    }
  }, [analysisData, currentTime, xRange, theme])

  if (!analysisData?.audio_slice?.length) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        Run analysis to see waveform
      </div>
    )
  }

  return (
    <div className="relative w-full h-full">
      <button
        onClick={isPlaying ? stop : play}
        className="absolute top-1 right-1 z-10 px-2 py-1 rounded bg-muted/80 border border-border text-xs text-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
        title={isPlaying ? 'Stop playback' : 'Play audio slice'}
      >
        {isPlaying ? '■ Stop' : '▶ Play'}
      </button>
      <Plot
        ref={plotRef}
        data={data} layout={layout}
        config={{ responsive: true, displayModeBar: false }}
        onHover={onHover} onRelayout={onRelayout}
        useResizeHandler style={{ width: '100%', height: '100%' }}
      />
    </div>
  )
}
