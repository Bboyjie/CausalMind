<template>
  <div class="graph-renderer w-full h-full bg-slate-50 relative rounded-xl border border-slate-200 overflow-hidden">
    <div v-if="isLoading" class="absolute inset-0 flex items-center justify-center bg-white/80 z-10 transition-opacity">
      <el-icon class="is-loading text-3xl text-blue-500"><Loading /></el-icon>
    </div>
    <v-chart ref="chartRef" v-show="!isLoading" class="chart" :option="chartOption" autoresize @click="handleNodeClick" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { getChartTokens } from '../utils/designTokens'

const props = defineProps<{
  nodes: any[]
  edges: any[]
  isLoading: boolean
  activeNodeId?: string | null
  rippleNodeIds?: string[]
}>()

const emit = defineEmits(['node-click'])
const chartRef = ref<any>(null)
const tokens = getChartTokens()

const chartOption = computed(() => {
  const chartNodes = props.nodes.map(n => {
    const isObjective = n.type === 'objective'
    const isActive = props.activeNodeId === n.id
    const badges = Array.isArray(n.topology_badges) ? n.topology_badges : []
    const hasConfounder = badges.includes('confounder')
    const hasCollider = badges.includes('collider')
    const badgeText = [hasConfounder ? '混杂因子' : '', hasCollider ? '对撞因子' : ''].filter(Boolean).join(' / ')
    const baseColor = isObjective ? '#60a5fa' : '#fb923c'
    const tokenColor = hasConfounder ? tokens.confounder : hasCollider ? tokens.collider : baseColor
    
    return {
      id: n.id,
      name: n.name,
      symbolSize: isObjective ? 70 : 60,
      symbol: isObjective ? 'circle' : 'roundRect',
      itemStyle: {
        color: tokenColor,
        borderColor: isActive ? tokens.primary : (isObjective ? '#93c5fd' : '#fdba74'),
        borderWidth: isActive ? 4 : (badges.length ? 3 : 2),
        shadowBlur: isActive || badges.length ? 12 : 0,
        shadowColor: hasConfounder ? `${tokens.confounder}66` : (hasCollider ? `${tokens.collider}66` : 'rgba(0,0,0,0.2)')
      },
      label: {
        show: true,
        formatter: badgeText ? `{b}\n{badge|${badgeText}}\n{val|值: ${n.val}}` : `{b}\n\n{val|值: ${n.val}}`,
        rich: {
          badge: {
            fontSize: 10,
            color: '#f8fafc',
            backgroundColor: hasConfounder ? tokens.confounder : tokens.collider,
            borderRadius: 3,
            padding: [2, 4],
            lineHeight: 16,
          },
          val: {
            fontSize: 10,
            color: '#fff'
          }
        }
      },
      tooltip: {
        formatter: [
          `<div><b>${n.name}</b></div>`,
          badgeText ? `<div style="margin-top:4px;color:#334155;">${badgeText}</div>` : '',
          `<div style="margin-top:4px;color:#64748b;">当前值: ${n.val}</div>`
        ].join('')
      },
      // Pass original data for click handler
      data: n
    }
  })

  const chartEdges = props.edges.map(e => ({
    source: e.source,
    target: e.target,
    label: {
      show: true,
      formatter: e.desc,
      fontSize: 10,
      color: '#64748b'
    },
    lineStyle: {
      color: e.polarity === 'positive' ? tokens.success : (e.polarity === 'negative' ? tokens.danger : tokens.info),
      width: e._ripple ? 4 : (e.topology_related ? 3 : 2),
      curveness: 0.2,
      type: e._ripple ? 'solid' : (e.topology_related ? 'dotted' : (e.polarity === 'positive' ? 'solid' : 'dashed')),
      opacity: e._ripple ? 1 : 0.82
    }
  }))

  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      textStyle: { color: '#0f172a' }
    },
    animationDurationUpdate: 1000,
    animationEasingUpdate: 'quinticInOut',
    series: [
      {
        type: 'graph',
        layout: 'force',
        force: {
          repulsion: 800,
          edgeLength: 200,
          layoutAnimation: true
        },
        roam: true,
        label: {
          position: 'inside',
          color: '#fff',
          fontWeight: 'bold',
          fontSize: 12
        },
        edgeSymbol: ['circle', 'arrow'],
        edgeSymbolSize: [4, 10],
        data: chartNodes,
        edges: chartEdges
      }
    ]
  }
})

const handleNodeClick = (params: any) => {
  if (params.dataType === 'node') {
    emit('node-click', params.data)
  }
}

watch(
  () => props.rippleNodeIds,
  (ids) => {
    if (!chartRef.value) return
    const chart = chartRef.value.chart
    if (!chart) return
    chart.dispatchAction({ type: 'downplay', seriesIndex: 0 })
    if (!ids?.length) return
    for (const id of ids) {
      chart.dispatchAction({ type: 'highlight', seriesIndex: 0, dataId: id })
    }
  },
  { deep: true }
)
</script>

<style scoped>
.chart {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  width: 100%;
}
</style>
