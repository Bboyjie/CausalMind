<template>
  <div class="strategy-config flex flex-col h-full animate-fade-in relative">
    <div class="flex-1 overflow-y-auto pr-2 pb-24">
      <!-- Loading State -->
      <div v-if="isLoading" class="flex flex-col items-center justify-center py-20 mt-12">
        <el-icon class="is-loading text-4xl text-blue-500 mb-4"><Loading /></el-icon>
        <p class="text-slate-500 font-medium">代理 AI 正在深入分析您的问题情境...</p>
        <p class="text-xs text-slate-400 mt-2">预计生成专属信息搜集策略需要 2 秒钟</p>
      </div>

      <!-- Content State -->
      <div v-else-if="!isLoading && keywords.length > 0" class="space-y-8 fade-in p-2">
        <section>
          <div class="flex items-center space-x-2 text-lg font-bold text-slate-800 mb-4">
            <el-icon class="text-blue-500"><MagicStick /></el-icon>
            <h2>步骤 1: 确定高维搜索词组</h2>
          </div>
          <KeywordEditor v-model="keywords" />
        </section>

        <el-divider />

        <section>
          <div class="flex items-center space-x-2 text-lg font-bold text-slate-800 mb-4">
            <el-icon class="text-indigo-500"><LocationInformation /></el-icon>
            <h2>步骤 2: 配置采集管道与信息源</h2>
          </div>
          <SourceSelector v-model="sourceConfig" />
        </section>
      </div>
      
      <!-- Error / Empty State -->
      <div v-else class="py-20 text-center text-slate-400">
        加载失败，请刷新页面重试
      </div>
    </div>

    <!-- Bottom Actions -->
    <div class="absolute bottom-0 left-0 right-0 flex justify-between items-center bg-white p-4 rounded-xl shadow-[0_-10px_40px_-15px_rgba(0,0,0,0.1)] border border-slate-100 z-10 m-2">
      <div class="text-sm text-slate-500">
        <span v-if="!isLoading && keywords.length > 0" class="flex items-center">
          <el-icon class="mr-1 text-green-500"><CircleCheckFilled /></el-icon> 
          已准备就绪，点击开始自动化采集
        </span>
      </div>
      <el-button 
        type="primary" 
        size="large" 
        class="w-48 text-base tracking-wide"
        :disabled="isLoading || keywords.length === 0"
        @click="startCollection"
        :loading="isSubmitting"
      >
        立刻开始采集
        <el-icon class="ml-2" v-if="!isSubmitting"><VideoPlay /></el-icon>
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Loading, MagicStick, LocationInformation, VideoPlay, CircleCheckFilled } from '@element-plus/icons-vue'
import KeywordEditor from '../components/KeywordEditor.vue'
import SourceSelector from '../components/SourceSelector.vue'
import { generateSearchStrategy, startCollectionTask } from '../api/case'
import { useCaseStore } from '../store/caseStore'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const caseStore = useCaseStore()

const isLoading = ref(true)
const isSubmitting = ref(false)
const keywords = ref<string[]>([])
const sourceConfig = ref({
  platforms: ['xhs', 'zhihu'],
  extraction: {
    chunk_size: 12,
    chunk_overlap: 0,
    max_chunk_tokens: 0
  },
  timeRange: '1y',
  targetCount: 150
})

const caseId = route.params.id as string

onMounted(async () => {
  try {
    const res = await generateSearchStrategy(caseId)
    if (res.code === 200) {
      keywords.value = res.data.keywords
    }
  } catch (error) {
    console.error('Failed to generate strategy:', error)
  } finally {
    isLoading.value = false
  }
})

const startCollection = async () => {
  isSubmitting.value = true
  try {
    const res = await startCollectionTask(caseId, {
      keywords: keywords.value,
      config: sourceConfig.value
    })
    
    if (res.code === 200) {
      // Save configuration to store
      caseStore.searchKeywords = keywords.value
      caseStore.dataSourceConfig = sourceConfig.value
      
      ElMessage.success('抓取管道建立成功，开始采集...')
      router.push({ name: 'CollectionProgress', params: { id: caseId } })
    }
  } catch (error) {
    ElMessage.error('启动失败，请检查网络')
  } finally {
    isSubmitting.value = false
  }
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
</style>
