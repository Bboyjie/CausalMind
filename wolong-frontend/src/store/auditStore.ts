import { defineStore } from 'pinia'

export const useAuditStore = defineStore('audit', {
  state: () => ({
    selectedFactId: null as string | null
  }),
  actions: {
    setSelectedFact(id: string | null) {
      this.selectedFactId = id
    }
  }
})
