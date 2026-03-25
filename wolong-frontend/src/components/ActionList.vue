<template>
  <div class="action-list space-y-4">
    <div 
      v-for="action in actList" 
      :key="action.id"
      class="border rounded-xl p-4 transition-all duration-300 relative overflow-hidden group"
      :class="action.done ? 'bg-slate-50 border-slate-200' : 'bg-white border-blue-100 hover:border-blue-300 shadow-sm'"
    >
      <div 
        v-if="action.done" 
        class="absolute inset-0 bg-green-500/5 backdrop-blur-[1px] z-0 pointer-events-none"
      />
      
      <div class="relative z-10 flex gap-4">
        <div class="pt-1">
          <el-checkbox v-model="action.done" size="large" @change="toggleAction(action)" />
        </div>
        
        <div class="flex-1">
          <h4 
            class="text-lg font-bold text-slate-800 transition-colors"
            :class="{'line-through text-slate-400': action.done}"
          >
            {{ action.title }}
          </h4>
          
          <div class="mt-2 space-y-2" :class="{'opacity-60': action.done}">
            <div class="text-sm text-slate-600 bg-slate-50 p-2 rounded">
              <span class="font-bold text-slate-700 mr-1">验证目标:</span>
              {{ action.objective }}
            </div>
            
            <div class="flex justify-between items-center mt-2">
              <span class="text-xs font-mono text-amber-600 bg-amber-50 px-2 py-1 rounded-sm">
                耗损预估: {{ action.cost }}
              </span>
              
              <el-button 
                type="danger" 
                link 
                size="small" 
                class="opacity-0 group-hover:opacity-100 transition-opacity"
                @click="reportError(action)"
              >
                此建议不切实际 (纠错)
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  actions: any[]
}>()

const emit = defineEmits(['feedback'])

// Local reactive deep copy to hold checkbox state without emitting upward immediately
const actList = ref<any[]>([])

watch(() => props.actions, (newVals) => {
  actList.value = newVals.map(a => ({ ...a, done: a.status === 'done' }))
}, { immediate: true, deep: true })

const toggleAction = (action?: any) => {
  // Optionally sync via API or pinia here
  console.log('Action toggled:', action?.id)
}

const reportError = (action: any) => {
  emit('feedback', { target_id: action.id, target_type: 'ACTION' })
}
</script>
