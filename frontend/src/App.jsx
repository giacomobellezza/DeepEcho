import React, { useEffect } from 'react'
import Sidebar from './components/Sidebar'
import DashboardGrid from './components/DashboardGrid'
import Timeline from './components/Timeline'
import HoverReadout from './components/HoverReadout'
import { useTimelineStore } from './stores/timelineStore'
import { useLayoutStore } from './stores/layoutStore'
import { useDeploymentStore } from './stores/deploymentStore'
import { useSettingsStore } from './stores/settingsStore'

export default function App() {
  const { currentTime, setCurrentTime, togglePlay, setXRange } = useTimelineStore()
  const { maximizedId, setMaximized } = useLayoutStore()
  const { analysisData, deployment } = useDeploymentStore()
  const { theme } = useSettingsStore()

  // Apply theme on mount and when it changes
  useEffect(() => {
    const isDark = theme === 'dark'
    document.documentElement.classList.toggle('dark', isDark)
  }, [theme])

  useEffect(() => {
    const handler = (e) => {
      if (e.target.closest('input, textarea, select')) return
      const { selectedInterval } = useTimelineStore.getState()
      const duration = analysisData
        ? (analysisData.end_idx - analysisData.start_idx) / 10
        : (selectedInterval.end_idx - selectedInterval.start_idx) / 10 || 0
      if (e.code === 'Space') {
        e.preventDefault()
        togglePlay()
      } else if (e.key === 'ArrowLeft') {
        setCurrentTime(Math.max(0, currentTime - (e.shiftKey ? 1 : 0.1)))
      } else if (e.key === 'ArrowRight') {
        setCurrentTime(Math.min(duration, currentTime + (e.shiftKey ? 1 : 0.1)))
      } else if (e.key === 'Escape' && maximizedId) {
        setMaximized(null)
      } else if (e.key === 'r' || e.key === 'R') {
        setXRange(null)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [currentTime, setCurrentTime, togglePlay, maximizedId, setMaximized, setXRange, analysisData, deployment])

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <DashboardGrid />
        <HoverReadout />
        <Timeline />
      </div>
    </div>
  )
}
