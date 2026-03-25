<template>
  <el-alert
    v-if="visible"
    :title="title"
    :type="type || 'warning'"
    :description="description"
    show-icon
    class="my-4"
  >
    <template #default>
      <div class="mt-2 flex space-x-4">
        <slot name="actions">
          <el-button size="small" type="primary" plain @click="$emit('action')">{{ actionText }}</el-button>
        </slot>
      </div>
    </template>
  </el-alert>
</template>

<script setup lang="ts">
defineProps<{
  visible: boolean
  title: string
  description?: string
  type?: 'success' | 'warning' | 'info' | 'error'
  actionText?: string
}>()

defineEmits(['action'])
</script>
