<template>
  <div class="info-pool-summary animate-fade-in flex flex-col h-full">
    <div class="flex-1 overflow-y-auto p-4 sm:p-8">
      
      <div class="flex items-center space-x-3 mb-8">
        <el-icon class="text-3xl text-green-500"><CircleCheckFilled /></el-icon>
        <h2 class="text-2xl font-bold text-slate-800">信息采集完成，专属信息池已建立</h2>
      </div>

      <WarningAlert 
        v-if="caseStore.collectionStats?.valid_sources < 20"
        visible
        type="error"
        title="有效样本量不足"
        description="系统只收集到少于20篇的有效参考资料，这可能会导致后续大模型分析出现严重的幻觉。建议重新调整你的搜索策略（如扩大时间维度或增加不同视角的修饰词）。"
        actionText="返回上一步调整"
        @action="goBack"
      />

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
        <!-- Pool Overview Card -->
        <div class="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
          <h3 class="text-lg font-bold text-slate-800 mb-4 flex items-center">
            <el-icon class="mr-2 text-indigo-500"><PieChart /></el-icon>信息质量分布
          </h3>
          <ul class="space-y-4">
            <li class="flex justify-between items-center text-slate-600">
              <span>总爬取网页数</span>
              <span class="font-mono font-bold">{{ caseStore.collectionStats?.total_scraped || 0 }}</span>
            </li>
            <li class="flex justify-between items-center text-slate-600">
              <span>配置抓取上限(篇/平台)</span>
              <span class="font-mono font-bold">{{ platformLimitText }}</span>
            </li>
            <li class="flex justify-between items-center text-slate-600">
              <span>评论抓取开关</span>
              <span class="font-mono font-bold">{{ commentSwitchText }}</span>
            </li>
            <li class="flex justify-between items-center text-slate-600">
              <span>单帖评论上限</span>
              <span class="font-mono font-bold">{{ commentLimitText }}</span>
            </li>
            <li class="flex justify-between items-center text-slate-600">
              <span>分块参数</span>
              <span class="font-mono font-bold">{{ extractionConfigText }}</span>
            </li>
            <li class="flex justify-between items-center text-slate-600">
              <span>配置执行对账</span>
              <span class="font-mono font-bold">{{ reconciliationText }}</span>
            </li>
            <li class="flex justify-between items-center text-slate-600">
              <span>实际评论条目</span>
              <span class="font-mono font-bold">{{ caseStore.collectionStats?.crawler_observed?.comment_items_total || 0 }}</span>
            </li>
            <li class="flex justify-between items-center text-slate-600">
              <span>软广软文过滤量</span>
              <span class="font-mono font-bold text-rose-500">{{ caseStore.collectionStats?.filtered?.ads || 0 }}</span>
            </li>
            <li class="flex justify-between items-center text-slate-600">
              <span>高度重复剔除数</span>
              <span class="font-mono font-bold text-amber-500">{{ caseStore.collectionStats?.filtered?.duplicates || 0 }}</span>
            </li>
            <li class="flex justify-between items-center text-slate-600">
              <span>无有效信息发泄贴</span>
              <span class="font-mono font-bold text-orange-400">{{ caseStore.collectionStats?.filtered?.emotional_venting || 0 }}</span>
            </li>
            <li class="pt-4 border-t border-slate-100 flex justify-between items-center text-lg font-bold">
              <span class="text-slate-800">高质量有效信息源</span>
              <span class="text-green-600 font-mono">{{ caseStore.collectionStats?.valid_sources || 0 }} 篇</span>
            </li>
          </ul>
        </div>

        <!-- Next Step Card -->
        <div class="bg-gradient-to-br from-indigo-50 to-blue-50 rounded-xl border border-blue-100 p-6 flex flex-col justify-between">
          <div>
            <h3 class="text-lg font-bold text-indigo-900 mb-2">下一周期工作流提示</h3>
            <p class="text-indigo-700/80 text-sm leading-relaxed mb-6">
              信息池已装载完毕。由于我们在“开发周期 2”，此阶段仅用于验证收集链路。<br/><br/>
              在后续的**开发周期 3**中，我们将基于此处提取的数十篇高质量信源，送入“认知审计台”与事实审查代理网，对每条事实的真伪、局限性、立场进行交叉验证。
            </p>
          </div>
          
          <el-button 
            type="primary" 
            size="large" 
            class="w-full text-base tracking-wide"
            @click="moveToNextCycle"
          >
            进入认知审计台
            <el-icon class="ml-2"><Right /></el-icon>
          </el-button>
        </div>
      </div>
      
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheckFilled, PieChart, Right } from '@element-plus/icons-vue'
import WarningAlert from '../components/WarningAlert.vue'
import { useCaseStore } from '../store/caseStore'
import { getCollectionStatus } from '../api/case'

const router = useRouter()
const route = useRoute()
const caseStore = useCaseStore()
const caseId = route.params.id as string

const platformLimitText = computed(() => {
  const platforms = caseStore.collectionStats?.crawler_config?.platforms || []
  if (!Array.isArray(platforms) || platforms.length === 0) return '未提供'
  return platforms.map((p: any) => `${p.name}:${p.max_notes}`).join(' / ')
})

const commentSwitchText = computed(() => {
  const platforms = caseStore.collectionStats?.crawler_config?.platforms || []
  if (!Array.isArray(platforms) || platforms.length === 0) return '未提供'
  return platforms.map((p: any) => `${p.name}:${p.get_comments ? '开' : '关'}`).join(' / ')
})

const commentLimitText = computed(() => {
  const platforms = caseStore.collectionStats?.crawler_config?.platforms || []
  if (!Array.isArray(platforms) || platforms.length === 0) return '未提供'
  return platforms.map((p: any) => `${p.name}:${p.max_comments_count_singlenotes ?? '默认'}`).join(' / ')
})

const extractionConfigText = computed(() => {
  const extraction = caseStore.collectionStats?.crawler_config?.extraction || {}
  const size = extraction.chunk_size ?? '12'
  const overlap = extraction.chunk_overlap ?? '0'
  const tokens = extraction.max_chunk_tokens ?? '0'
  return `size:${size} ov:${overlap} tok:${tokens}`
})

const reconciliationText = computed(() => {
  const r = caseStore.collectionStats?.crawler_reconciliation || {}
  const postCapOk = r.observed_posts_within_cap === false ? '帖子上限异常' : '帖子上限OK'
  const commentOk = r.comment_toggle_respected === false ? '评论开关异常' : '评论开关OK'
  return `${postCapOk} / ${commentOk}`
})

onMounted(async () => {
  // Refresh-safe stats hydration: store resets on page reload.
  if (caseStore.collectionStats?.status === 'COMPLETED') return
  try {
    const res = await getCollectionStatus(caseId)
    if (res.code === 200) {
      caseStore.collectionStats = res.data
    }
  } catch {
    ElMessage.warning('统计信息加载失败，稍后可刷新重试')
  }
})

const goBack = () => {
  router.push({ name: 'StrategyConfig', params: { id: route.params.id } })
}

const moveToNextCycle = () => {
  router.push({ name: 'FactAudit', params: { id: route.params.id } })
}
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.4s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
