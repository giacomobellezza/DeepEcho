import React, { useMemo, useEffect, useState, useCallback } from 'react'
import Plot from 'react-plotly.js'
import { useDeploymentStore } from '../../stores/deploymentStore'
import { useTimelineStore } from '../../stores/timelineStore'
import { usePlotTheme } from '../../hooks/usePlotTheme'

// Fit the map viewport to the track extent. Picks a Mapbox zoom level from the
// larger of the lat/lon spans (rough log2 heuristic that looks right for the
// scattermapbox tile pyramid).
function fitBounds(lats, lons) {
  const minLat = Math.min(...lats), maxLat = Math.max(...lats)
  const minLon = Math.min(...lons), maxLon = Math.max(...lons)
  const center = { lat: (minLat + maxLat) / 2, lon: (minLon + maxLon) / 2 }
  const span = Math.max(maxLat - minLat, maxLon - minLon, 0.005)
  const zoom = Math.min(14, Math.max(7, Math.log2(360 / span) - 1))
  return { center, zoom }
}

const MIN_ZOOM = 1
const MAX_ZOOM = 20

export default function GpsMapPlot() {
  const { deployment, analysisData, fetchTrack } = useDeploymentStore()
  const currentTime = useTimelineStore((s) => s.currentTime)
  const theme = usePlotTheme()
  const [track, setTrack] = useState(null)
  const [loading, setLoading] = useState(false)
  // Controlled viewport so the zoom buttons work and the view survives the
  // marker re-renders. Synced back from user pan/scroll via onRelayout.
  const [view, setView] = useState(null)

  const deploymentId = deployment?.deployment_id
  const hasGps = (deployment?.metadata?.gps_track?.length ?? 0) > 0

  useEffect(() => {
    if (!deploymentId || !hasGps) {
      setTrack(null)
      setView(null)
      return
    }
    let cancelled = false
    setLoading(true)
    fetchTrack(deploymentId).then((data) => {
      if (cancelled) return
      setTrack(data)
      setLoading(false)
      if (data?.lat?.length) setView(fitBounds(data.lat, data.lon))
    })
    return () => { cancelled = true }
  }, [deploymentId, hasGps])

  const handleRelayout = useCallback((e) => {
    if (!e) return
    setView((v) => {
      const next = { ...(v || {}) }
      if (e['mapbox.center']) next.center = e['mapbox.center']
      if (e['mapbox.zoom'] != null) next.zoom = e['mapbox.zoom']
      return next
    })
  }, [])

  const nudgeZoom = useCallback((delta) => {
    setView((v) => {
      if (!v) return v
      const zoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, (v.zoom ?? 8) + delta))
      return { ...v, zoom }
    })
  }, [])

  // Animal position on the track, synced to the timeline crosshair. currentTime
  // is seconds within the analysed interval, so the absolute PRH frame is
  // start_idx + currentTime*10; map that onto the uniformly-decimated arrays.
  const marker = useMemo(() => {
    if (!track?.lat?.length || !analysisData || !track.frames) return null
    const absIdx = (analysisData.start_idx ?? 0) + currentTime * 10
    const frac = Math.min(1, Math.max(0, absIdx / track.frames))
    const i = Math.round(frac * (track.lat.length - 1))
    return { lat: track.lat[i], lon: track.lon[i], depth: track.depth[i] }
  }, [track, analysisData, currentTime])

  const { data, layout } = useMemo(() => {
    if (!track?.lat?.length || !view) return { data: [], layout: {} }

    const { lat, lon, depth, fixes } = track

    const traces = [
      // Reconstructed track: thin connecting line + depth-colored markers.
      {
        type: 'scattermapbox', mode: 'lines',
        lat, lon,
        line: { color: 'rgba(148,163,184,0.5)', width: 1 },
        hoverinfo: 'skip', showlegend: false,
      },
      {
        type: 'scattermapbox', mode: 'markers',
        lat, lon,
        marker: {
          size: 5,
          color: depth,
          colorscale: [[0, '#bae6fd'], [0.5, '#3b82f6'], [1, '#0c1f5e']],
          cmin: 0,
          colorbar: {
            title: { text: 'Depth (m)', font: { color: theme.axis, size: 11 } },
            tickfont: { color: theme.axis, size: 10 },
            thickness: 12, len: 0.85, x: 1,
          },
        },
        name: 'Track',
        hovertemplate: 'Depth: %{marker.color:.0f} m<br>%{lat:.4f}, %{lon:.4f}<extra></extra>',
      },
    ]

    // Labeled GPS surface fixes. In-range fixes (anchors) are solid; fixes
    // beyond the PRH coverage are hollow so it's clear they don't anchor.
    const fx = fixes ?? []
    if (fx.length) {
      const anchored = fx.filter((f) => f.in_range)
      const outside = fx.filter((f) => !f.in_range)
      const fixTrace = (pts, color, name) => ({
        type: 'scattermapbox', mode: 'markers+text',
        lat: pts.map((p) => p.latitude),
        lon: pts.map((p) => p.longitude),
        text: pts.map((p) => p.label || ''),
        textposition: 'top right',
        textfont: { color: theme.axis, size: 10 },
        marker: { size: 11, color, symbol: 'circle' },
        name,
        hovertemplate: '%{text}<br>%{lat:.4f}, %{lon:.4f}<extra></extra>',
      })
      if (anchored.length) traces.push(fixTrace(anchored, '#f59e0b', 'GPS fix'))
      if (outside.length) traces.push(fixTrace(outside, '#9ca3af', 'GPS fix (outside record)'))
    }

    // Timeline-synced animal position.
    if (marker) {
      traces.push({
        type: 'scattermapbox', mode: 'markers',
        lat: [marker.lat], lon: [marker.lon],
        marker: { size: 15, color: '#fde047', opacity: 1 },
        name: 'Animal',
        hovertemplate: `Animal here<br>Depth: ${marker.depth?.toFixed(0)} m<extra></extra>`,
      })
    }

    return {
      data: traces,
      layout: {
        mapbox: { style: 'open-street-map', center: view.center, zoom: view.zoom },
        margin: { t: 6, b: 6, l: 6, r: 6 },
        paper_bgcolor: theme.paper,
        showlegend: true,
        legend: { x: 0, y: 1, font: { size: 10, color: theme.axis }, bgcolor: 'rgba(0,0,0,0)' },
      },
    }
  }, [track, theme, view, marker])

  if (!hasGps) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm text-center px-4">
        {deployment
          ? 'No GPS track in this deployment. Upload a deployment whose metadata file includes a GPS track log.'
          : 'Upload a deployment with GPS metadata to see the map'}
      </div>
    )
  }

  if (loading || !track?.lat?.length) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        {loading ? 'Reconstructing track…' : 'No track available'}
      </div>
    )
  }

  return (
    <div className="relative w-full h-full">
      <Plot
        data={data} layout={layout}
        onRelayout={handleRelayout}
        config={{ responsive: true, displayModeBar: false, scrollZoom: true }}
        useResizeHandler style={{ width: '100%', height: '100%' }}
      />
      {/* Zoom controls (bottom-left, clear of the legend and depth colorbar) */}
      <div className="absolute bottom-2 left-2 z-10 flex flex-col rounded overflow-hidden border border-border shadow">
        <button
          onClick={() => nudgeZoom(1)}
          className="w-7 h-7 flex items-center justify-center bg-card/90 hover:bg-muted text-foreground text-lg leading-none font-semibold"
          title="Zoom in" aria-label="Zoom in"
        >
          +
        </button>
        <button
          onClick={() => nudgeZoom(-1)}
          className="w-7 h-7 flex items-center justify-center bg-card/90 hover:bg-muted text-foreground text-lg leading-none font-semibold border-t border-border"
          title="Zoom out" aria-label="Zoom out"
        >
          −
        </button>
      </div>
    </div>
  )
}
