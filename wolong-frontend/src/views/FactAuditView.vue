<template>
  <div class="fact-audit flex flex-col h-full animate-fade-in relative">
    <div class="flex-1 overflow-y-auto p-4 sm:p-8 pb-24">
      
      <!-- Header -->
      <div class="mb-6 flex justify-between items-end">
        <div>
          <h2 class="text-2xl font-bold text-slate-800 flex items-center">
            <el-icon class="mr-2 text-blue-500"><DocumentChecked /></el-icon>
            认知拆解与事实审计
          </h2>
          <p class="text-slate-500 text-sm mt-1">从 {{ totalSources }} 篇原始信息源中提取到了 {{ validFactsCount }} 条有效事实与推论</p>
        </div>
        
        <div class="flex gap-2">
          <el-tag type="primary" effect="dark">客观事实: {{ counts.fact }}</el-tag>
          <el-tag type="warning" effect="dark">主观推论: {{ counts.inference }}</el-tag>
          <el-tag type="danger" effect="dark">前置假设: {{ counts.assumption }}</el-tag>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="flex flex-col items-center justify-center py-20 mt-12">
        <el-icon class="is-loading text-4xl text-blue-500 mb-4"><Loading /></el-icon>
        <p class="text-slate-500 font-medium">代理 AI 正在交叉对比信源并提取事实...</p>
      </div>

      <!-- Facts List -->
      <div v-else-if="facts.length > 0" class="max-w-4xl mx-auto space-y-2">
        <TransitionGroup name="list">
          <FactCard 
            v-for="fact in facts" 
            :key="fact.id" 
            :fact="fact" 
            :is-useful="fact._useful"
            @feedback="onFeedback"
            @view-chain="onViewChain"
          />
        </TransitionGroup>
      </div>
      
      <!-- Empty/Error State -->
      <div v-else class="py-20 text-center text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-300">
        没有提取到足够的事实或网络错误
      </div>
    </div>

    <!-- Sliding Drawer for Source Tracing -->
    <SourceTraceDrawer :case-id="caseId" :facts="facts" />
    <el-dialog v-model="showChainDialog" title="思维链下钻" width="680px" :close-on-click-modal="false">
      <div class="space-y-3 text-sm">
        <div class="bg-slate-50 border border-slate-200 rounded-lg p-3">
          <div class="text-xs font-bold text-slate-600 mb-1">对象</div>
          <div class="text-slate-800">{{ chainFactMeta }}</div>
        </div>
        <div class="bg-slate-50 border border-slate-200 rounded-lg p-3">
          <div class="text-xs font-bold text-slate-600 mb-1">推理说明</div>
          <div class="text-slate-700 whitespace-pre-wrap">{{ chainText || '暂无思维链明细。' }}</div>
        </div>
        <div class="bg-slate-50 border border-slate-200 rounded-lg p-3">
          <div class="text-xs font-bold text-slate-600 mb-1">结构化中间结果</div>
          <pre class="text-xs text-slate-700 whitespace-pre-wrap max-h-80 overflow-auto">{{ chainJson }}</pre>
        </div>
      </div>
    </el-dialog>

    <!-- Bottom Actions -->
    <div class="absolute bottom-0 left-0 right-0 flex justify-between items-center bg-white p-4 rounded-xl shadow-[0_-10px_40px_-15px_rgba(0,0,0,0.1)] border border-slate-100 z-10 m-2">
      <div class="text-sm text-slate-500">
        请审核事实卡片，标记出无价值或明显错误的推论。
      </div>
      <el-button type="primary" size="large" @click="proceedToSandbox">
        进入因果逻辑沙盘
        <el-icon class="ml-2"><Right /></el-icon>
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { DocumentChecked, Loading, Right } from '@element-plus/icons-vue'
import FactCard from '../components/FactCard.vue'
import SourceTraceDrawer from '../components/SourceTraceDrawer.vue'
import { getAuditElements, getFacts, feedbackFact } from '../api/case'
import { useCaseStore } from '../store/caseStore'
import { useAuditStore } from '../store/auditStore'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const caseStore = useCaseStore()
const auditStore = useAuditStore()

