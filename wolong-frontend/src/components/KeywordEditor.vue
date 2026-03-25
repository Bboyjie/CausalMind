<template>
  <div class="keyword-editor-container">
    <div class="mb-2 text-sm text-slate-500 flex justify-between">
      <span>AI 自动生成的搜索策略：</span>
      <span class="text-xs text-blue-500"><el-icon><InfoFilled /></el-icon> 可自由增删调整</span>
    </div>
    
    <div class="flex flex-wrap gap-3 items-center p-4 bg-slate-50 border border-slate-200 rounded-lg min-h-[80px]">
      <el-tag
        v-for="keyword in modelValue"
        :key="keyword"
        closable
        :disable-transitions="false"
        @close="handleClose(keyword)"
        size="large"
        effect="light"
        class="text-base py-4 px-3"
      >
        {{ keyword }}
      </el-tag>
      
      <el-input
        v-if="inputVisible"
        ref="InputRef"
        v-model="inputValue"
        class="w-32"
        size="large"
        @keyup.enter="handleInputConfirm"
        @blur="handleInputConfirm"
      />
      <el-button v-else class="button-new-tag" size="large" @click="showInput">
        + 新增关键词
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { InfoFilled } from '@element-plus/icons-vue'

const props = defineProps<{
  modelValue: string[]
}>()

const emit = defineEmits(['update:modelValue'])

const inputValue = ref('')
const inputVisible = ref(false)
const InputRef = ref<any>(null)

const handleClose = (tag: string) => {
  const newKeywords = props.modelValue.filter(k => k !== tag)
  emit('update:modelValue', newKeywords)
}

const showInput = () => {
  inputVisible.value = true
  nextTick(() => {
    InputRef.value!.input!.focus()
  })
}

const handleInputConfirm = () => {
  if (inputValue.value) {
    // Avoid duplicates
    if (!props.modelValue.includes(inputValue.value)) {
      emit('update:modelValue', [...props.modelValue, inputValue.value])
    }
  }
  inputVisible.value = false
  inputValue.value = ''
}
</script>
