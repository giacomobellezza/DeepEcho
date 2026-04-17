import React, { useRef } from 'react'
import Plotly from 'plotly.js-dist-min'
import { useLayoutStore, PANEL_LABELS } from '../stores/layoutStore'

export default function PanelWrapper({ id, type, children }) {
  const togglePanel = useLayoutStore((s) => s.togglePanel)
  const toggleMaximized = useLayoutStore((s) => s.toggleMaximized)
  const maximizedId = useLayoutStore((s) => s.maximizedId)
  const contentRef = useRef(null)
  const isMaximized = maximizedId === id

  const stopDrag = (e) => {
    e.stopPropagation()
  }

  const handleExport = (e) => {
    stopDrag(e)
    const node = contentRef.current?.querySelector('.js-plotly-plot')
    if (!node) return
    Plotly.downloadImage(node, {
      format: 'png',
      filename: `cats-${type}`,
      width: node.clientWidth * 2,
      height: node.clientHeight * 2,
    })
  }

  return (
    <div className="flex flex-col h-full bg-card rounded-lg border border-border overflow-hidden">
      {/* Header - drag handle */}
      <div
        className="drag-handle flex items-center justify-between px-3 py-1.5 bg-muted border-b border-border cursor-move select-none"
        onDoubleClick={() => toggleMaximized(id)}
      >
        <span className="text-xs font-medium text-muted-foreground">
          {PANEL_LABELS[type] || type}
        </span>
        <div className="flex items-center gap-1" onMouseDown={stopDrag} onTouchStart={stopDrag}>
          <button
            onClick={handleExport}
            onMouseDown={stopDrag}
            className="text-muted-foreground hover:text-accent text-xs px-1"
            title="Export as PNG"
          >
            ⬇
          </button>
          <button
            onClick={() => toggleMaximized(id)}
            onMouseDown={stopDrag}
            className="text-muted-foreground hover:text-accent text-xs px-1"
            title={isMaximized ? 'Restore' : 'Maximize'}
          >
            {isMaximized ? '▭' : '⛶'}
          </button>
          <button
            onClick={() => togglePanel(id)}
            onMouseDown={stopDrag}
            className="text-muted-foreground hover:text-destructive text-xs px-1"
            title="Close panel"
          >
            ✕
          </button>
        </div>
      </div>
      {/* Content */}
      <div ref={contentRef} className="flex-1 overflow-hidden min-h-0">
        {children}
      </div>
    </div>
  )
}
