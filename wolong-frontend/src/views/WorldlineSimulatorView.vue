<template>
  <div class="worldline-simulator flex flex-col h-full animate-fade-in relative">
    
    <div class="p-4 pb-2 border-b border-slate-100 flex justify-between items-center z-10 bg-white">
      <div>
        <h2 class="text-2xl font-bold text-slate-800 flex items-center">
          <el-icon class="mr-2 text-blue-500"><Share /></el-icon>
          世界线分支推演
        </h2>
        <p class="text-slate-500 text-sm mt-1">
          基于沙盘结构叠加个人语境后，推演未来 {{ timelineKeys.length }} 个阶段的可能性分支。
        </p>
      </div>
      <div class="flex flex-row gap-2" v-if="hasContext">
        <el-button @click="showContextModal = true" plain icon="Edit">
          修改约束语境
        </el-button>
        <el-button type="warning" plain icon="Refresh" :loading="isRegenerating" @click="onRegenerate">
          重铸推演
        </el-button>
      </div>
    </div>

    <div class="flex-1 w-full min-h-0 relative bg-slate-50 flex rounded-b-xl shadow-inner pb-20">
      
      <!-- Timeline Graph Area -->
      <div class="flex-1 relative border-r border-slate-200">
        <div
          v-if="hasContext && (globalDominantLoop || globalNewPrimaryContradiction)"
          class="mx-4 mt-3 bg-white/90 border border-slate-200 rounded-lg px-3 py-2 shadow-sm text-xs"
        >
          <div class="text-slate-700">
            <span class="font-bold text-indigo-700 mr-1">主导回路:</span>{{ globalDominantLoop || '暂无' }}
          </div>
          <div class="text-slate-700 mt-1">
            <span class="font-bold text-amber-700 mr-1">新主要矛盾:</span>{{ globalNewPrimaryContradiction || '暂无' }}
          </div>
        </div>
        <div v-if="hasContext && worldlineSummaries.length > 0" class="px-4 pt-4 pb-2 grid grid-cols-1 lg:grid-cols-3 gap-3">
          <div
            v-for="(line, idx) in worldlineSummaries"
            :key="idx"
            class="bg-white border border-slate-200 rounded-lg px-3 py-2 shadow-sm"
          >
            <div class="text-sm font-bold text-slate-800 truncate">{{ line.line_name || `世界线 ${idx + 1}` }}</div>
            <div class="text-xs text-slate-500 mt-1 line-clamp-2">策略：{{ line.core_strategy || '—' }}</div>
            <div class="text-xs text-slate-600 mt-1 line-clamp-2">主导回路：{{ line.dominant_loop || '—' }}</div>
            <div class="text-xs text-amber-700 mt-2 line-clamp-2">新矛盾：{{ line.new_primary_contradiction || '—' }}</div>
          </div>
        </div>
        <TimelineTree 
          v-if="hasContext" 
          :paths="paths" 
          :timeline-keys="timelineKeys" 
          :is-loading="isLoading" 
        />
        
        <div v-else class="absolute inset-0 flex flex-col items-center justify-center">
          <template v-if="isLoading">
            <el-icon class="is-loading text-4xl text-blue-500 mb-4"><Share /></el-icon>
            <p class="text-slate-500">正在计算世界线，请稍候...</p>
          </template>
          <template v-else>
            <el-icon class="text-5xl text-slate-300 mb-4"><MagicStick /></el-icon>
            <p class="text-slate-500 mb-4">世界线处于坍缩态，未确立个人锚点</p>
            <el-button type="primary" size="large" @click="showContextModal = true">
              注入个人信息并展开推演
            </el-button>
          </template>
        </div>
      </div>

      <!-- Text Intervention Sandbox -->
      <div v-if="hasContext" class="w-80">
        <WorldlineInterventionPanel 
          :is-simulating="isSimulating"
          :simulation-result="simulationResult"
          :history="historyList"
          @intervene="handleIntervene"
          @undo="handleUndo"
        />
      </div>
      
    </div>

    <!-- Bottom Actions -->
    <div v-if="hasContext" class="absolute bottom-4 left-4 right-8 flex justify-between items-center bg-white/90 backdrop-blur p-4 rounded-xl shadow-[0_-5px_20px_-10px_rgba(0,0,0,0.1)] border border-slate-200 z-20" style="width: calc(100% - 32px);">
      <div class="text-sm text-slate-600 font-medium pl-2">
        <span>推演已完成，可点击分支节点查看详情。满意后生成最终报告。</span>
      </div>
      <el-button 
        type="primary" 
        size="large" 
        class="w-48 tracking-wide shadow-md"
        @click="generateWhitepaper"
        :loading="isGenerating"
      >
        生成破局白皮书
        <el-icon class="ml-2"><Document /></el-icon>
      </el-button>
    </div>

    <ContextInjectionModal
      v-model="showContextModal"
      :probes="probeQuestions"
      @submit="handleContextSubmit"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Share, MagicStick, Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import TimelineTree from '../components/TimelineTree.vue'
import ContextInjectionModal from '../components/ContextInjectionModal.vue'
import WorldlineInterventionPanel from '../components/WorldlineInterventionPanel.vue'
import { submitContext, getWorldline, getWorldlineProbe, submitWorldlineIntervention, regenerateWorldline } from '../api/case'
import { useCaseStore, CaseStatus } from '../store/caseStore'
import { adaptWorldlinePayload, adaptWorldlineInterventionPayload } from '../utils/adapters/worldlineAdapter'

