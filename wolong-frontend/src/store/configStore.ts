import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export interface Provider {
  id: string
  name: string
  baseUrl: string
  apiKey: string
  defaultModel: string
}

export interface StageAssignments {
  collection: string
  audit: string
  sandbox: string
  worldline: string
}

export const useConfigStore = defineStore('config', () => {
  const providers = ref<Provider[]>([])
  
  const stageAssignments = ref<StageAssignments>({
    collection: '',
    audit: '',
    sandbox: '',
    worldline: ''
  })

  // Load from LocalStorage
  const loadState = () => {
    const saved = localStorage.getItem('wolong_llm_config')
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        if (parsed.providers) providers.value = parsed.providers
        if (parsed.stageAssignments) stageAssignments.value = parsed.stageAssignments
      } catch (e) {
        console.error('Failed to parse config from localStorage', e)
      }
    } else {
      // Default Provider Example
      const defaultProvider: Provider = {
        id: 'default',
        name: 'OpenAI (Default)',
        baseUrl: 'https://api.openai.com/v1',
        apiKey: '',
        defaultModel: 'gpt-4o'
      }
      providers.value = [defaultProvider]
      stageAssignments.value = {
        collection: 'default',
        audit: 'default',
        sandbox: 'default',
        worldline: 'default'
      }
    }
  }

  // Save to LocalStorage automatically when state changes
  watch([providers, stageAssignments], () => {
    localStorage.setItem('wolong_llm_config', JSON.stringify({
      providers: providers.value,
      stageAssignments: stageAssignments.value
    }))
  }, { deep: true })

  loadState()

  return {
    providers,
    stageAssignments
  }
})
