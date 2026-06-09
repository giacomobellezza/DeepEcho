import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const DEFAULT_PANELS = [
  { id: 'spectrogram', type: 'spectrogram', visible: true },
  { id: 'depthSpeed', type: 'depthSpeed', visible: true },
  { id: 'prh', type: 'prh', visible: true },
  { id: 'jerkFluke', type: 'jerkFluke', visible: true },
  { id: 'waveform', type: 'waveform', visible: false },
  { id: 'trajectory', type: 'trajectory', visible: false },
  { id: 'gpsMap', type: 'gpsMap', visible: false },
  { id: 'stats', type: 'stats', visible: true },
  { id: 'dives', type: 'dives', visible: true },
  { id: 'energy', type: 'energy', visible: false },
]

const DEFAULT_LAYOUT = [
  { i: 'spectrogram', x: 0, y: 0, w: 6, h: 4, minW: 3, minH: 3 },
  { i: 'depthSpeed', x: 6, y: 0, w: 6, h: 4, minW: 3, minH: 3 },
  { i: 'prh', x: 0, y: 4, w: 6, h: 4, minW: 3, minH: 3 },
  { i: 'jerkFluke', x: 6, y: 4, w: 6, h: 4, minW: 3, minH: 3 },
  { i: 'waveform', x: 0, y: 8, w: 12, h: 3, minW: 4, minH: 2 },
  { i: 'trajectory', x: 0, y: 11, w: 6, h: 5, minW: 3, minH: 3 },
  { i: 'gpsMap', x: 6, y: 11, w: 6, h: 5, minW: 3, minH: 3 },
  { i: 'stats', x: 0, y: 16, w: 6, h: 4, minW: 3, minH: 3 },
  { i: 'dives', x: 0, y: 20, w: 12, h: 6, minW: 4, minH: 4 },
  { i: 'energy', x: 0, y: 26, w: 12, h: 4, minW: 4, minH: 3 },
]

export const PANEL_LABELS = {
  spectrogram: 'Spectrogram',
  depthSpeed: 'Depth & Speed',
  prh: 'Pitch / Roll / Heading',
  jerkFluke: 'Jerk & Fluke Stroke',
  waveform: 'Audio Waveform',
  trajectory: '3D Trajectory',
  gpsMap: 'GPS Track Map',
  stats: 'Statistics',
  dives: 'Dive Profile & Table',
  energy: 'ODBA / VeDBA / MSA',
}

export const useLayoutStore = create(
  persist(
    (set, get) => ({
      panels: DEFAULT_PANELS,
      gridLayout: DEFAULT_LAYOUT,
      maximizedId: null,

      togglePanel: (id) =>
        set((s) => ({
          panels: s.panels.map((p) =>
            p.id === id ? { ...p, visible: !p.visible } : p
          ),
        })),

      updateLayout: (layout) => set({ gridLayout: layout }),

      setMaximized: (id) => set({ maximizedId: id }),
      toggleMaximized: (id) =>
        set((s) => ({ maximizedId: s.maximizedId === id ? null : id })),

      resetLayout: () =>
        set({ panels: DEFAULT_PANELS, gridLayout: DEFAULT_LAYOUT, maximizedId: null }),

      getVisiblePanels: () => get().panels.filter((p) => p.visible),

      getVisibleLayout: () => {
        const visible = get().panels.filter((p) => p.visible).map((p) => p.id)
        return get().gridLayout.filter((l) => visible.includes(l.i))
      },
    }),
    {
      name: 'deepecho-layout',
      version: 2,
      partialize: (s) => ({ panels: s.panels, gridLayout: s.gridLayout }),
      // Union persisted panels/layout with the current defaults so panels added
      // in newer versions (e.g. gpsMap) appear for users with a cached layout,
      // while preserving the user's existing visibility/positions.
      merge: (persisted, current) => {
        const p = persisted || {}
        const panelIds = new Set((p.panels || []).map((x) => x.id))
        const panels = [
          ...(p.panels || []),
          ...DEFAULT_PANELS.filter((d) => !panelIds.has(d.id)),
        ]
        const layoutIds = new Set((p.gridLayout || []).map((x) => x.i))
        const gridLayout = [
          ...(p.gridLayout || []),
          ...DEFAULT_LAYOUT.filter((d) => !layoutIds.has(d.i)),
        ]
        return {
          ...current,
          ...p,
          panels: panels.length ? panels : DEFAULT_PANELS,
          gridLayout: gridLayout.length ? gridLayout : DEFAULT_LAYOUT,
        }
      },
    }
  )
)
