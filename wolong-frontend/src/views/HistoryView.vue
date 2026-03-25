<template>
  <div class="history-view max-w-7xl mx-auto p-6 md:p-8 animate-fade-in flex flex-col gap-8 h-screen">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-slate-800">历史决策档案</h1>
        <p class="text-slate-500 mt-2">查看、恢复或管理过去推演过的博弈与职业决策案例库。</p>
      </div>
      <el-button @click="router.push('/')" plain type="primary">
        返回控制台
      </el-button>
    </div>

    <div v-if="isLoading" class="flex-1 flex items-center justify-center">
      <el-icon class="is-loading text-4xl text-blue-500"><Loading /></el-icon>
    </div>

    <div v-else-if="cases.length === 0" class="flex-1 flex flex-col items-center justify-center">
      <el-empty description="暂无历史归档记录" />
      <el-button type="primary" class="mt-4" @click="router.push('/')">立即创建新决策</el-button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 auto-rows-max overflow-y-auto pb-10">
      <el-card 
        v-for="item in cases" 
        :key="item.id" 
        shadow="hover" 
        class="rounded-xl border-slate-200 cursor-pointer group flex flex-col h-56 transition-all hover:-translate-y-1 hover:shadow-lg"
        @click="resumeCase(item)"
      >
        <div class="flex justify-between items-start mb-3">
          <div class="text-[10px] text-slate-400 font-mono tracking-wider">
            {{ new Date(item.created_at).toLocaleString() }}
          </div>
          <el-tag :type="getStatusType(item.status)" size="small" effect="light" round class="border-transparent">
            {{ getStatusLabel(item.status) }}
          </el-tag>
        </div>
        
        <h3 class="text-lg font-bold text-slate-800 leading-snug line-clamp-2 h-14 group-hover:text-blue-600 transition-colors">
          {{ item.title }}
        </h3>
        
        <div class="flex flex-wrap gap-1 mt-4">
          <el-tag v-for="tag in item.tags" :key="tag" size="small" type="info" class="rounded-md">
            {{ tag }}
          </el-tag>
        </div>

        <div class="mt-auto pt-4 border-t border-slate-100 flex justify-between items-center opacity-0 group-hover:opacity-100 transition-opacity">
          <span class="text-sm font-medium text-blue-500">恢复推演现场 &rarr;</span>
          <el-button link type="danger" @click.stop="deleteCase(item.id)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Loading, Delete } from '@element-plus/icons-vue'
import { deleteHistoricalCase, getHistoricalCases } from '../api/case'
import { useCaseStore } from '../store/caseStore'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const caseStore = useCaseStore()

const cases = ref<any[]>([])
const isLoading = ref(true)

onMounted(async () => {
  try {
    const res = await getHistoricalCases()
    if (res.code === 200) {
      cases.value = res.data
    }
  } catch (err) {
    ElMessage.error('无法拉取历史记录')
  } finally {
    isLoading.value = false
  }
})

const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    'CREATED': '草稿态',
    'COLLECTING': '信采期',
    'FACT_AUDIT': '认知审计',
    'CAUSAL_SANDBOX': '沙盘推演',
    'WORLDLINE_EVOLUTION': '世界线干预',
    'WHITE_PAPER': '归档白皮书'
  }
  return map[status] || status
}

const getStatusType = (status: string): any => {
  if (['WHITE_PAPER'].includes(status)) return 'success'
  if (['WORLDLINE_EVOLUTION', 'CAUSAL_SANDBOX'].includes(status)) return 'primary'
  if (['FACT_AUDIT', 'COLLECTING'].includes(status)) return 'warning'
  return 'info'
}

const resumeCase = (item: any) => {
  // Sync the caseStore so child routes mount correctly
  caseStore.currentCaseId = item.id
  caseStore.currentCaseDetail = {
    id: item.id,
    profile: item.title,
    status: item.status,
    created_at: item.created_at
  }
  
  ElMessage.success(`恢复场景 [${item.title.substring(0,6)}...]`)
  
  // Route to the appropriate workflow step based on status
  // For simplicity, we can route directly to the layout and it should handle or we explicitly push.
  // We'll enforce the map routing:
  const routeMap: Record<string, string> = {
    'CREATED': `/case/${item.id}/workflow/strategy`,
    'COLLECTING': `/case/${item.id}/workflow/collection`,
    'FACT_AUDIT': `/case/${item.id}/workflow/audit`,
    'CAUSAL_SANDBOX': `/case/${item.id}/workflow/sandbox`,
    'WORLDLINE_EVOLUTION': `/case/${item.id}/workflow/worldline`,
    'WHITE_PAPER': `/case/${item.id}/workflow/whitepaper`
  }
  
  const target = routeMap[item.status] || `/case/${item.id}/workflow/strategy`
  router.push(target)
}

const deleteCase = (id: string) => {
  ElMessageBox.confirm('是否永久删除该推演沙盘归档？', '确认操作', {
    confirmButtonText: '狠心删除',
    cancelButtonText: '保留',
    type: 'error'
  }).then(async () => {
    await deleteHistoricalCase(id)
    cases.value = cases.value.filter(c => c.id !== id)
    if (caseStore.currentCaseId === id) {
      caseStore.currentCaseId = null
      caseStore.currentCaseDetail = null
    }
    ElMessage.success('归档已删除')
  }).catch((e) => {
    if (e !== 'cancel') {
      ElMessage.error('删除失败，请稍后重试')
    }
  })
}
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.5s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(15px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
