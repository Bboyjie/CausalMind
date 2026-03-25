<template>
  <div class="worldline-intervention-panel flex flex-col h-full bg-white border-r border-slate-200 shadow-sm animate-fade-in-left">
    <div class="p-6 pb-4 border-b border-slate-100">
      <h3 class="text-lg font-bold text-slate-800 flex items-center">
        <el-icon class="mr-2 text-indigo-500"><MagicStick /></el-icon>
        世界线变动干预
      </h3>
      <p class="text-xs text-slate-500 mt-2 leading-relaxed">
        基于当前注入的个人约束语境，您可以输入新的主观决策或变量假设，观测其对未来发展路径的扰动。
      </p>
    </div>

    <div class="flex-1 overflow-y-auto p-6 space-y-6">
      
      <!-- Global Text Intervention -->
      <div class="bg-indigo-50 p-4 rounded-xl border border-indigo-100">
        <h4 class="text-sm font-bold text-indigo-800 mb-2 flex items-center">
          <el-icon class="mr-1"><ChatDotRound /></el-icon> 新的个人决策 (What-If)
        </h4>
        <el-input 
          v-model="interventionText" 
          type="textarea" 
          placeholder="例如：我不接受降薪，我决定死磕远程欧美Web3岗位..." 
          :rows="3" 
          class="mb-3"
          resize="none"
        />
        <el-button 
          type="primary" 
          size="small" 
          plain 
          class="w-full" 
          @click="triggerTextSimulation" 
          :loading="isSimulating"
          :disabled="!interventionText.trim()"
        >
          提交世界线扰动
        </el-button>
      </div>

      <el-divider class="my-0 border-slate-200" />

      <!-- Feedback Result -->
      <div v-if="simulationResult" class="fade-in space-y-4">
        <h4 class="text-sm font-bold text-slate-800 border-l-4 border-indigo-500 pl-2 mt-4">当期推演结论</h4>
        
        <p class="text-sm text-slate-600 bg-slate-50 p-3 rounded leading-relaxed border border-slate-200">
          {{ simulationResult.logic_explanation }}
        </p>

        <el-alert
          v-if="simulationResult.risk_warning"
          :title="simulationResult.risk_warning"
          type="error"
          :closable="false"
          show-icon
        />
        <div v-else class="text-xs text-slate-500 bg-slate-100 border border-slate-200 px-3 py-2 rounded">
          暂无关联风险
        </div>
      </div>

      <!-- History List -->
      <div v-if="history.length" class="space-y-3 pt-4 mt-6 border-t border-slate-100">
        <h4 class="text-sm font-bold text-slate-700 flex justify-between items-center">
          推演快照
          <el-button link type="danger" size="small" @click="emit('undo')" :disabled="isSimulating">
            <el-icon class="mr-1"><RefreshLeft /></el-icon>撤销回退
          </el-button>
        </h4>
        <div v-for="item in [...history].reverse()" :key="item.id" class="bg-slate-50 border border-slate-200 p-2.5 rounded text-xs text-slate-600">
           <div class="font-bold mb-1 text-slate-700">{{ item.title }}</div>
           <div class="text-slate-500 truncate" :title="item.desc">{{ item.desc }}</div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { MagicStick, ChatDotRound, RefreshLeft } from '@element-plus/icons-vue'

const props = defineProps<{
  isSimulating: boolean
  simulationResult: any | null
  history: any[]
}>()

const emit = defineEmits(['intervene', 'undo'])

const interventionText = ref('')

const triggerTextSimulation = () => {
  if (interventionText.value.trim()) {
    emit('intervene', {
      text: interventionText.value.trim()
    })
    interventionText.value = ''
  }
}
</script>

<style scoped>
.animate-fade-in-left {
  animation: fadeInLeft 0.4s ease-out;
}

@keyframes fadeInLeft {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}

.fade-in {
  animation: fadeIn 0.4s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
