<template>
  <div class="conflict-card bg-red-50 border border-red-100 rounded-xl p-6 relative overflow-hidden">
    <div class="absolute -right-4 -top-4 text-red-100 opacity-50 z-0">
      <el-icon :size="120"><WarningFilled /></el-icon>
    </div>
    <div class="relative z-10">
      <h3 class="text-xl font-bold text-red-800 flex items-center mb-4">
        <el-icon class="mr-2"><WarnTriangleFilled /></el-icon>
        核心结构性矛盾 (The Core Conflict)
      </h3>
      <p class="text-slate-800 text-lg leading-relaxed font-medium bg-white/60 p-4 rounded bg-clip-padding backdrop-filter backdrop-blur-sm border border-red-100 shadow-sm">
        {{ mainConflict }}
      </p>

      <div class="mt-6" v-if="criticalWarnings?.length">
        <h4 class="text-md font-bold text-amber-700 flex items-center mb-2">
          <el-icon class="mr-1"><AlarmClock /></el-icon>
          临界风险预警
        </h4>
        <ul class="space-y-2">
          <li 
            v-for="(warning, idx) in criticalWarnings" 
            :key="idx"
            class="text-amber-900 bg-amber-100/50 px-3 py-2 rounded text-sm flex items-start"
          >
            <span class="mr-2 font-bold opacity-50">#{{ idx + 1 }}</span>
            <span>{{ warning }}</span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { WarningFilled, WarnTriangleFilled, AlarmClock } from '@element-plus/icons-vue'

defineProps<{
  mainConflict: string
  criticalWarnings: string[]
}>()
</script>
