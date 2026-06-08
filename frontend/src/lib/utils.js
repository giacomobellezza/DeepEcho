import { clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs) {
  return twMerge(clsx(inputs))
}

// Format an elapsed-seconds value according to the chosen mode.
// mode: 'seconds' | 'mmss' | 'hms' | 'absolute'
// deploymentStart: ISO-ish string (from metadata) used only for 'absolute'.
export function formatTime(seconds, mode = 'seconds', deploymentStart = null) {
  const s = Number.isFinite(seconds) ? seconds : 0
  if (mode === 'seconds') return `${s.toFixed(1)}s`
  if (mode === 'mmss') {
    const m = Math.floor(s / 60)
    const rem = s - m * 60
    return `${m}:${rem.toFixed(1).padStart(4, '0')}`
  }
  if (mode === 'hms') {
    const h = Math.floor(s / 3600)
    const m = Math.floor((s % 3600) / 60)
    const sec = Math.floor(s % 60)
    return `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  }
  if (mode === 'absolute') {
    const base = parseDeploymentStart(deploymentStart)
    if (!base) {
      // no anchor → fall back to hh:mm:ss elapsed
      return formatTime(s, 'hms')
    }
    const d = new Date(base.getTime() + s * 1000)
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    const ss = String(d.getSeconds()).padStart(2, '0')
    return `${hh}:${mm}:${ss}`
  }
  return `${s.toFixed(1)}s`
}

// Accept ISO ("2026-05-28T14:05:06.860Z") or "YYYY-MM-DD HH:MM:SS.mmm".
function parseDeploymentStart(value) {
  if (!value) return null
  let v = String(value).trim()
  if (v.includes(' ') && !v.includes('T')) v = v.replace(' ', 'T')
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? null : d
}
