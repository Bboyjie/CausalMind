import { defineStore } from 'pinia'
import { createCase as apiCreateCase } from '../api/case'

export const CaseStatus = {
  CREATED: 'CREATED',
  STRATEGY_GENERATING: 'STRATEGY_GENERATING',
  COLLECTING: 'COLLECTING',
  FUSING_AND_AUDITING: 'FUSING_AND_AUDITING',
  GRAPH_BUILDING: 'GRAPH_BUILDING',
  CAUSAL_ANALYSIS: 'CAUSAL_ANALYSIS',
  INFO_GATHERING: 'INFO_GATHERING',
  FACT_CHECKING: 'FACT_CHECKING',
  WORLDLINE_EVOLUTION: 'WORLDLINE_EVOLUTION',
  WHITE_PAPER: 'WHITE_PAPER',
  ARCHIVED: 'ARCHIVED'
} as const

export type CaseStatusType = typeof CaseStatus[keyof typeof CaseStatus]

export interface CaseDetail {
  id: string
  profile: string
  status: CaseStatusType
  created_at: string
}

export const useCaseStore = defineStore('case', {
  state: () => ({
    currentCaseId: null as string | null,
    currentCaseDetail: null as CaseDetail | null,
    searchKeywords: [] as string[],
    dataSourceConfig: null as any,
    collectionStats: null as any,
    isLoading: false
  }),
  actions: {
    async createCase(profile: string) {
      this.isLoading = true
      try {
        const response = await apiCreateCase(profile)
        if (response.code === 200) {
          this.currentCaseDetail = response.data
          this.currentCaseId = response.data.id
          return response.data
        }
        throw new Error(response.message || 'Failed to create case')
      } catch (error) {
        console.error('Error creating case:', error)
        throw error
      } finally {
        this.isLoading = false
      }
    },
    updateStatus(newStatus: CaseStatusType) {
      if (!this.currentCaseDetail) {
         this.currentCaseDetail = { id: this.currentCaseId || 'unknown', profile: '', status: newStatus, created_at: new Date().toISOString() }
      } else {
         this.currentCaseDetail.status = newStatus
      }
    }
  }
})
