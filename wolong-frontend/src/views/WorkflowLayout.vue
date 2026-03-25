<template>
  <div class="workflow-layout flex flex-col min-h-screen bg-slate-50">
    <!-- Header / Progress Bar -->
    <header class="bg-white shadow-sm sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div class="flex items-center space-x-4">
          <h2 class="text-xl font-bold text-slate-800">卧龙决策域</h2>
          <el-tag type="info" size="small" effect="plain" class="font-mono">
            {{ route.params.id }}
          </el-tag>
        </div>
        
        <div class="flex-1 px-4 lg:px-8 overflow-x-auto no-scrollbar py-2">
          <div class="flex justify-between md:justify-center md:space-x-8 min-w-max">
            <template v-for="(step, index) in steps" :key="index">
              <div 
                class="flex items-center cursor-pointer group transition-colors"
                @click="navigateToStep(step.routeName)"
              >
                <div 
                  class="flex items-center justify-center w-8 h-8 rounded-full border-2 text-sm font-bold shadow-sm transition-all"
                  :class="[
                    activeIndex === index ? 'border-blue-600 bg-blue-600 text-white' : 
                    activeIndex > index ? 'border-green-500 bg-green-500 text-white' : 
                    'border-slate-300 bg-slate-50 text-slate-400 group-hover:border-blue-400'
                  ]"
                >
                  <el-icon v-if="activeIndex > index"><Check /></el-icon>
                  <span v-else>{{ index + 1 }}</span>
                </div>
                <div class="ml-3 hidden sm:block">
                  <p 
                    class="text-sm font-bold transition-colors"
                    :class="[activeIndex === index ? 'text-blue-700' : 'text-slate-600 group-hover:text-blue-500']"
                  >{{ step.title }}</p>
                  <p class="text-xs text-slate-400 hidden lg:block">{{ step.description }}</p>
                </div>
                
                <!-- Connector Line -->
                <div v-if="index < steps.length - 1" class="w-8 md:w-16 h-0.5 mx-3 md:mx-4" :class="activeIndex > index ? 'bg-green-500' : 'bg-slate-200'"></div>
              </div>
            </template>
          </div>
        </div>
        
        <div class="flex items-center space-x-4">
          <el-button link type="primary" @click="router.push('/history')">
            <el-icon class="mr-1"><Memo /></el-icon> 历史记录
          </el-button>
          <el-button link type="info" @click="router.push('/settings')">
            <el-icon class="mr-1"><Setting /></el-icon> 模型配置
          </el-button>
          <div class="h-4 w-px bg-slate-300 mx-2"></div>
          <el-button link @click="goHome">返回首页</el-button>
        </div>
      </div>
    </header>

    <!-- Main Content Area -->
    <main class="flex-1 max-w-7xl w-full mx-auto sm:p-4 lg:p-6 flex flex-col min-h-0">
      <div class="bg-white rounded-xl shadow-sm border border-slate-100 flex-1 relative flex flex-col overflow-hidden">

        
        <!-- Placeholder for child routes in future cycles -->
        <router-view></router-view>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Check, Setting, Memo } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const steps = [
  { title: '信息采集', description: '配置与获取', routeName: 'StrategyConfig' },
  { title: '信息汇聚池', description: '智能提炼成果', routeName: 'FactsPool' },
  { title: '事实审查', description: '认知审计台', routeName: 'FactAudit' },
  { title: '因果沙盘', description: '反事实推演', routeName: 'CausalSandbox' },
  { title: '世界线演化', description: '个人语境推演', routeName: 'WorldlineSimulator' },
  { title: '破局白皮书', description: '方案生成', routeName: 'WhitepaperReader' }
]

const activeIndex = computed(() => {
  const name = route.name as string
  if (['StrategyConfig', 'CollectionProgress'].includes(name)) return 0
  if (name === 'InfoPoolSummary') return 1
  if (name === 'FactsPool') return 1
  if (name === 'FactAudit') return 2
  if (name === 'CausalSandbox') return 3
  if (name === 'WorldlineSimulator') return 4
  if (name === 'WhitepaperReader') return 5
  return 0
})

const navigateToStep = (routeName: string) => {
  router.push({ name: routeName, params: { id: route.params.id } })
}

const goHome = () => {
  router.push('/')
}
</script>

<style scoped>
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;  /* IE and Edge */
  scrollbar-width: none;  /* Firefox */
}
</style>
