type ChartTokenKey =
  | 'primary'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'confounder'
  | 'collider'
  | 'chartBg'

const CSS_VAR_MAP: Record<ChartTokenKey, string> = {
  primary: '--wl-color-primary',
  success: '--wl-color-success',
  warning: '--wl-color-warning',
  danger: '--wl-color-danger',
  info: '--wl-color-info',
  confounder: '--wl-color-confounder',
  collider: '--wl-color-collider',
  chartBg: '--wl-chart-bg',
}

const FALLBACKS: Record<ChartTokenKey, string> = {
  primary: '#3b82f6',
  success: '#22c55e',
  warning: '#f59e0b',
  danger: '#ef4444',
  info: '#94a3b8',
  confounder: '#8b5cf6',
  collider: '#f97316',
  chartBg: '#f8fafc',
}

export interface ChartTokens {
  primary: string
  success: string
  warning: string
  danger: string
  info: string
  confounder: string
  collider: string
  chartBg: string
}

const readCssVar = (name: string, fallback: string) => {
  if (typeof window === 'undefined') return fallback
  const val = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return val || fallback
}

export const getChartTokens = (): ChartTokens => {
  return {
    primary: readCssVar(CSS_VAR_MAP.primary, FALLBACKS.primary),
    success: readCssVar(CSS_VAR_MAP.success, FALLBACKS.success),
    warning: readCssVar(CSS_VAR_MAP.warning, FALLBACKS.warning),
    danger: readCssVar(CSS_VAR_MAP.danger, FALLBACKS.danger),
    info: readCssVar(CSS_VAR_MAP.info, FALLBACKS.info),
    confounder: readCssVar(CSS_VAR_MAP.confounder, FALLBACKS.confounder),
    collider: readCssVar(CSS_VAR_MAP.collider, FALLBACKS.collider),
    chartBg: readCssVar(CSS_VAR_MAP.chartBg, FALLBACKS.chartBg),
  }
}
