import React, { useCallback, useEffect } from 'react'
import { Responsive, WidthProvider } from 'react-grid-layout'
import { useLayoutStore } from '../stores/layoutStore'
import { useDeploymentStore } from '../stores/deploymentStore'
import { useTimelineStore } from '../stores/timelineStore'
import PanelWrapper from './PanelWrapper'
import SpectrogramPlot from './plots/SpectrogramPlot'
import DepthSpeedPlot from './plots/DepthSpeedPlot'
import PRHPlot from './plots/PRHPlot'
import JerkFlukePlot from './plots/JerkFlukePlot'
import WaveformPlot from './plots/WaveformPlot'
import TrajectoryPlot from './plots/TrajectoryPlot'
import StatsPanel from './plots/StatsPanel'
import DivePanel from './plots/DivePanel'
import EnergyPlot from './plots/EnergyPlot'

const ResponsiveGridLayout = WidthProvider(Responsive)

const PLOT_COMPONENTS = {
  spectrogram: SpectrogramPlot,
  depthSpeed: DepthSpeedPlot,
  prh: PRHPlot,
  jerkFluke: JerkFlukePlot,
  waveform: WaveformPlot,
  trajectory: TrajectoryPlot,
  stats: StatsPanel,
  dives: DivePanel,
  energy: EnergyPlot,
}

export default function DashboardGrid() {
  const { panels, gridLayout, updateLayout, maximizedId } = useLayoutStore()
  const { deployment, analysisData, isLoading } = useDeploymentStore()
  const activeEventLabel = useTimelineStore((s) => s.activeEventLabel)
  const selectedInterval = useTimelineStore((s) => s.selectedInterval)

  const visiblePanels = panels.filter((p) => p.visible)
  const maximizedPanel = maximizedId ? panels.find((p) => p.id === maximizedId) : null
  const visibleLayout = gridLayout.filter((l) =>
    visiblePanels.some((p) => p.id === l.i)
  )

  const handleLayoutChange = useCallback(
    (layout) => {
      updateLayout(layout)
    },
    [updateLayout]
  )

  // Fire window resize so Plotly's useResizeHandler picks up container size
  const fireResize = useCallback(() => {
    window.dispatchEvent(new Event('resize'))
  }, [])

  const hasData = deployment || analysisData

  useEffect(() => {
    const t = setTimeout(() => window.dispatchEvent(new Event('resize')), 50)
    return () => clearTimeout(t)
  }, [maximizedId])

  if (maximizedPanel) {
    const MaxComponent = PLOT_COMPONENTS[maximizedPanel.type]
    return (
      <div className="flex-1 overflow-hidden p-2 relative">
        <PanelWrapper id={maximizedPanel.id} type={maximizedPanel.type}>
          {MaxComponent ? <MaxComponent /> : <div>Unknown panel type</div>}
        </PanelWrapper>
      </div>
    )
  }

  const intervalSec = analysisData
    ? ((analysisData.end_idx - analysisData.start_idx) / 10).toFixed(1)
    : null

  return (
    <div className="flex-1 overflow-y-auto relative">
      {isLoading && (
        <div className="sticky top-0 left-0 right-0 h-1 bg-muted z-10 overflow-hidden">
          <div className="h-full bg-accent animate-progress" />
        </div>
      )}
      {/* Active event / interval title */}
      {analysisData && (
        <div className="sticky top-0 z-10 bg-card/90 backdrop-blur-sm border-b border-border px-4 py-2 flex items-center gap-3">
          {activeEventLabel ? (
            <span className="text-sm font-semibold text-accent">{activeEventLabel}</span>
          ) : (
            <span className="text-sm font-semibold text-muted-foreground">Custom interval</span>
          )}
          <span className="text-xs text-muted-foreground">
            {(selectedInterval.start_idx / 10).toFixed(1)}s – {(selectedInterval.end_idx / 10).toFixed(1)}s
          </span>
          <span className="text-xs text-muted-foreground">({intervalSec}s)</span>
        </div>
      )}
      <div className="p-2">
        {!hasData ? (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            <div className="text-center space-y-2">
              <p className="text-lg">No data loaded</p>
              <p className="text-sm">Upload WAV + PRH + Events files to begin</p>
            </div>
          </div>
        ) : (
          <ResponsiveGridLayout
            className="layout"
            layouts={{ lg: visibleLayout }}
            breakpoints={{ lg: 1200, md: 996, sm: 768 }}
            cols={{ lg: 12, md: 12, sm: 6 }}
            rowHeight={60}
            draggableHandle=".drag-handle"
            onLayoutChange={handleLayoutChange}
            onResize={fireResize}
            onResizeStop={fireResize}
            compactType="vertical"
            margin={[8, 8]}
          >
            {visiblePanels.map((panel) => {
              const PlotComponent = PLOT_COMPONENTS[panel.type]
              return (
                <div key={panel.id}>
                  <PanelWrapper id={panel.id} type={panel.type}>
                    {PlotComponent ? <PlotComponent /> : <div>Unknown panel type</div>}
                  </PanelWrapper>
                </div>
              )
            })}
          </ResponsiveGridLayout>
        )}
      </div>
    </div>
  )
}
