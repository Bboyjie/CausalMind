<template>
  <div class="facts-pool-view w-full h-full p-6 md:p-8 animate-fade-in bg-slate-50/30">
    <div class="max-w-7xl mx-auto flex flex-col h-full">
      
      <!-- Header -->
      <div class="flex items-center justify-between mb-8 pb-4 border-b border-slate-200">
        <div>
          <h1 class="text-3xl font-black text-slate-800 flex items-center gap-3">
            <span class="text-4xl">🌊</span> 智能信息池
          </h1>
          <p class="text-slate-500 mt-2 font-medium">深度清洗与凝练后的高价值情报集，共收录 {{ facts.length }} 条核心摘要。</p>
        </div>
        <div class="flex items-center gap-4">
          <el-button @click="goBack" plain round size="large" class="shadow-sm hover:shadow-md transition-all">
            <el-icon class="mr-1"><Back /></el-icon> 返回看盘
          </el-button>
          <el-button @click="goToAudit" type="primary" round size="large" class="shadow-sm hover:shadow-md transition-all">
            开始认知审计 <el-icon class="ml-1"><Right /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="flex-1 flex flex-col items-center justify-center py-20">
        <el-icon class="text-6xl text-indigo-400 animate-spin mb-4"><Loading /></el-icon>
        <p class="text-slate-500 font-medium tracking-wider">正在打捞高价值情报...</p>
      </div>

      <!-- Empty State -->
      <div v-else-if="facts.length === 0" class="flex-1 flex flex-col items-center justify-center py-20 text-center bg-white rounded-3xl border border-dashed border-slate-300 shadow-sm">
        <span class="text-6xl text-slate-300 mb-6">🏝️</span>
        <h3 class="text-xl font-bold text-slate-600 mb-2">信息池目前还是干涸的</h3>
        <p class="text-slate-400 max-w-sm">搜狗或爬虫引擎可能还在路上，或者刚刚抛下的过滤网并未捞起足够有价值的金沙。请稍后再来看看。</p>
        <el-button type="primary" plain class="mt-6" @click="fetchData">刷新池水</el-button>
      </div>

      <!-- Masonry Grid -->
      <div v-else class="masonry-grid flex-1 overflow-y-auto pb-12 pr-2 custom-scrollbar">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 items-start">
          
          <div v-for="fact in facts" :key="fact.id" class="fact-card break-inside-avoid shadow-sm hover:shadow-xl transition-all duration-300 bg-white border border-slate-100/80 rounded-2xl overflow-hidden flex flex-col transform hover:-translate-y-1 group">
            
            <!-- Card Header: Platform tags -->
            <div class="px-5 py-3 border-b border-slate-50 bg-slate-50/50 flex flex-wrap gap-2 items-center justify-between">
              <div class="flex flex-wrap gap-1">
                <el-tag v-for="(source, idx) in fact.sources.slice(0, 2)" :key="idx" size="small" effect="plain" class="!bg-white font-bold !text-slate-600 !border-slate-200 shadow-sm">
                  {{ extractPlatform(source.url) }}
                </el-tag>
                <el-tag v-if="fact.sources.length > 2" size="small" type="info" effect="plain" class="!bg-white">
                  +{{ fact.sources.length - 2 }}
                </el-tag>
              </div>
              
              <div class="text-xs text-slate-400 font-mono tracking-tighter opacity-0 group-hover:opacity-100 transition-opacity">
                #{{ fact.id.split('_').pop() }}
              </div>
            </div>
            
            <!-- Card Body: Content -->
            <div class="p-5 flex-1 flex flex-col relative text-slate-700">
              <div class="text-[15px] leading-relaxed relative" :class="{'line-clamp-6': !fact.expanded}">
                {{ fact.content }}
              </div>
              
              <div v-if="!fact.expanded && fact.content.length > 150" class="absolute bottom-5 left-0 w-full pt-12 text-center bg-gradient-to-t from-white via-white/80 to-transparent"></div>
              
              <button v-if="fact.content.length > 150" @click="fact.expanded = !fact.expanded" class="text-indigo-500 hover:text-indigo-700 text-sm font-medium mt-3 self-start focus:outline-none transition-colors">
                {{ fact.expanded ? '收起文章的尾巴' : '阅读核心腹地...' }}
              </button>

              <div v-if="fact.audit_alerts?.length" class="mt-3 space-y-1">
                <div
                  v-for="(alert, idx) in fact.audit_alerts.slice(0, 2)"
                  :key="idx"
                  class="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded px-2 py-1"
                >
                  {{ alert.message }}
                </div>
              </div>
              <div v-if="fact.counter_evidence" class="mt-2 text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded px-2 py-1">
                反面证据：{{ fact.counter_evidence }}
              </div>
            </div>
            
            <!-- Card Footer: Tags & Actions -->
            <div class="px-5 py-4 bg-slate-50/30 border-t border-slate-100 mt-auto flex items-end justify-between">
              <!-- AI Tags -->
              <div class="flex-1 flex flex-wrap gap-2 pr-4">
                <el-tag 
                  effect="light" 
                  round 
                  :type="getFactTypeColor(fact.type)"
                  class="!border-none font-bold shadow-sm px-3"
                >
                  {{ formatFactType(fact.type) }}
                </el-tag>
                <el-tag effect="plain" round type="info" class="!border-slate-200">
                  引文 {{ fact.evidence_ids?.length || 0 }}
                </el-tag>
              </div>
              
              <!-- Source Link Actions -->
              <el-dropdown trigger="click" placement="bottom-end" v-if="fact.sources.length > 0">
                <el-button type="primary" circle class="shadow-md !bg-indigo-600 hover:!bg-indigo-700 border-none transform font-bold transition-transform hover:scale-110">
                  <el-icon><Link /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item
                      v-for="(source, idx) in fact.sources"
                      :key="idx"
                      @click="openSource(source.url, source.source_name, fact.content)"
                    >
                      <div class="flex flex-col">
                        <span class="font-bold text-slate-700">{{ extractPlatform(source.url) }} 原帖</span>
                        <span class="text-xs text-slate-400 truncate max-w-[200px]">{{ source.source_name || source.url }}</span>
                      </div>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
            
          </div>
          
        </div>
      </div>
      
      <!-- Call to action -->
      <div v-if="facts.length > 0 && !loading" class="mt-4 flex justify-center pb-8 shrink-0">
        <el-button type="primary" size="large" round class="px-12 py-6 text-lg shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all" @click="goToAudit">
          信息凝练完毕，开启认知与事实审计 <el-icon class="ml-2"><Right /></el-icon>
        </el-button>
      </div>
      
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Back, Loading, Link, Right } from '@element-plus/icons-vue'
import { getFacts } from '../api/case'

