<template>
  <div class="settings-view max-w-5xl mx-auto p-6 md:p-8 animate-fade-in flex flex-col gap-8">
    
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-slate-800">大模型路由配置 (GenAI Settings)</h1>
        <p class="text-slate-500 mt-2">在这里配置兼容 OpenAI 格式的底层大模型密钥，可针对独立推理阶段分发不同的模型架构。</p>
      </div>
      <el-button @click="router.push('/')" plain>返回首页</el-button>
    </div>

    <!-- Providers Configuration -->
    <el-card shadow="never" class="rounded-2xl border-slate-200">
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <el-icon class="text-blue-500 text-xl"><Setting /></el-icon>
            <span class="font-bold text-lg text-slate-800">服务端点配置 (LLM Providers)</span>
          </div>
          <el-button type="primary" size="small" @click="openProviderModal()">+ 新增服务商</el-button>
        </div>
      </template>

      <el-table :data="configStore.providers" style="width: 100%" class="rounded-lg overflow-hidden border border-slate-100">
        <el-table-column prop="name" label="名称 (Name)" width="180" />
        <el-table-column prop="baseUrl" label="API Base URL" show-overflow-tooltip />
        <el-table-column prop="defaultModel" label="默认模型 (Model)" width="180" />
        <el-table-column label="API Key">
          <template #default="scope">
            <span class="text-slate-400 font-mono select-none">
              {{ scope.row.apiKey ? '••••••••' + scope.row.apiKey.slice(-4) : '未配置' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center">
          <template #default="scope">
            <el-button link type="success" @click="testProvider(scope.row)" :loading="testingProviderId === scope.row.id">测试</el-button>
            <el-button link type="primary" @click="openProviderModal(scope.row)">编辑</el-button>
            <el-button link type="danger" @click="deleteProvider(scope.row.id)" :disabled="configStore.providers.length <= 1">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Stage Assignments -->
    <el-card shadow="never" class="rounded-2xl border-slate-200 bg-slate-50">
      <template #header>
        <div class="flex items-center gap-2">
          <el-icon class="text-green-500 text-xl"><Connection /></el-icon>
          <span class="font-bold text-lg text-slate-800">推理阶段绑定 (Stage Assignments)</span>
        </div>
        <p class="text-sm text-slate-500 mt-1">为核心认知引擎指派不同算力的大模型。例如数据抓取使用高速泛用模型，因果推演使用深度推理模型。</p>
      </template>
      
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        
        <!-- Collection Stage -->
        <div class="bg-white p-4 rounded-xl border border-slate-200">
          <h3 class="font-bold text-slate-700 mb-2 flex items-center"><el-icon class="mr-1"><Search /></el-icon> 数据过滤池</h3>
          <p class="text-xs text-slate-400 mb-4 h-8">快速分类与降噪，需高并发低延迟。</p>
          <el-select v-model="configStore.stageAssignments.collection" class="w-full">
            <el-option v-for="p in configStore.providers" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </div>

        <!-- Audit Stage -->
        <div class="bg-white p-4 rounded-xl border border-slate-200">
          <h3 class="font-bold text-slate-700 mb-2 flex items-center"><el-icon class="mr-1"><Finished /></el-icon> 事实审核台</h3>
          <p class="text-xs text-slate-400 mb-4 h-8">交叉比对结构化信息，需良好的上下文窗口。</p>
          <el-select v-model="configStore.stageAssignments.audit" class="w-full">
            <el-option v-for="p in configStore.providers" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </div>

        <!-- Sandbox Stage -->
        <div class="bg-white p-4 rounded-xl border border-slate-200">
          <h3 class="font-bold text-indigo-700 mb-2 flex items-center"><el-icon class="mr-1"><DataAnalysis /></el-icon> 因果沙盘分析</h3>
          <p class="text-xs text-indigo-400 mb-4 h-8">构建影响因子DAG树，需强逻辑演绎能力。</p>
          <el-select v-model="configStore.stageAssignments.sandbox" class="w-full">
            <el-option v-for="p in configStore.providers" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </div>

        <!-- Worldline Stage -->
        <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm border-blue-200">
          <h3 class="font-bold text-blue-700 mb-2 flex items-center"><el-icon class="mr-1"><Guide /></el-icon> 世界线演化</h3>
          <p class="text-xs text-blue-400 mb-4 h-8">融合个人破局背景树，强烈推荐最高级模型(o1类)。</p>
          <el-select v-model="configStore.stageAssignments.worldline" class="w-full">
            <el-option v-for="p in configStore.providers" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </div>

      </div>
    </el-card>

    <!-- Modal for Provider -->
    <el-dialog
      v-model="modalVisible"
      :title="editingProvider.id ? '编辑服务商' : '新增服务商'"
      width="500px"
      append-to-body
    >
      <el-form label-position="top">
        <el-form-item label="名称 (如: OpenAI, 智谱, SiliconFlow)">
          <el-input v-model="form.name" placeholder="请输入标识名称" />
        </el-form-item>
        <el-form-item label="Base URL (OpenAI 协议接口格式)">
          <el-input v-model="form.baseUrl" placeholder="https://api.openai.com/v1" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="form.apiKey" type="password" show-password placeholder="sk-..." />
        </el-form-item>
        <el-form-item label="默认模型 (如: gpt-4o, qwen-max)">
          <el-input v-model="form.defaultModel" placeholder="gpt-4o" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="modalVisible = false">取消</el-button>
          <el-button type="primary" @click="saveProvider">保存</el-button>
        </span>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Setting, Connection, Search, Finished, DataAnalysis, Guide } from '@element-plus/icons-vue'
import { useConfigStore, type Provider } from '../store/configStore'
import { testLlmConnection } from '../api/case'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const configStore = useConfigStore()

const modalVisible = ref(false)
const testingProviderId = ref<string | null>(null)
const editingProvider = ref<Partial<Provider>>({})
const form = ref<Partial<Provider>>({})

const openProviderModal = (provider?: Provider) => {
  if (provider) {
    editingProvider.value = provider
    form.value = { ...provider }
  } else {
    editingProvider.value = {}
    form.value = {
      name: '',
      baseUrl: 'https://api.openai.com/v1',
      apiKey: '',
      defaultModel: ''
    }
  }
  modalVisible.value = true
}

const saveProvider = () => {
  if (!form.value.name || !form.value.baseUrl || !form.value.defaultModel) {
    ElMessage.error('请填写完整的必要信息')
    return
  }
  
  if (editingProvider.value.id) {
    // Edit
    const index = configStore.providers.findIndex(p => p.id === editingProvider.value.id)
    if (index > -1) {
      configStore.providers[index] = { ...configStore.providers[index], ...form.value } as Provider
    }
  } else {
    // Create
    const newId = 'provider_' + Date.now()
    configStore.providers.push({
      id: newId,
      name: form.value.name,
      baseUrl: form.value.baseUrl,
      apiKey: form.value.apiKey,
      defaultModel: form.value.defaultModel
    } as Provider)
  }
  
  modalVisible.value = false
  ElMessage.success('保存成功')
}

const deleteProvider = (id: string) => {
  ElMessageBox.confirm('确定要删除此模型服务商吗？如果删除了当前绑定的服务商，部分推理阶段将会失效。', '确认警告', {
    confirmButtonText: '删除',
    cancelButtonText: '保留',
    type: 'warning'
  }).then(() => {
    configStore.providers = configStore.providers.filter(p => p.id !== id)
    ElMessage.success('服务商已删除')
  }).catch(() => {})
}

const testProvider = async (provider: Provider) => {
  testingProviderId.value = provider.id
  try {
    const res = await testLlmConnection(provider)
    if (res.code === 200) {
      ElMessage.success(`[${provider.name}] 测试连接通过! 延迟低`)
    }
  } catch (error: any) {
    ElMessage.error(`[${provider.name}] 测试失败: ${error.message}`)
  } finally {
    testingProviderId.value = null
  }
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
