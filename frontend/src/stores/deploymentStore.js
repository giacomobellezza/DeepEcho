import { create } from 'zustand'

export const API_BASE = '/api'

export const useDeploymentStore = create((set, get) => ({
  deployment: null,
  analysisData: null,
  isLoading: false,
  error: null,

  upload: async (wavFile, prhCsv, eventsCsv, metadataFile = null) => {
    set({ isLoading: true, error: null })
    try {
      const formData = new FormData()
      formData.append('wav_file', wavFile)
      formData.append('prh_csv', prhCsv)
      formData.append('events_csv', eventsCsv)
      if (metadataFile) formData.append('metadata_file', metadataFile)

      const res = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Upload failed')
      }

      const data = await res.json()
      set({ deployment: data, isLoading: false })
      return data
    } catch (err) {
      set({ error: err.message, isLoading: false })
      throw err
    }
  },

  analyze: async (deploymentId, startIdx, endIdx) => {
    set({ isLoading: true, error: null })
    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deployment_id: deploymentId,
          start_idx: startIdx,
          end_idx: endIdx,
        }),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Analysis failed')
      }

      const data = await res.json()
      set({ analysisData: data, isLoading: false })
      return data
    } catch (err) {
      set({ error: err.message, isLoading: false })
      throw err
    }
  },

  fetchTrajectory: async (deploymentId, startIdx, endIdx) => {
    try {
      const res = await fetch(`${API_BASE}/trajectory`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          deployment_id: deploymentId,
          start_idx: startIdx,
          end_idx: endIdx,
        }),
      })
      if (!res.ok) return null
      return await res.json()
    } catch {
      return null
    }
  },

  reset: () => set({ deployment: null, analysisData: null, error: null }),
}))
