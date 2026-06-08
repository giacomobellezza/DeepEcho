import { useSettingsStore } from '../stores/settingsStore'

const THEMES = {
  dark: {
    paper: 'rgba(0,0,0,0)',
    plot: '#09090b',
    grid: '#27272a',
    axis: '#a1a1aa',
    zeroLine: '#52525b',
  },
  light: {
    paper: '#ffffff',
    plot: '#ffffff',
    grid: '#e4e4e7',
    axis: '#3f3f46',
    zeroLine: '#a1a1aa',
  },
}

export function usePlotTheme() {
  const theme = useSettingsStore((s) => s.theme)
  return THEMES[theme] || THEMES.dark
}
