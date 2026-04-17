import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const SPECIES = [
  { id: 'sperm', name: 'Sperm whale (Physeter macrocephalus)' },
  { id: 'fin', name: 'Fin whale (Balaenoptera physalus)' },
  { id: 'humpback', name: 'Humpback whale (Megaptera novaeangliae)' },
  { id: 'blue', name: 'Blue whale (Balaenoptera musculus)' },
  { id: 'orca', name: 'Orca (Orcinus orca)' },
  { id: 'dolphin', name: 'Bottlenose dolphin (Tursiops truncatus)' },
  { id: 'unknown', name: 'Unknown cetacean' },
]

export const useSettingsStore = create(
  persist(
    (set) => ({
      species: 'sperm',
      setSpecies: (id) => set({ species: id }),
      speciesLock: false,
      setSpeciesLock: (locked) => set({ speciesLock: locked }),
      theme: 'dark',
      setTheme: (t) => set({ theme: t }),
    }),
    { name: 'deepecho-settings' }
  )
)
