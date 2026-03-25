<template>
  <el-drawer
    v-model="visible"
    title="证据溯源审查"
    direction="rtl"
    size="40%"
    :with-header="true"
  >
    <div v-if="isLoading" class="flex flex-col items-center justify-center py-10">
      <el-icon class="is-loading text-3xl text-blue-500 mb-2"><Loading /></el-icon>
      <span class="text-slate-500">正在调取底层原始片段...</span>
    </div>

    <div v-else-if="evidences.length > 0" class="space-y-6">
      <div 
        v-for="ev in evidences" 
        :key="ev.evidence_id"
        class="bg-slate-50 p-4 rounded-lg border border-slate-200"
      >
        <div class="flex justify-between items-center mb-2">
          <span class="text-sm font-bold text-slate-700">文段来源: {{ ev.source_name }}</span>
          <el-link :href="normalizeUrl(ev.url, ev.source_name, ev.content)" target="_blank" type="primary" class="text-xs">
            跳转原文 <el-icon class="ml-1"><Link /></el-icon>
          </el-link>
        </div>
        
        <!-- Inject highlighted HTML carefully, relying on backend <mark> tag sanitization -->
        <div class="text-sm text-slate-600 leading-relaxed font-serif highlight-container" v-html="ev.content"></div>
      </div>
    </div>

    <div v-else class="text-center text-slate-400 py-10">
      无法加载证据源
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, watch, ref } from 'vue'
import { Loading, Link } from '@element-plus/icons-vue'
import { useAuditStore } from '../store/auditStore'
import { getEvidences } from '../api/case'

const props = defineProps<{
  caseId: string
  facts: any[]
}>()

const auditStore = useAuditStore()

const isLoading = ref(false)
const evidences = ref<any[]>([])

const visible = computed({
  get: () => auditStore.selectedFactId !== null,
  set: (val) => {
    if (!val) auditStore.setSelectedFact(null)
  }
})

const activeFact = computed(() => {
  return props.facts.find(f => f.id === auditStore.selectedFactId)
})

watch(() => auditStore.selectedFactId, async (newId) => {
  if (newId && activeFact.value && activeFact.value.evidence_ids.length > 0) {
    isLoading.value = true
    try {
      const res = await getEvidences(props.caseId, activeFact.value.evidence_ids)
      if (res.code === 200) {
        evidences.value = res.data
      }
    } catch (e) {
      console.error('Failed to load evidences', e)
    } finally {
      isLoading.value = false
    }
  } else {
    evidences.value = []
  }
})

const buildFallbackSourceUrl = (sourceName: string, content: string) => {
  const name = String(sourceName || '').toLowerCase()
  const q = encodeURIComponent(String(content || '').replace(/\s+/g, ' ').slice(0, 40))
  if (!q) return undefined
  if (name.includes('xhs') || name.includes('xiaohongshu')) return `https://www.xiaohongshu.com/search_result?keyword=${q}`
  if (name.includes('zhihu')) return `https://www.zhihu.com/search?type=content&q=${q}`
  if (name.includes('douyin') || name === 'dy') return `https://www.douyin.com/search/${q}`
  if (name.includes('weibo') || name === 'wb') return `https://s.weibo.com/weibo?q=${q}`
  if (name.includes('bili')) return `https://search.bilibili.com/all?keyword=${q}`
  if (name.includes('tieba')) return `https://tieba.baidu.com/f?kw=${q}`
  return undefined
}

const normalizeUrl = (url: string, sourceName = '', content = '') => {
  const raw = (url || '').trim()
  if (!raw || raw === '#' || raw.toLowerCase().startsWith('javascript:')) {
    return buildFallbackSourceUrl(sourceName, content)
  }
  return /^https?:\/\//i.test(raw) ? raw : `https://${raw}`
}
</script>

<style>
/* Style the mark tag injected from backend/mock */
.highlight-container mark {
  background-color: #fef0f0;
  color: #f56c6c;
  padding: 0.1em 0.3em;
  border-radius: 3px;
  font-weight: 600;
}
</style>
