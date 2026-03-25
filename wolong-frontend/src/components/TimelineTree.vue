<template>
  <div class="timeline-tree w-full h-full relative">
    <div v-if="isLoading" class="absolute inset-0 flex items-center justify-center bg-white/50 z-10">
      <el-icon class="is-loading text-4xl text-blue-500"><Loading /></el-icon>
    </div>
    <v-chart class="chart" :option="chartOption" autoresize />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { getChartTokens } from '../utils/designTokens'

const props = defineProps<{
  paths: any[]
  timelineKeys: string[]
  isLoading: boolean
}>()

const tokens = getChartTokens()

const chartOption = computed(() => {
  // We need to convert the Paths array into a hierarchical Tree for ECharts.
  // A simple representation: Root -> Branches (Baseline, Best, Worst) -> Nodes sequentially
  
  const rootNode = {
    name: '当前状态\n(个人语境注入后)',
    itemStyle: { color: '#3b82f6', borderColor: '#bfdbfe', borderWidth: 2 },
    symbolSize: 40,
    children: props.paths.map(path => {
      let head: any = {}
      let current = head
      
      const configMap: Record<string, {color: string, name: string}> = {
        'baseline': { color: tokens.info, name: '维持现状线 (Baseline)' },
        'best_case': { color: tokens.success, name: '破局线 (Best-case)' },
        'worst_case': { color: tokens.danger, name: '恶化线 (Worst-case)' },
        'custom': { color: tokens.primary, name: '干预重构线 (Custom)' }
      }
      const pConf = configMap[path.type] || configMap['baseline']!
      const colorMap: Record<string, string> = {
        primary: tokens.primary,
        success: tokens.success,
        warning: tokens.warning,
        danger: tokens.danger,
        info: tokens.info
      }
      const branchName = path.branch_name || pConf.name
      const nodeColor = colorMap[path.color] || pConf.color
      
      // Create a chain of nodes for this path
      path.nodes.forEach((n: any, idx: number) => {
        const triggers = Array.isArray(n.triggers) ? n.triggers : []
        const nextNode = {
          name: `${n.time}\n\n${n.desc}`,
          value: branchName,
          symbolSize: 20,
          itemStyle: { color: nodeColor },
          label: {
            position: 'right',
            align: 'left',
            width: 250,
            overflow: 'break',
            formatter: [
              `{title|${branchName} [${n.time}]}`,
              `{desc|${n.desc}}`,
              `{trigger|触发条件: ${triggers.join(', ')}}`
            ].join('\n'),
            rich: {
              title: { fontWeight: 'bold', color: nodeColor, padding: [0,0,5,0] },
              desc: { color: '#475569', lineHeight: 18, width: 220, overflow: 'break' },
              trigger: { color: '#ca8a04', fontSize: 11, padding: [8,0,0,0], width: 220 }
            }
          },
          children: []
        }
        
        if (idx === 0) {
          head = nextNode
          current = head
        } else {
          current.children.push(nextNode)
          current = nextNode
        }
      })
      
      return head
    })
  }

  return {
    tooltip: {
      trigger: 'item',
      triggerOn: 'mousemove',
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      formatter: (params: any) => {
        const node = params?.data || {}
        const name = String(node?.name || '')
        const value = String(node?.value || '世界线分支')
        const normalized = name.split('\n').filter(Boolean)
        const time = normalized[0] || '时间未知'
        const desc = normalized.slice(1).join(' ') || '暂无说明'
        return [
          `<div style="min-width:220px;">`,
          `<div style="font-weight:700;color:#0f172a;">${value}</div>`,
          `<div style="margin-top:6px;color:#334155;">${time}</div>`,
          `<div style="margin-top:4px;color:#475569;line-height:1.4;">${desc}</div>`,
          `</div>`
        ].join('')
      }
    },
    series: [
      {
        type: 'tree',
        data: [rootNode],
        left: '10%',
        right: '25%',
        top: '10%',
        bottom: '10%',
        symbol: 'circle',
        orient: 'horizontal',
        expandAndCollapse: false,
        initialTreeDepth: -1,
        label: {
          position: 'left',
          verticalAlign: 'middle',
          align: 'right',
          fontSize: 12
        },
        leaves: {
          label: {
            position: 'right',
            verticalAlign: 'middle',
            align: 'left'
          }
        },
        lineStyle: {
          width: 3,
          curveness: 0.3
        },
        animationDuration: 500,
        animationDurationUpdate: 750,
        animationEasingUpdate: 'cubicOut'
      }
    ]
  }
})
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