const route = useRoute()
const router = useRouter()
const caseId = route.params.id as string

const loading = ref(true)
const facts = ref<any[]>([])

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getFacts(caseId)
    // Map existing data + local UI state
    facts.value = (res.data || []).map((f: any) => ({
      ...f,
      sources: f.sources || [],
      expanded: false
    }))
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '获取提取结果失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})

const goBack = () => {
  router.push(`/case/${caseId}/workflow/collection`)
}

const goToAudit = () => {
  router.push(`/case/${caseId}/workflow/audit`)
}

const buildFallbackSourceUrl = (sourceName: string, content: string) => {
  const name = String(sourceName || '').toLowerCase()
  const q = encodeURIComponent(String(content || '').replace(/\s+/g, ' ').slice(0, 40))
  if (!q) return ''
  if (name.includes('xhs') || name.includes('xiaohongshu')) return `https://www.xiaohongshu.com/search_result?keyword=${q}`
  if (name.includes('zhihu')) return `https://www.zhihu.com/search?type=content&q=${q}`
  if (name.includes('douyin') || name === 'dy') return `https://www.douyin.com/search/${q}`
  if (name.includes('weibo') || name === 'wb') return `https://s.weibo.com/weibo?q=${q}`
  if (name.includes('bili')) return `https://search.bilibili.com/all?keyword=${q}`
  if (name.includes('tieba')) return `https://tieba.baidu.com/f?kw=${q}`
  return ''
}

const openSource = (url: string, sourceName = '', factContent = '') => {
  const raw = (url || '').trim()
  let normalized = ''
  if (raw && raw !== '#' && !raw.toLowerCase().startsWith('javascript:')) {
    normalized = /^https?:\/\//i.test(raw) ? raw : `https://${raw}`
  } else {
    normalized = buildFallbackSourceUrl(sourceName, factContent)
  }
  if (!normalized) {
    ElMessage.warning('该条来源未提供可访问原帖链接')
    return
  }
  window.open(normalized, '_blank', 'noopener,noreferrer')
}

// Utility formatting functions
const extractPlatform = (url: string) => {
  if (!url) return '未知来源'
  if (url.includes('xiaohongshu')) return '小红书'
  if (url.includes('zhihu')) return '知乎'
  if (url.includes('douyin')) return '抖音'
  if (url.includes('bilibili')) return 'B站'
  if (url.includes('weibo')) return '微博'
  if (url.includes('kuaishou')) return '快手'
  if (url.includes('tieba')) return '百度贴吧'
  
  try {
    return new URL(url).hostname.replace('www.', '')
  } catch (e) {
    return '网页来源'
  }
}

const getFactTypeColor = (type: string) => {
  const t = type.toUpperCase()
  if (t === 'DATA' || t.includes('数据')) return 'primary'
  if (t === 'OPINION' || t.includes('观点')) return 'warning'
  if (t === 'EVENT' || t.includes('事件')) return 'success'
  if (t === 'RISK' || t.includes('风险')) return 'danger'
  return 'info'
}

const formatFactType = (type: string) => {
  const t = type.toUpperCase()
  if (t === 'DATA') return '客观数据'
  if (t === 'OPINION') return '主观观点'
  if (t === 'EVENT') return '事件节点'
  if (t === 'RISK') return '风险预警'
  return type
}
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.4s ease-out forwards;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 20px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: #94a3b8;
}

/* Ensure grid items stack naturally */
.masonry-grid {
  align-items: start;
}
</style>
