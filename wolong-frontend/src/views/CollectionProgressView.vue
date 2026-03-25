<template>
  <div class="collection-progress flex flex-col h-full items-center justify-center p-6 animate-fade-in relative text-center">
    
    <div class="max-w-3xl w-full bg-white rounded-2xl shadow-sm border border-slate-100 p-8 pb-10 mt-10">
      <div class="mb-6 flex justify-center">
        <el-tag effect="light" type="primary" size="large" class="rounded-full px-6 text-sm">
          <el-icon class="mr-1"><Opportunity /></el-icon>
          正在为你构建专属信息采集网
        </el-tag>
      </div>

      <CollectionDashboard 
        :progress="progress" 
        :status="status" 
        :current_platform="current_platform"
        :filtering_progress="filtering_progress"
        :filtering_status="filtering_status"
        :stats="stats" 
      />
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Opportunity } from '@element-plus/icons-vue'
import CollectionDashboard from '../components/CollectionDashboard.vue'
import { getCollectionStatus } from '../api/case'
import { useCaseStore } from '../store/caseStore'

const router = useRouter()
const route = useRoute()
const caseStore = useCaseStore()

const caseId = route.params.id as string

const progress = ref(0)
const status = ref('STARTING')
const current_platform = ref<string | null>(null)
const filtering_progress = ref(0)
const filtering_status = ref<string | null>(null)
const stats = ref<any>(null)

let timer: number

const fetchProgress = async () => {
  try {
    const res = await getCollectionStatus(caseId)
    if (res.code === 200) {
      status.value = res.data.status
      progress.value = res.data.progress
      current_platform.value = res.data.current_platform
      filtering_progress.value = res.data.filtering_progress
      filtering_status.value = res.data.filtering_status
      
      if (res.data.status === 'COMPLETED') {
        stats.value = res.data
        caseStore.collectionStats = res.data
        clearInterval(timer)
        
        // Wait 2 seconds so user can see 100%, then transition
        setTimeout(() => {
          router.push({ name: 'InfoPoolSummary', params: { id: caseId } })
        }, 2000)
      }
    }
  } catch (error) {
    console.error('Failed to get status', error)
  }
}

onMounted(() => {
  // Start polling
  timer = window.setInterval(fetchProgress, 800)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
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
