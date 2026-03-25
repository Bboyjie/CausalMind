<template>
  <div class="source-selector-container w-full">
    <div class="mb-4 text-sm font-medium text-slate-700 mt-2">爬取平台与额度分配（支持引擎：MediaCrawler）</div>
    
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div 
        v-for="plat in availablePlatforms" 
        :key="plat.value"
        class="border rounded-xl p-4 flex flex-col gap-3 transition-all duration-300"
        :class="{ 'border-blue-400 bg-blue-50/40 shadow-sm': plat.enabled, 'border-slate-200 bg-slate-50 opacity-60 grayscale-[0.3] hover:grayscale-0': !plat.enabled }"
      >
        <div class="flex items-center justify-between">
          <el-checkbox v-model="plat.enabled" size="large">
            <span class="font-bold text-slate-800 text-base ml-1">{{ plat.label }}</span>
            <span class="text-xs text-slate-400 ml-2 font-normal hidden sm:inline-block">{{ plat.desc }}</span>
          </el-checkbox>
        </div>
        
        <div v-show="plat.enabled" class="flex flex-col gap-3 pl-8 mt-1 animate-fade-in">
          <div class="flex items-center justify-between">
            <span class="text-sm text-slate-600">抓取上限 (篇/平台):</span>
            <el-input-number v-model="plat.max_notes" :min="1" :max="1000" :step="10" size="default" class="w-32" />
          </div>
          <div class="flex items-center justify-between">
            <span class="text-sm text-slate-600">包含子评论:</span>
            <el-switch v-model="plat.get_comments" style="--el-switch-on-color: #3b82f6;" inline-prompt active-text="是" inactive-text="否" />
          </div>
          <div v-show="plat.get_comments" class="flex items-center justify-between">
            <span class="text-sm text-slate-600">单帖评论上限:</span>
            <el-input-number
              v-model="plat.max_comments_count_singlenotes"
              :min="1"
              :max="100"
              :step="1"
              size="default"
              class="w-32"
            />
          </div>
        </div>
      </div>
    </div>

    <div class="mt-6 border rounded-xl p-4 bg-white/80">
      <div class="text-sm font-semibold text-slate-700 mb-3">提取分块参数（用于事实提炼稳定性）</div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div class="flex items-center justify-between border border-slate-200 rounded-lg px-3 py-2">
          <span class="text-sm text-slate-600">分块长度</span>
          <el-input-number v-model="extraction.chunk_size" :min="1" :max="200" :step="1" size="small" class="w-28" />
        </div>
        <div class="flex items-center justify-between border border-slate-200 rounded-lg px-3 py-2">
          <span class="text-sm text-slate-600">重叠长度</span>
          <el-input-number v-model="extraction.chunk_overlap" :min="0" :max="100" :step="1" size="small" class="w-28" />
        </div>
        <div class="flex items-center justify-between border border-slate-200 rounded-lg px-3 py-2">
          <span class="text-sm text-slate-600">单块Token上限</span>
          <el-input-number v-model="extraction.max_chunk_tokens" :min="0" :max="12000" :step="100" size="small" class="w-28" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'

const props = defineProps<{
  modelValue: any
}>()

const emit = defineEmits(['update:modelValue'])

const availablePlatforms = ref([
  { label: '小红书', value: 'xhs', desc: '经验类主阵地', enabled: true, max_notes: 50, get_comments: true, max_comments_count_singlenotes: 10 },
  { label: '知乎', value: 'zhihu', desc: '深度分析', enabled: true, max_notes: 20, get_comments: true, max_comments_count_singlenotes: 10 },
  { label: '抖音', value: 'douyin', desc: '短视频/下沉', enabled: false, max_notes: 20, get_comments: true, max_comments_count_singlenotes: 10 },
  { label: '快手', value: 'kuaishou', desc: '短视频/下沉', enabled: false, max_notes: 20, get_comments: true, max_comments_count_singlenotes: 10 },
  { label: '微博', value: 'weibo', desc: '实时热点', enabled: false, max_notes: 50, get_comments: false, max_comments_count_singlenotes: 10 },
  { label: 'B站', value: 'bilibili', desc: '中长视频分析', enabled: false, max_notes: 20, get_comments: true, max_comments_count_singlenotes: 10 },
  { label: '贴吧', value: 'tieba', desc: '垂类社区讨论', enabled: false, max_notes: 50, get_comments: true, max_comments_count_singlenotes: 10 },
])

const extraction = ref({
  chunk_size: 12,
  chunk_overlap: 0,
  max_chunk_tokens: 0
})

const emitUpdate = () => {
  const selected = availablePlatforms.value
    .filter(p => p.enabled)
    .map(p => ({
      name: p.value,
      max_notes: p.max_notes,
      get_comments: p.get_comments,
      max_comments_count_singlenotes: p.max_comments_count_singlenotes
    }))
    
  emit('update:modelValue', {
    ...props.modelValue,
    platforms: selected,
    extraction: {
      chunk_size: extraction.value.chunk_size,
      chunk_overlap: extraction.value.chunk_overlap,
      max_chunk_tokens: extraction.value.max_chunk_tokens
    }
  })
}

watch(availablePlatforms, emitUpdate, { deep: true })
watch(extraction, emitUpdate, { deep: true })

onMounted(() => {
  if (props.modelValue?.extraction) {
    extraction.value = {
      chunk_size: Number(props.modelValue.extraction.chunk_size ?? 12),
      chunk_overlap: Number(props.modelValue.extraction.chunk_overlap ?? 0),
      max_chunk_tokens: Number(props.modelValue.extraction.max_chunk_tokens ?? 0)
    }
  }
  emitUpdate()
})
</script>
