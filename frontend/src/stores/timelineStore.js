import { create } from 'zustand'

export const useTimelineStore = create((set, get) => ({
  currentTime: 0,
  selectedInterval: { start_idx: 0, end_idx: 600 },
  activeEventLabel: null,  // e.g. "Creak" — shown as title above charts
  xRange: null,  // [min, max] for synced zoom, null = auto
  isPlaying: false,

  setCurrentTime: (t) => set({ currentTime: t }),
  setSelectedInterval: (interval) => set({ selectedInterval: interval }),
  setActiveEventLabel: (label) => set({ activeEventLabel: label }),
  setXRange: (range) => set({ xRange: range }),

  play: () => set({ isPlaying: true }),
  pause: () => set({ isPlaying: false }),
  togglePlay: () => set((s) => ({ isPlaying: !s.isPlaying })),
}))
