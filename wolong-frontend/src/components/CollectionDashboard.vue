<template>
  <div class="collection-dashboard w-full py-16 flex flex-col items-center relative overflow-hidden bg-slate-50/50 rounded-3xl border border-white shadow-sm mt-8">
    
    <!-- Header -->
    <div class="z-10 text-center mb-10">
      <h2 class="text-xl font-bold text-slate-700 flex items-center justify-center gap-2">
        <span>🎯</span> 正在洞察
      </h2>
      <p class="text-slate-500 mt-2 font-medium">平台 [{{ currentPlatformLabel }}] &middot; {{ progress < 100 ? '正在高速获取数据' : '数据获取完毕' }}</p>
    </div>

    <!-- Breathing Ring Center -->
    <div class="z-10 relative flex justify-center items-center w-64 h-64 mb-12">
      <!-- Pulsing Rings -->
      <div class="absolute inset-0 bg-blue-400 rounded-full blur-3xl opacity-20 animate-pulse" 
           :class="{'bg-indigo-400': isFiltering, 'bg-emerald-400': isDone}"></div>
      <div class="absolute inset-4 bg-white/60 rounded-full backdrop-blur-sm border border-white/80 shadow-xl flex flex-col items-center justify-center transition-all duration-1000"
           :class="{'animate-bounce-slow': !isDone, 'scale-105': isDone}">
        
        <div class="text-4xl mb-2 transition-transform duration-500" :class="{'scale-125': isDone}">
          {{ statusEmoji }}
        </div>
        
        <div class="text-3xl font-black bg-clip-text text-transparent bg-gradient-to-br from-slate-700 to-slate-900 drop-shadow-sm">
          {{ displayProgress }}%
        </div>
        
      </div>
      
      <!-- SVG Spinners -->
      <svg class="absolute inset-0 w-full h-full -rotate-90 origin-center" v-if="!isDone">
        <circle cx="128" cy="128" r="120" stroke="currentColor" stroke-width="2" fill="none" class="text-slate-200" />
        <circle cx="128" cy="128" r="120" stroke="currentColor" stroke-width="6" fill="none" stroke-linecap="round" 
                :stroke-dasharray="2 * Math.PI * 120"
                :stroke-dashoffset="2 * Math.PI * 120 * (1 - (displayProgress / 100))"
                class="transition-all duration-700 ease-out"
                :class="{'text-blue-500': !isFiltering, 'text-indigo-500': isFiltering}" />
      </svg>
    </div>

    <!-- Dynamic Status Text -->
    <div class="z-10 text-center h-16 w-full max-w-md px-6 flex items-center justify-center rounded-2xl bg-white shadow-sm border border-slate-100 transition-all">
      <p class="text-slate-600 font-medium text-lg animate-fade-in" :key="humorousText">
        {{ humorousText }}
      </p>
    </div>

    <!-- Bottom Teaser (Accumulated Pool) -->
    <div class="z-10 mt-12 w-full max-w-lg px-4">
      <div class="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-2xl p-6 border border-blue-100 shadow-inner flex flex-col items-center">
        <p class="text-sm font-bold text-slate-500 mb-2 uppercase tracking-wide">智能提炼成果</p>
        <div class="flex items-baseline gap-2 mb-4">
          <span class="text-4xl font-black text-indigo-600 tabular-nums tracking-tighter">{{ extractedFactsCount }}</span>
          <span class="text-slate-600 font-medium">条高价值情报</span>
        </div>
        
        <el-button 
          v-if="extractedFactsCount > 0"
          type="primary" 
          size="large" 
          round 
          class="w-full sm:w-auto px-8 !bg-indigo-600 hover:!bg-indigo-700 border-none shadow-md hover:shadow-lg transition-all"
          @click="goToFacts">
          👉 边等边看 (前往信息池)
        </el-button>
        <p v-else class="text-xs text-slate-400">正在提炼中，请稍候...</p>
      </div>
    </div>
    
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const props = defineProps<{
  progress: number
  status: string
  current_platform?: string | null
  filtering_progress?: number
  filtering_status?: string | null
  stats?: any
}>()

const caseId = computed(() => route.params.id as string)

const extractedFactsCount = computed(() => {
  if (props.stats && typeof props.stats.extracted_facts === 'number') {
    return props.stats.extracted_facts
  }
  return 0
})

const isFiltering = computed(() => props.filtering_status === 'PROCESSING')
const isDone = computed(() => props.status === 'COMPLETED' || props.filtering_status === 'COMPLETED')

// Smooth total progress combining scrape + filter
const displayProgress = computed(() => {
  if (isDone.value) return 100
  // Approx mapping: scraping is ~60% of total visual, filtering is ~40%
  const scrapePart = (props.progress / 100) * 60
  const filterPart = ((props.filtering_progress || 0) / 100) * 40
  return Math.min(Math.floor(scrapePart + filterPart), 99)
})

const currentPlatformLabel = computed(() => {
  if (props.current_platform === 'DONE') return '全网提炼'
  if (props.current_platform) return props.current_platform
  return '全网'
})

const humorousText = computed(() => {
  if (isDone.value) {
    return '✨ 采集分析大功告成，请验收成果！'
  }
  if (isFiltering.value) {
    return '🧠 AI 正在极速阅读并提炼核心观点...'
  }
  if (props.progress > 0) {
    return '👀 正在茫茫帖海中寻找有价值的内容...'
  }
  return '🔋 引擎预热中，准备起航涉水...'
})

const statusEmoji = computed(() => {
  if (isDone.value) return '🎉'
  if (isFiltering.value) return '🔮'
  return '🛰️'
})

const goToFacts = () => {
  router.push(`/case/${caseId.value}/workflow/facts`)
}
</script>

<style scoped>
.animate-bounce-slow {
  animation: bounce-slow 3s infinite ease-in-out;
}
@keyframes bounce-slow {
  0%, 100% { transform: translateY(-5%); }
  50% { transform: translateY(5%); }
}

.animate-fade-in {
  animation: fadeIn 0.5s ease-out forwards;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
