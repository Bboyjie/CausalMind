<template>
  <div class="case-create-container min-h-screen bg-slate-50 flex items-center justify-center p-4 relative">
    
    <!-- Top Nav -->
    <div class="absolute top-4 right-6 flex gap-4">
      <el-button link type="primary" @click="router.push('/history')">
        <el-icon class="mr-1"><Memo /></el-icon> 历史决策档案
      </el-button>
      <el-button link type="info" @click="router.push('/settings')">
        <el-icon class="mr-1"><Setting /></el-icon> 大模型配置
      </el-button>
    </div>

    <div class="max-w-2xl w-full bg-white rounded-xl shadow-lg p-8">
      <div class="text-center mb-8">
        <h1 class="text-3xl font-bold text-slate-800 mb-2">卧龙 - 决策推演沙盘</h1>
        <p class="text-slate-500">请输入您的决策情景或当前面临的难题，我们将为您构建专属推演空间</p>
      </div>

      <el-form label-position="top">
        <el-form-item label="决策情景描述">
          <el-input
            v-model="profile"
            type="textarea"
            :rows="6"
            placeholder="例如：我想在潍坊找一份IT开发工作，我是三年经验的专科生..."
            class="w-full text-lg"
          />
        </el-form-item>

        <div class="flex justify-center mt-8">
          <el-button
            type="primary"
            size="large"
            :loading="caseStore.isLoading"
            @click="handleSubmit"
            class="w-full sm:w-auto px-12 text-lg font-medium tracking-wide h-12"
          >
            {{ caseStore.isLoading ? '正在初始化决策沙盘...' : '一键生成决策案例' }}
          </el-button>
        </div>
      </el-form>
      
      <!-- Placeholder details for demo -->
      <div class="mt-8 pt-6 border-t border-slate-100 flex justify-center space-x-8 text-sm text-slate-400">
        <span class="flex items-center"><el-icon class="mr-1"><Edit /></el-icon> 自由输入</span>
        <span class="flex items-center"><el-icon class="mr-1"><Cpu /></el-icon> AI 深度解析</span>
        <span class="flex items-center"><el-icon class="mr-1"><DataAnalysis /></el-icon> 多维推演</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCaseStore } from '../store/caseStore'
import { ElMessage } from 'element-plus'
import { Edit, Cpu, DataAnalysis, Memo, Setting } from '@element-plus/icons-vue'

const profile = ref('')
const router = useRouter()
const caseStore = useCaseStore()

const handleSubmit = async () => {
  if (!profile.value.trim()) {
    ElMessage.warning('请输入您的决策情景描述')
    return
  }
  
  try {
    const newCase = await caseStore.createCase(profile.value)
    ElMessage.success('决策案例创建成功！')
    
    // Jump to the workflow page
    router.push({
      name: 'CaseWorkflow',
      params: { id: newCase.id }
    })
  } catch (error: any) {
    // Error is handled in the request interceptor or store
    console.error(error)
  }
}
</script>

<style scoped>
/* Extra styling not covered by Tailwind */
:deep(.el-textarea__inner) {
  @apply text-base p-4 bg-slate-50 border-slate-200 focus:bg-white;
  border-radius: 0.5rem;
}
</style>