const router = useRouter()
const route = useRoute()
const caseStore = useCaseStore()

const caseId = route.params.id as string

const showContextModal = ref(false)
const hasContext = ref(false)
const isLoading = ref(false)
const isSimulating = ref(false)
const isGenerating = ref(false)
const isRegenerating = ref(false)

const timelineKeys = ref<string[]>([])
const paths = ref<any[]>([])
const worldlineSummaries = ref<any[]>([])
const probeQuestions = ref<any[]>([])
const simulationResult = ref<any>(null)
const historyList = ref<{ id: number, title: string, desc: string, snapshot: any, lastResult: any }[]>([])
let historyCounter = 0
const globalDominantLoop = ref('')
const globalNewPrimaryContradiction = ref('')

onMounted(async () => {
  isLoading.value = true
  try {
    const res = await getWorldline(caseId)
    if (res.code === 200 && res.data.timeline && res.data.timeline.length > 0) {
      const adapted = adaptWorldlinePayload(res.data || {})
      hasContext.value = true
      timelineKeys.value = adapted.timelineKeys
      paths.value = adapted.paths
      worldlineSummaries.value = adapted.summaries
      globalDominantLoop.value = adapted.dominantLoop
      globalNewPrimaryContradiction.value = adapted.newPrimaryContradiction
    }
  } catch (err) {
    // Expected 404 or empty if no worldline exists yet, don't show error, just wait for user to inject context
  } finally {
    await loadProbeQuestions()
    isLoading.value = false
  }
})

const loadProbeQuestions = async () => {
  try {
    const res = await getWorldlineProbe(caseId)
    if (res.code === 200) {
      probeQuestions.value = res.data.questions || []
    }
  } catch (err) {
    probeQuestions.value = []
  }
}

const handleContextSubmit = async (contextData: any) => {
  isLoading.value = true
  try {
    // 1. Submit Context
    await submitContext(caseId, contextData)
    // 2. Fetch Worldline
    const res = await getWorldline(caseId)
    if (res.code === 200 && res.data?.timeline?.length > 0 && res.data?.paths?.length > 0) {
      const adapted = adaptWorldlinePayload(res.data || {})
      hasContext.value = true
      timelineKeys.value = adapted.timelineKeys
      paths.value = adapted.paths
      worldlineSummaries.value = adapted.summaries
      globalDominantLoop.value = adapted.dominantLoop
      globalNewPrimaryContradiction.value = adapted.newPrimaryContradiction
      ElMessage.success('世界线重构完成')
    } else {
      ElMessage.error('模型返回空世界线，请补充语境后重试')
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '世界线推演失败')
  } finally {
    isLoading.value = false
  }
}

const onRegenerate = async () => {
  isRegenerating.value = true
  try {
    const res = await regenerateWorldline(caseId)
    if (res.code === 200 && res.data?.timeline?.length > 0 && res.data?.paths?.length > 0) {
      const adapted = adaptWorldlinePayload(res.data || {})
      timelineKeys.value = adapted.timelineKeys
      paths.value = adapted.paths
      worldlineSummaries.value = adapted.summaries
      globalDominantLoop.value = adapted.dominantLoop
      globalNewPrimaryContradiction.value = adapted.newPrimaryContradiction
      simulationResult.value = null
      historyList.value = [] // Wipe history to prevent stale states
      ElMessage.success('世界线重铸完成！')
    } else {
      ElMessage.error('重铸失败：模型返回空世界线')
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '重铸失败，请检查模型配置或前置逻辑节点满⾜度')
  } finally {
    isRegenerating.value = false
  }
}

const handleIntervene = async (payload: { text: string }) => {
  if (!payload.text) return
  isSimulating.value = true
  
  // Snapshot current state
  const snapshot = JSON.parse(JSON.stringify(paths.value))
  
  try {
    const res = await submitWorldlineIntervention(caseId, payload.text)
    if (res.code === 200) {
      // Create new history item
      historyList.value.push({
         id: ++historyCounter,
         title: '世界线文本干预',
         desc: payload.text,
         snapshot: snapshot,
         lastResult: simulationResult.value
      })
      
      // Update graph and results
      if (res.data.new_paths) {
         const adaptedNewPaths = adaptWorldlineInterventionPayload(res.data || {})
         paths.value = [...paths.value, ...adaptedNewPaths]
         timelineKeys.value = Array.from(new Set(paths.value.flatMap((p: any) => p.nodes.map((n: any) => n.time))))
      }
      simulationResult.value = {
        logic_explanation: res.data.logic_explanation,
        risk_warning: res.data.risk_warning
      }
      
      ElMessage.success('世界线重组完成')
    }
  } catch(err: any) {
    ElMessage.error(err?.response?.data?.detail || '推演响应失败')
  } finally {
    isSimulating.value = false
  }
}

const handleUndo = () => {
  if (historyList.value.length === 0) return
  const lastState = historyList.value.pop()!
  
  // Restore timeline graph and results
  paths.value = lastState.snapshot
  simulationResult.value = lastState.lastResult
  
  ElMessage.info('已撤销上一步干预')
}

const generateWhitepaper = () => {
  if (isGenerating.value) return
  isGenerating.value = true
  caseStore.updateStatus(CaseStatus.WHITE_PAPER)
  router.push(`/case/${caseId}/workflow/whitepaper`).finally(() => {
    isGenerating.value = false
  })
}
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.4s ease-out;
}
</style>
