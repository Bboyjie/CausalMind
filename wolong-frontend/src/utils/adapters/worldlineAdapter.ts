type Dict = Record<string, any>

export interface AdaptedWorldlineNode {
  time: string
  desc: string
  triggers: string[]
}

export interface AdaptedWorldlinePath {
  type: 'baseline' | 'best_case' | 'worst_case' | 'custom'
  branch_name: string
  color: 'primary' | 'success' | 'warning' | 'danger' | 'info'
  nodes: AdaptedWorldlineNode[]
}

export interface AdaptedWorldlineSummary {
  line_name: string
  core_strategy: string
  dominant_loop: string
  new_primary_contradiction: string
}

export interface AdaptedWorldlineData {
  timelineKeys: string[]
  paths: AdaptedWorldlinePath[]
  summaries: AdaptedWorldlineSummary[]
  dominantLoop: string
  newPrimaryContradiction: string
}

const asArray = (value: any): any[] => (Array.isArray(value) ? value : [])
const asText = (value: any): string => String(value ?? '').trim()
const dedup = (arr: string[]) => Array.from(new Set(arr.filter(Boolean)))

const typeFromLineName = (name: string): AdaptedWorldlinePath['type'] => {
  const t = name.toLowerCase()
  if (t.includes('beta') || t.includes('破局')) return 'best_case'
  if (t.includes('gamma') || t.includes('崩溃') || t.includes('恶化')) return 'worst_case'
  return 'baseline'
}

const normalizePathType = (raw: any): AdaptedWorldlinePath['type'] => {
  const t = asText(raw).toLowerCase()
  if (['best_case', 'best', 'beta'].includes(t)) return 'best_case'
  if (['worst_case', 'worst', 'gamma'].includes(t)) return 'worst_case'
  if (['custom'].includes(t)) return 'custom'
  return 'baseline'
}

const normalizeColor = (raw: any, pathType: AdaptedWorldlinePath['type']): AdaptedWorldlinePath['color'] => {
  const c = asText(raw).toLowerCase()
  if (['primary', 'success', 'warning', 'danger', 'info'].includes(c)) return c as AdaptedWorldlinePath['color']
  if (pathType === 'best_case') return 'success'
  if (pathType === 'worst_case') return 'danger'
  if (pathType === 'custom') return 'primary'
  return 'info'
}

const pathFromWorldline = (line: Dict): AdaptedWorldlinePath => {
  const lineName = asText(line?.line_name) || '世界线'
  const type = typeFromLineName(lineName)
  const evolution = (line?.timeline_evolution && typeof line.timeline_evolution === 'object')
    ? line.timeline_evolution
    : {}
  const nodes = Object.entries(evolution).map(([k, v]) => ({
    time: String(k).replace(/T_plus_/g, 'T+').replace(/_years/g, '年').replace(/_year/g, '年'),
    desc: asText(v),
    triggers: [asText(line?.core_strategy), asText(line?.dominant_loop)].filter(Boolean),
  }))
  return {
    type,
    branch_name: lineName,
    color: normalizeColor(line?.color, type),
    nodes,
  }
}

const normalizePath = (path: Dict): AdaptedWorldlinePath => {
  const type = normalizePathType(path?.type)
  const nodes = asArray(path?.nodes).map((n: Dict) => ({
    time: asText(n?.time) || 'T+?',
    desc: asText(n?.desc) || '暂无描述',
    triggers: dedup(asArray(n?.triggers).map(asText)),
  }))
  return {
    type,
    branch_name: asText(path?.branch_name) || '世界线分支',
    color: normalizeColor(path?.color, type),
    nodes,
  }
}

export const adaptWorldlinePayload = (data: Dict): AdaptedWorldlineData => {
  const summaries = asArray(data?.worldlines).map((line: Dict) => ({
    line_name: asText(line?.line_name) || '未命名世界线',
    core_strategy: asText(line?.core_strategy),
    dominant_loop: asText(line?.dominant_loop),
    new_primary_contradiction: asText(line?.new_primary_contradiction),
  }))

  let paths = asArray(data?.paths).map((x) => normalizePath(x))
  if (!paths.length && summaries.length) {
    paths = asArray(data?.worldlines).map((line) => pathFromWorldline(line))
  }

  const timelineFromPaths = paths.flatMap((p) => p.nodes.map((n) => n.time))
  const timelineKeys = dedup([
    ...asArray(data?.timeline).map(asText),
    ...timelineFromPaths,
  ])

  const dominantLoop = summaries.find((x) => x.dominant_loop)?.dominant_loop || asText(data?.dominant_loop)
  const newPrimaryContradiction =
    summaries.find((x) => x.new_primary_contradiction)?.new_primary_contradiction ||
    asText(data?.new_primary_contradiction)

  return {
    timelineKeys,
    paths,
    summaries,
    dominantLoop,
    newPrimaryContradiction,
  }
}

export const adaptWorldlineInterventionPayload = (data: Dict): AdaptedWorldlinePath[] => {
  const merged = asArray(data?.new_paths)
  return merged.map((x) => normalizePath(x))
}