const caseId = route.params.id as string
const isLoading = ref(true)
const facts = ref<any[]>([])
const showChainDialog = ref(false)
const chainText = ref('')
const chainJson = ref('')
const chainFactMeta = ref('')

// Assuming this came from Cycle 2
const totalSources = computed(() => caseStore.collectionStats?.valid_sources || 85)

const validFactsCount = computed(() => facts.value.filter(f => !f._discarded).length)

const normalizeAuditType = (type: string) => {
  const t = String(type || '').toUpperCase()
  if (t === 'FACT') return 'fact'
  if (t === 'ASSUMPTION') return 'assumption'
  return 'inference'
}

const counts = computed(() => {
  return facts.value.reduce((acc, f) => {
    if (!f._discarded) {
      const normalized = normalizeAuditType(f.type)
      if (normalized === 'fact') acc.fact++
      else if (normalized === 'inference') acc.inference++
      else if (normalized === 'assumption') acc.assumption++
    }
    return acc
  }, { fact: 0, inference: 0, assumption: 0 })
})

onMounted(async () => {
  // Clear any previously selected fact
  auditStore.setSelectedFact(null)
  
  try {
    const res = await getAuditElements(caseId)
    if (res.code === 200 && (res.data || []).length > 0) {
      // Add local _discarded and _useful properties for UI tracking without mutating API data strictly
      facts.value = res.data.map((f: any) => ({ ...f, _discarded: false, _useful: false }))
      return
    }
    // Fallback to raw fact cards when audit endpoint is empty.
    const fallback = await getFacts(caseId)
    if (fallback.code === 200) {
      facts.value = fallback.data.map((f: any) => ({ ...f, _discarded: false, _useful: false }))
    }
  } catch (error) {
    try {
      const fallback = await getFacts(caseId)
      if (fallback.code === 200) {
        facts.value = fallback.data.map((f: any) => ({ ...f, _discarded: false, _useful: false }))
      } else {
        ElMessage.error('无法加载事实列表')
      }
    } catch {
      ElMessage.error('无法加载事实列表')
    }
  } finally {
    isLoading.value = false
  }
})

// Clean up state when leaving route
onUnmounted(() => {
  auditStore.setSelectedFact(null)
})

const onFeedback = async ({ id, type }: { id: string, type: string }) => {
  try {
    await feedbackFact(caseId, id, type as any)
    if (type === 'LOW_VALUE') {
      const idx = facts.value.findIndex(f => f.id === id)
      if (idx !== -1) {
        facts.value[idx]._discarded = true
        facts.value[idx]._useful = false
      }
      ElMessage({ message: '已标记为无价值并折叠', type: 'info', duration: 2000 })
    } else {
      const idx = facts.value.findIndex(f => f.id === id)
      if (idx !== -1) {
        facts.value[idx]._useful = true
      }
      ElMessage.success('已标记为高价值事实')
    }
    
    // Auto-close drawer if the discarded fact was the actively traced one
    if (auditStore.selectedFactId === id && type === 'LOW_VALUE') {
       auditStore.setSelectedFact(null)
    }
  } catch (err) {
    ElMessage.error('反馈同步失败')
  }
}

const onViewChain = (fact: any) => {
  const raw = fact?.reasoning_chain
    || fact?.thinking_chain
    || fact?.logic_trace
    || fact?.raw_whitepaper
    || fact?.raw_model_output
    || null
  chainText.value = String(fact?.causal_deduction || fact?.dialectical_risk || fact?.summary || '')
  chainJson.value = raw ? JSON.stringify(raw, null, 2) : '暂无可展示的结构化推理链数据。'
  chainFactMeta.value = `${fact?.element_name || '未命名元素'} / ${fact?.category || '未分类'}`
  showChainDialog.value = true
}

const proceedToSandbox = () => {
  caseStore.updateStatus('GRAPH_BUILDING')
  ElMessage.success('审计完成！进入因果沙盘构建...')
  router.push(`/case/${caseId}/workflow/sandbox`)
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

.list-enter-active,
.list-leave-active {
  transition: all 0.5s ease;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
</style>
