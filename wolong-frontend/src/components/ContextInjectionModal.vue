<template>
  <el-dialog
    v-model="visible"
    title="注入个人约束语境"
    width="560px"
    :close-on-click-modal="false"
    :show-close="false"
    class="rounded-xl overflow-hidden"
  >
    <div class="mb-4 text-sm text-slate-600 bg-blue-50 p-3 rounded border border-blue-100 flex items-start gap-2">
      <el-icon class="text-blue-500 mt-1"><InfoFilled /></el-icon>
      <p>
        世界线推演需要叠加您自身的现状与硬性约束。此数据仅用于本次推演计算，以消除幸存者偏差。
      </p>
    </div>

    <el-form :model="form" ref="formRef" label-position="top">
      <template v-if="hasDynamicProbes">
        <el-form-item
          v-for="probe in probes"
          :key="probe.node_id"
          :label="probe.probe_question"
          :prop="`probe_answers.${probe.node_id}`"
          :rules="[{ required: true, message: '请补充该变量的真实状态' }]"
        >
          <div class="text-xs text-slate-500 mb-2 leading-relaxed">{{ probe.why_it_matters }}</div>
          <el-input
            v-model="form.probe_answers[probe.node_id]"
            type="textarea"
            :rows="2"
            placeholder="请给出可量化、可落地的当前状态"
          />
        </el-form-item>
      </template>

      <template v-else>
        <el-form-item label="核心诉求 (最想解决的痛点)" prop="goal" :rules="[{ required: true, message: '请输入核心诉求' }]">
          <el-input
            v-model="form.goal"
            placeholder="例如：3个月内必须在本地找到10k以上的开发工作"
            type="textarea"
            :rows="2"
          />
        </el-form-item>

        <el-form-item label="当前的劣势/短板" prop="weakness" :rules="[{ required: true, message: '请客观评估劣势' }]">
          <el-input
            v-model="form.weakness"
            placeholder="例如：第一学历专科，脱产空窗期接近半年"
            type="textarea"
            :rows="2"
          />
        </el-form-item>

        <el-form-item label="不可妥协的底线约束 (时间/资金/地域)" prop="constraints">
          <el-input
            v-model="form.constraints"
            placeholder="例如：最高只能接受降薪30%，绝不去外包"
            type="textarea"
            :rows="2"
          />
        </el-form-item>
      </template>
    </el-form>

    <template #footer>
      <div class="flex justify-end gap-3">
        <el-button @click="visible = false">暂不推演</el-button>
        <el-button type="primary" :loading="isSubmitting" @click="submitContext">
          注入语境并开始演化
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { InfoFilled } from '@element-plus/icons-vue'

interface ProbeQuestion {
  node_id: string
  probe_question: string
  why_it_matters: string
}

const props = defineProps<{
  modelValue: boolean
  probes?: ProbeQuestion[]
}>()

const emit = defineEmits(['update:modelValue', 'submit'])

const visible = computed({
  get: () => props.modelValue,
  set: val => emit('update:modelValue', val)
})

const formRef = ref()
const isSubmitting = ref(false)

const form = reactive({
  goal: '',
  weakness: '',
  constraints: '',
  probe_answers: {} as Record<string, string>
})

const probes = computed(() => props.probes || [])
const hasDynamicProbes = computed(() => probes.value.length > 0)

watch(probes, val => {
  if (!val.length) return
  for (const probe of val) {
    if (form.probe_answers[probe.node_id] === undefined) {
      form.probe_answers[probe.node_id] = ''
    }
  }
}, { immediate: true, deep: true })

const submitContext = async () => {
  if (!formRef.value) return
  let valid = false
  try {
    valid = await formRef.value.validate()
  } catch {
    valid = false
  }
  if (!valid) return
  isSubmitting.value = true
  try {
    if (hasDynamicProbes.value) {
      emit('submit', {
        probe_answers: { ...form.probe_answers },
        probe_details: probes.value.map(item => ({
          node_id: item.node_id,
          question: item.probe_question,
          why_it_matters: item.why_it_matters,
          answer: form.probe_answers[item.node_id] || ''
        }))
      })
    } else {
      emit('submit', {
        goal: form.goal,
        weakness: form.weakness,
        constraints: form.constraints
      })
    }
    visible.value = false
  } finally {
    isSubmitting.value = false
  }
}
</script>
