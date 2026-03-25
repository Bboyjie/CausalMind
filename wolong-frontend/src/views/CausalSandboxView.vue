<template>
  <div class="causal-sandbox flex flex-row flex-1 w-full min-h-[500px] animate-fade-in relative bg-white">
    <!-- Main Graph Area (Left 70%) -->
    <div class="flex-1 w-full min-h-0 p-4 pr-0 flex flex-col relative pb-20">
      <div class="mb-4 flex flex-row justify-between items-start pr-4">
        <div>
          <h2 class="text-2xl font-bold text-slate-800 flex items-center">
            <el-icon class="mr-2 text-blue-500"><DataAnalysis /></el-icon>
            因果逻辑沙盘 (DAG)
            <el-button 
              type="warning" 
              plain 
              size="small" 
              :icon="Refresh" 
              class="ml-4" 
              :loading="isRegenerating"
              @click="onRegenerate"
            >重铸逻辑图谱</el-button>
          </h2>
          <p class="text-slate-500 text-sm mt-1">
            基于抽取事实构建的因果图。蓝色为客观约束状态，橙色为您的主观可控变量。
          </p>
          <div v-if="counterfactualInsight" class="mt-3 text-xs text-indigo-700 bg-indigo-50 border border-indigo-100 rounded-lg px-3 py-2 max-w-4xl">
            <span class="font-bold mr-1">反事实洞察:</span>{{ counterfactualInsight }}
          </div>
          <div v-if="topologyTips.length > 0" class="mt-3 flex flex-wrap gap-2 max-w-4xl">
            <el-tag
              v-for="(tip, idx) in topologyTips"
              :key="idx"
              type="warning"
              effect="plain"
              class="!whitespace-normal !h-auto !leading-relaxed py-1"
            >
              {{ tip }}
            </el-tag>
          </div>
        </div>
      </div>

      <div class="flex-1 w-full min-h-0 relative rounded-xl shadow-[inset_0_2px_10px_rgba(0,0,0,0.02)]">
        <Transition name="fade">
          <div
            v-if="rippleBanner"
            class="absolute top-3 left-3 right-3 z-20 bg-white/90 backdrop-blur border border-indigo-100 shadow-sm rounded-lg px-4 py-2"
          >
            <div class="text-xs text-indigo-700 truncate">
              <span class="font-bold mr-1">逻辑推演:</span>{{ rippleBanner.logic_explanation || '推演完成' }}
            </div>
            <div class="text-xs text-rose-700 mt-1 truncate">
              <span class="font-bold mr-1">风险提示:</span>{{ rippleBanner.risk_warning || '暂无关联风险' }}
            </div>
          </div>
        </Transition>
        <GraphRenderer 
          :nodes="nodes" 
          :edges="edges" 
          :is-loading="isLoading"
          :active-node-id="activeNode?.id"
          :ripple-node-ids="rippleNodeIds"
          @node-click="onNodeSelected"
        />
      </div>
    </div>

    <!-- Simulation Panel (Right 30%) -->
    <SimulationPanel 
      :active-node="activeNode"
      :is-simulating="isSimulating"
      :simulation-result="simulationResult"
      :history="historyList"
      :node-topology-details="activeNode?.topology_details || []"
      @intervene="onInterventionSubmit"
      @undo="onUndo"
    />

    <!-- Bottom Actions -->
    <div class="absolute bottom-4 left-4 right-8 flex justify-between items-center bg-white/90 backdrop-blur p-4 rounded-xl shadow-[0_-5px_20px_-10px_rgba(0,0,0,0.1)] border border-slate-200 z-20" style="width: calc(100% - 24rem - 32px);">
      <div class="text-sm text-slate-600 font-medium pl-2">
        <span v-if="simulationResult" class="text-indigo-600">已获得至少一次有效推演结果</span>
        <span v-else>通过右侧面板调试节点并观察推演，满意后可进入下阶段</span>
      </div>
      <el-button 
        type="primary" 
        size="large" 
        class="w-48 tracking-wide shadow-md"
        @click="proceedToWorldLine"
      >
        进入世界线演化
        <el-icon class="ml-2"><Right /></el-icon>
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { DataAnalysis, Right, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import GraphRenderer from '../components/GraphRenderer.vue'
import SimulationPanel from '../components/SimulationPanel.vue'

import { getSandboxGraph, regenerateSandboxGraph, submitIntervention } from '../api/case'
import { useCaseStore } from '../store/caseStore'
import { adaptCausalGraphPayload } from '../utils/adapters/causalGraphAdapter'

const router = useRouter()
const route = useRoute()
const caseStore = useCaseStore()

const caseId = route.params.id as string

const isLoading = ref(true)
const isSimulating = ref(false)
const isRegenerating = ref(false)

const nodes = ref<any[]>([])
const edges = ref<any[]>([])
const activeNode = ref<any>(null)
const simulationResult = ref<any>(null)
const causalTopology = ref<any>({})
const counterfactualInsight = ref('')
const historyList = ref<{ id: number, title: string, desc: string, snapshot: any, lastResult: any }[]>([])
let historyCounter = 0

const topologyTips = ref<string[]>([])
const rippleNodeIds = ref<string[]>([])
const rippleBanner = ref<{ logic_explanation: string, risk_warning: string } | null>(null)
let rippleTimer: number | null = null

onMounted(async () => {
  await fetchGraph()
})

onUnmounted(() => {
  if (rippleTimer) {
    window.clearTimeout(rippleTimer)
    rippleTimer = null
  }
})

const fetchGraph = async () => {
  isLoading.value = true
  try {
    const res = await getSandboxGraph(caseId)
    if (res.code === 200) {
      const adapted = adaptCausalGraphPayload(res.data || {})
      nodes.value = adapted.nodes
      edges.value = adapted.edges
      causalTopology.value = adapted.causalTopology
      counterfactualInsight.value = adapted.counterfactualInsight
      topologyTips.value = adapted.topologyTips
    }
  } catch (err) {
    ElMessage.error('沙盘连通性较低，因果获取失败')
  } finally {
    isLoading.value = false
  }
}

const onRegenerate = async () => {
  isRegenerating.value = true
  try {
    const res = await regenerateSandboxGraph(caseId)
    if (res.code === 200) {
      const adapted = adaptCausalGraphPayload(res.data || {})
      nodes.value = adapted.nodes
      edges.value = adapted.edges
      causalTopology.value = adapted.causalTopology
      counterfactualInsight.value = adapted.counterfactualInsight
      topologyTips.value = adapted.topologyTips
      activeNode.value = null
      simulationResult.value = null
      historyList.value = [] // Wipe history to prevent stale states
      ElMessage.success('沙盘逻辑已重铸完成！')
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '重铸失败，请检查模型配置或代理')
  } finally {
    isRegenerating.value = false
  }
}

const onNodeSelected = (nodeData: any) => {
  activeNode.value = nodeData
  // Optional: clear previous simulation result related to other nodes?
  // simulationResult.value = null
}

const onInterventionSubmit = async (payload: any) => {
  isSimulating.value = true
  
  // Save current graph state for rollback
  const currentSnapshot = JSON.parse(JSON.stringify({ nodes: nodes.value, edges: edges.value }))
  
  // If specific node intervened directly, optimism update
  if (payload.node_id && payload.new_val !== undefined) {
    const nIndex = nodes.value.findIndex(n => n.id === payload.node_id)
    if (nIndex > -1) {
      nodes.value[nIndex] = { ...nodes.value[nIndex], val: payload.new_val }
    }
  }

  try {
    const apiPayload = payload.text ? { text: payload.text } : { interventions: [payload] }
    const res = await submitIntervention(caseId, apiPayload)
    if (res.code === 200) {
      
      historyList.value.push({
        id: ++historyCounter,
        title: payload.text ? '自然语言假设' : '关键变量干预',
        desc: payload.text || `调节节点 [${payload.node_id}]`,
        snapshot: currentSnapshot,
        lastResult: simulationResult.value
      })

      simulationResult.value = res.data
      activeNode.value = null // clear active node to make room for text evaluation
      
      // Update the affected downstream nodes on the graph for visual feedback
      if (res.data.affected_nodes) {
        const touched = new Set<string>()
        res.data.affected_nodes.forEach((an: any) => {
          const tIndex = nodes.value.findIndex(n => n.id === an.id)
          if (tIndex > -1) {
             nodes.value[tIndex] = { ...nodes.value[tIndex], val: an.new_val }
             touched.add(an.id)
          }
        })
        rippleNodeIds.value = Array.from(touched)
        const touchedEdges = edges.value.map((e: any) => ({
          ...e,
          _ripple: touched.has(e.source) || touched.has(e.target)
        }))
        edges.value = touchedEdges
      }
      rippleBanner.value = {
        logic_explanation: res.data.logic_explanation || '',
        risk_warning: res.data.risk_warning || ''
      }
      if (rippleTimer) window.clearTimeout(rippleTimer)
      rippleTimer = window.setTimeout(() => {
        rippleNodeIds.value = []
        edges.value = edges.value.map((e: any) => ({ ...e, _ripple: false }))
        rippleBanner.value = null
      }, 2600)
      
      ElMessage({ message: '推演已生效', type: 'success', duration: 2000 })
    }
  } catch (err) {
    ElMessage.error('推演运算失败，请重试')
    // rollback optimism silently if failed
    nodes.value = currentSnapshot.nodes
  } finally {
    isSimulating.value = false
  }
}

const onUndo = () => {
  if (historyList.value.length === 0) return
  const lastState = historyList.value.pop()!
  
  // Restore graph and results
  nodes.value = lastState.snapshot.nodes
  edges.value = lastState.snapshot.edges
  simulationResult.value = lastState.lastResult
  
  ElMessage.info('已撤销上一步操作')
}

const proceedToWorldLine = () => {
  caseStore.updateStatus('WORLDLINE_EVOLUTION')
  ElMessage.success('周期 4 完成！进入演化期...')
  router.push(`/case/${caseId}/workflow/worldline`)
}
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.4s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
