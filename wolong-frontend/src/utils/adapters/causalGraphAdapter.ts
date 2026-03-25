type Dict = Record<string, any>

export interface AdaptedTopologyDetail {
  kind: 'confounder' | 'collider'
  label: string
  cognitiveTrap: string
  detail: string
}

export interface AdaptedCausalNode {
  id: string
  name: string
  type: string
  val: number
  status?: string
  topology_badges?: Array<'confounder' | 'collider'>
  topology_details?: AdaptedTopologyDetail[]
}

export interface AdaptedCausalEdge {
  source: string
  target: string
  polarity: string
  desc: string
  topology_related?: boolean
}

export interface AdaptedCausalGraph {
  nodes: AdaptedCausalNode[]
  edges: AdaptedCausalEdge[]
  causalTopology: Dict
  counterfactualInsight: string
  topologyTips: string[]
}

const asArray = (value: any): any[] => (Array.isArray(value) ? value : [])
const asText = (value: any): string => String(value ?? '').trim()
const lower = (value: any): string => asText(value).toLowerCase()

const nodeType = (raw: any): string => {
  const t = lower(raw)
  if (['action', 'intervention', 'controllable', 'subjective'].includes(t)) return 'action'
  return 'objective'
}

const edgePolarity = (raw: any): string => {
  const p = lower(raw)
  if (['positive', 'up', 'increase'].includes(p)) return 'positive'
  if (['negative', 'down', 'decrease'].includes(p)) return 'negative'
  return 'neutral'
}

const collectNodeSignals = (item: Dict): string[] => {
  const signals: string[] = []
  const add = (v: any) => {
    const t = asText(v)
    if (t) signals.push(t)
  }
  add(item.node_id)
  add(item.node)
  add(item.factor)
  add(item.variable)
  add(item.hidden_variable_C)
  add(item.collider_variable_C)
  add(item.causes_A)
  add(item.causes_B)
  add(item.caused_by_A)
  add(item.caused_by_B)
  asArray(item.nodes).forEach(add)
  return Array.from(new Set(signals))
}

const findNodeIds = (signals: string[], nodes: AdaptedCausalNode[]) => {
  if (!signals.length) return [] as string[]
  const byId = new Map(nodes.map((n) => [lower(n.id), n.id]))
  const byName = new Map(nodes.map((n) => [lower(n.name), n.id]))
  const ids = new Set<string>()
  for (const s of signals) {
    const key = lower(s)
    const id = byId.get(key) || byName.get(key)
    if (id) ids.add(id)
  }
  return Array.from(ids)
}

const extractTopologyList = (topology: Dict, key: 'confounders' | 'colliders') => {
  const list = asArray(topology?.[key]).filter((x) => x && typeof x === 'object')
  return list as Dict[]
}

export const adaptCausalGraphPayload = (data: Dict): AdaptedCausalGraph => {
  const rawNodes = asArray(data?.nodes)
  const rawEdges = asArray(data?.edges)
  const causalTopology = (data?.causal_topology && typeof data.causal_topology === 'object') ? data.causal_topology : {}
  const counterfactualInsight = asText(data?.counterfactual_insight)

  const nodes: AdaptedCausalNode[] = rawNodes.map((n: Dict, idx: number) => ({
    id: asText(n?.id) || `n_${idx + 1}`,
    name: asText(n?.name) || `节点 ${idx + 1}`,
    type: nodeType(n?.type),
    val: Number.isFinite(Number(n?.val)) ? Number(n?.val) : 0.5,
    status: asText(n?.status) || 'variable',
    topology_badges: [],
    topology_details: [],
  }))

  const confounders = extractTopologyList(causalTopology, 'confounders')
  const colliders = extractTopologyList(causalTopology, 'colliders')
  const topologyTips = [...confounders, ...colliders]
    .map((x) => asText(x.cognitive_trap))
    .filter(Boolean)
    .slice(0, 8)

  for (const item of confounders) {
    const detail: AdaptedTopologyDetail = {
      kind: 'confounder',
      label: asText(item.hidden_variable_C) || '混杂因子',
      cognitiveTrap: asText(item.cognitive_trap),
      detail: [asText(item.causes_A), asText(item.causes_B)].filter(Boolean).join(' -> '),
    }
    const ids = findNodeIds(collectNodeSignals(item), nodes)
    for (const id of ids) {
      const target = nodes.find((x) => x.id === id)
      if (!target) continue
      if (!target.topology_badges?.includes('confounder')) target.topology_badges?.push('confounder')
      target.topology_details?.push(detail)
    }
  }

  for (const item of colliders) {
    const detail: AdaptedTopologyDetail = {
      kind: 'collider',
      label: asText(item.collider_variable_C) || '对撞因子',
      cognitiveTrap: asText(item.cognitive_trap),
      detail: [asText(item.caused_by_A), asText(item.caused_by_B)].filter(Boolean).join(' + '),
    }
    const ids = findNodeIds(collectNodeSignals(item), nodes)
    for (const id of ids) {
      const target = nodes.find((x) => x.id === id)
      if (!target) continue
      if (!target.topology_badges?.includes('collider')) target.topology_badges?.push('collider')
      target.topology_details?.push(detail)
    }
  }

  const topologyNodeIds = new Set(
    nodes.filter((n) => (n.topology_badges?.length || 0) > 0).map((n) => n.id)
  )

  const edges: AdaptedCausalEdge[] = rawEdges.map((e: Dict) => {
    const source = asText(e?.source)
    const target = asText(e?.target)
    return {
      source,
      target,
      polarity: edgePolarity(e?.polarity),
      desc: asText(e?.desc) || '因果作用',
      topology_related: topologyNodeIds.has(source) || topologyNodeIds.has(target),
    }
  })

  return {
    nodes,
    edges,
    causalTopology,
    counterfactualInsight,
    topologyTips,
  }
}
