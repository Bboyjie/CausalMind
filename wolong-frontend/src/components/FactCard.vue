<template>
  <el-card 
    class="fact-card mb-4 relative overflow-hidden transition-all duration-300" 
    :class="[cardClass, { 'opacity-50 grayscale': isDiscarded }]"
    shadow="hover"
  >
    <div class="absolute top-0 left-0 w-1 h-full" :class="indicatorColor"></div>
    
    <div class="flex justify-between items-start mb-3 pl-2">
      <div class="flex items-center gap-2">
        <el-tag :type="tagType" effect="dark" size="small">{{ typeLabel }}</el-tag>
        <el-tag v-if="isUseful" type="success" effect="plain" size="small" class="font-bold flex items-center">
          <el-icon class="mr-1"><Select /></el-icon>已采纳
        </el-tag>
        <el-tag
          v-if="fact.bound_fact_ids && fact.bound_fact_ids.length > 0"
          type="info"
          effect="plain"
          size="small"
          class="font-bold"
        >
          绑定信息池 {{ fact.bound_fact_ids.length }} 条
        </el-tag>
      </div>
      
      <div v-if="!isDiscarded" class="space-x-2">
        <el-button size="small" :type="isUseful ? 'success' : 'default'" :plain="!isUseful" circle title="有价值" @click="handleFeedback('USEFUL')">
          <el-icon><Select /></el-icon>
        </el-button>
        <el-button size="small" type="danger" plain circle title="标为无价值/错误" @click="handleFeedback('LOW_VALUE')">
          <el-icon><CloseBold /></el-icon>
        </el-button>
      </div>
      <el-tag v-else type="info" size="small">已被折叠</el-tag>
    </div>

    <p class="text-slate-800 text-base leading-relaxed pl-2 mb-4 font-medium">
      {{ fact.content }}
    </p>
    <div v-if="fact.element_name || fact.category" class="pl-2 mb-3 text-xs text-slate-500">
      <span v-if="fact.element_name" class="mr-3">元素：{{ fact.element_name }}</span>
      <span v-if="fact.category">分类：{{ fact.category }}</span>
    </div>

    <!-- Audit Alerts (Risks/Bias) -->
    <div v-if="fact.audit_alerts && fact.audit_alerts.length > 0 && !isDiscarded" class="pl-2 mb-4">
      <div v-for="(alert, index) in fact.audit_alerts" :key="index" class="bg-amber-50 text-amber-800 text-sm p-3 rounded-lg border border-amber-100 flex items-start">
        <el-icon class="mt-0.5 mr-2 text-amber-500"><WarningFilled /></el-icon>
        <div>
          <span class="font-bold">{{ alert.type === 'BIAS' ? '认知偏差分析' : '逻辑风险提示' }}: </span>
          <span>{{ alert.message }}</span>
        </div>
      </div>
    </div>

    <!-- Counter Evidence -->
    <div v-if="fact.counter_evidence && !isDiscarded" class="pl-2 mb-4">
       <div class="bg-slate-50 text-slate-600 text-sm p-3 rounded-lg border border-slate-200 border-l-4 border-l-slate-400">
        <span class="font-bold">反面证据: </span>
        <span>{{ fact.counter_evidence }}</span>
      </div>
    </div>

    <!-- Footer Actions -->
    <div class="flex justify-between items-center mt-4 pt-3 border-t border-slate-100 pl-2">
      <div class="flex items-center gap-3">
        <el-button
          v-if="fact.evidence_ids && fact.evidence_ids.length > 0"
          type="primary"
          link
          @click="traceSources"
          :disabled="isDiscarded"
        >
          <el-icon class="mr-1"><Search /></el-icon>
          审计证据溯源 ({{ fact.evidence_ids.length }} 篇)
        </el-button>
        <span v-else class="text-xs text-slate-400 italic">无明确引文支持</span>
      </div>
      <el-button type="info" link @click="viewReasoningChain">
        查看思维链
      </el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Select, CloseBold, WarningFilled, Search } from '@element-plus/icons-vue'
import { useAuditStore } from '../store/auditStore'

const props = defineProps<{
  fact: any
  isUseful?: boolean
}>()

const emit = defineEmits(['feedback', 'view-chain'])
const auditStore = useAuditStore()

const isDiscarded = ref(false)

const tagMap: Record<string, { label: string, type: string, color: string, borderClass: string }> = {
  FACT: { label: '客观事实', type: 'primary', color: 'bg-blue-500', borderClass: 'border-blue-100' },
  INFERENCE: { label: '主观推断', type: 'warning', color: 'bg-orange-400', borderClass: 'border-orange-100' },
  ASSUMPTION: { label: '前置假设', type: 'danger', color: 'bg-rose-500', borderClass: 'border-rose-100' },
  RISK: { label: '风险变量', type: 'danger', color: 'bg-rose-500', borderClass: 'border-rose-100' },
  CONTRADICTION: { label: '矛盾证据', type: 'warning', color: 'bg-orange-400', borderClass: 'border-orange-100' },
  CAUSAL_LINK: { label: '因果线索', type: 'success', color: 'bg-emerald-500', borderClass: 'border-emerald-100' }
}

const typeConfig = computed(() => tagMap[props.fact.type] || { label: '未知', type: 'info', color: 'bg-slate-400', borderClass: 'border-slate-100' })

const tagType = computed(() => typeConfig.value.type)
const typeLabel = computed(() => typeConfig.value.label)
const indicatorColor = computed(() => typeConfig.value.color)

const cardClass = computed(() => {
  if (auditStore.selectedFactId === props.fact.id) {
    return 'ring-2 ring-blue-400 shadow-md transform -translate-y-1'
  }
  if (props.isUseful) {
    return 'ring-2 ring-green-400 border-green-200 bg-green-50 shadow-sm'
  }
  return typeConfig.value.borderClass
})

const handleFeedback = (type: string) => {
  if (type === 'LOW_VALUE') {
    isDiscarded.value = true
  }
  emit('feedback', { id: props.fact.id, type })
}

const traceSources = () => {
  auditStore.setSelectedFact(props.fact.id)
}

const viewReasoningChain = () => {
  emit('view-chain', props.fact)
}
</script>

<style scoped>
.fact-card {
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}
</style>
