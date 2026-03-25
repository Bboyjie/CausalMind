<template>
  <div class="simulation-panel w-80 bg-white border-l border-slate-200 shadow-sm flex flex-col h-full animate-fade-in-right">
    <div class="p-6 border-b border-slate-100 pb-4">
      <h3 class="text-xl font-bold text-slate-800 flex items-center">
        <el-icon class="mr-2 text-indigo-500"><Operation /></el-icon>
        因果推演控制台
      </h3>
      <p class="text-xs text-slate-500 mt-2 leading-relaxed">
        点击左侧沙盘节点，调节可控变量（橙色节点），观察其对客观世界状态（蓝色节点）的涟漪影响。
      </p>
    </div>

    <div class="flex-1 overflow-y-auto p-6 space-y-6">
      
      <!-- Global Text Intervention -->
      <div class="bg-blue-50 p-4 rounded-xl border border-blue-100">
        <h4 class="text-sm font-bold text-blue-800 mb-2 flex items-center">
          <el-icon class="mr-1"><ChatDotRound /></el-icon> 自由文本指令 (What-If)
        </h4>
        <el-input 
          v-model="interventionText" 
          type="textarea" 
          placeholder="例如：假如我决定脱产并兼职送外卖..." 
          :rows="2" 
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
          提交因果假设
        </el-button>
      </div>

      <el-divider class="my-0 border-slate-200" />

      <div v-if="!activeNode" class="flex flex-col items-center justify-center text-slate-400 py-6">
        <el-icon class="text-4xl mb-2"><Pointer /></el-icon>
        <span class="text-sm">选定左侧目标进行数值微调</span>
      </div>

      <div v-else class="space-y-6">
        <!-- Node Info -->
        <div class="bg-indigo-50 p-4 rounded-xl border border-indigo-100">
          <div class="flex justify-between items-start mb-2">
            <span class="font-bold text-slate-800">{{ activeNode.name }}</span>
            <el-tag size="small" :type="activeNode.type === 'action' ? 'warning' : 'primary'">
              {{ activeNode.type === 'action' ? '可控变量' : '客观约束' }}
            </el-tag>
          </div>
          <p class="text-xs text-slate-600">当前测算赋值: <span class="font-mono font-bold">{{ activeNode.val }}</span></p>
        </div>

        <el-collapse v-if="nodeTopologyDetails.length > 0" class="border border-violet-100 rounded-xl overflow-hidden">
          <el-collapse-item title="拓扑明细与认知陷阱" name="topology">
            <div class="space-y-3 pr-2">
              <div
                v-for="(detail, idx) in nodeTopologyDetails"
                :key="idx"
                class="bg-violet-50 border border-violet-100 rounded-lg p-3"
              >
                <div class="text-xs font-bold text-violet-700 mb-1">
                  {{ detail.kind === 'confounder' ? '混杂因子' : '对撞因子' }} · {{ detail.label || '未命名' }}
                </div>
                <div class="text-xs text-slate-600 leading-relaxed mb-1">{{ detail.detail || '结构信息缺失' }}</div>
                <div class="text-xs text-amber-700 leading-relaxed">
                  认知陷阱：{{ detail.cognitiveTrap || '暂无补充说明' }}
                </div>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>

        <!-- Intervention Form -->
        <div v-if="activeNode.type === 'action'" class="space-y-4">
          <div>
            <span class="text-sm font-bold text-slate-700 block mb-2">实施状态干预 (What-if)</span>
            <!-- Simple bounded slider for varying probability/intensity 0 to 1 -->
            <el-slider 
              v-model="interventionVal" 
              :min="0" :max="1" :step="0.1" 
              show-stops
              :format-tooltip="(v: number) => v === 0 ? '极低/否定' : (v === 1 ? '极高/肯定' : String(v))"
            />
          </div>
          
          <el-button 
            type="primary" 
            class="w-full" 
            @click="triggerSimulation"
            :loading="isSimulating"
          >
            执行推演
          </el-button>
        </div>
      </div>

      <div v-if="simulationResult" class="fade-in space-y-4">
        <h4 class="text-sm font-bold text-slate-800 border-l-4 border-indigo-500 pl-2 mt-4">当期推演结论</h4>
        
        <div v-if="simulationResult.affected_nodes?.length > 0" class="text-sm">
          波及下游节点：
          <div class="flex gap-2 mt-2">
                <el-tag v-for="an in simulationResult.affected_nodes" :key="an.id" 
                        :type="an.trend === 'down' ? 'danger' : (an.trend === 'up' ? 'success' : 'info')">
                  {{ an.id }} 变为 {{ an.new_val }}
                  <span v-if="an.impact_degree" class="ml-1">({{ an.impact_degree }})</span>
                  <span v-if="an.delay_type" class="ml-1">/{{ an.delay_type }}</span>
                  <el-icon v-if="an.trend === 'down'"><Bottom /></el-icon>
                  <el-icon v-else-if="an.trend === 'up'"><Top /></el-icon>
                </el-tag>
          </div>
        </div>

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
import { ref, watch } from 'vue'
import { Operation, Pointer, Bottom, Top, ChatDotRound, RefreshLeft } from '@element-plus/icons-vue'

const props = defineProps<{
  activeNode: any | null
  isSimulating: boolean
  simulationResult: any | null
  history: any[]
  nodeTopologyDetails?: any[]
}>()

const emit = defineEmits(['intervene', 'undo'])

const interventionVal = ref(0)
const interventionText = ref('')
const nodeTopologyDetails = ref<any[]>([])

watch(() => props.activeNode, (newNode) => {
  if (newNode) {
    interventionVal.value = newNode.val
  }
})

watch(
  () => props.nodeTopologyDetails,
  (val) => {
    nodeTopologyDetails.value = Array.isArray(val) ? val : []
  },
  { immediate: true, deep: true }
)

const triggerSimulation = () => {
  if (props.activeNode) {
    emit('intervene', {
      node_id: props.activeNode.id,
      new_val: interventionVal.value
    })
  }
}

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
.animate-fade-in-right {
  animation: fadeInRight 0.3s ease-out;
}

@keyframes fadeInRight {
  from { opacity: 0; transform: translateX(20px); }
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
