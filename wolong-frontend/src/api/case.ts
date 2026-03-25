import request from '../utils/request'

export function createCase(profile: string): Promise<any> {
  return request({
    url: '/cases',
    method: 'post',
    data: {
      profile
    }
  })
}

export function generateSearchStrategy(caseId: string): Promise<any> {
  return request({
    url: `/cases/${caseId}/search-strategy`,
    method: 'post'
  })
}

export function startCollectionTask(caseId: string, config: any): Promise<any> {
  return request({
    url: `/cases/${caseId}/start-collection`,
    method: 'post',
    data: config
  })
}

export function getCollectionStatus(caseId: string): Promise<any> {
  return request({
    url: `/cases/${caseId}/collection-status`,
    method: 'get'
  })
}

export function getFacts(caseId: string): Promise<any> {
  return request({
    url: `/cases/${caseId}/facts`,
    method: 'get'
  })
}

export function getAuditElements(caseId: string): Promise<any> {
  return request({
    url: `/cases/${caseId}/audit-elements`,
    method: 'get'
  })
}

export function getEvidences(caseId: string, evidenceIds: string[]): Promise<any> {
  return request({
    url: `/cases/${caseId}/evidences`,
    method: 'get',
    params: { ids: evidenceIds.join(',') }
  })
}

export function feedbackFact(caseId: string, factId: string, type: 'ERROR' | 'LOW_VALUE'): Promise<any> {
  return request({
    url: `/cases/${caseId}/facts/${factId}/feedback`,
    method: 'post',
    data: { type }
  })
}

export function getSandboxGraph(caseId: string): Promise<any> {
  return request({
    url: `/cases/${caseId}/sandbox`,
    method: 'get'
  })
}

export function regenerateSandboxGraph(caseId: string): Promise<any> {
  return request({
    url: `/cases/${caseId}/sandbox/regenerate`,
    method: 'post'
  })
}

export function submitIntervention(caseId: string, payload: any): Promise<any> {
  return request({
    url: `/cases/${caseId}/sandbox/intervene`,
    method: 'post',
    data: payload
  })
}

// --- Cycle 5 & 6 ---

export function submitContext(caseId: string, contextData: any): Promise<any> {
  return request({
    url: `/cases/${caseId}/context`,
    method: 'put',
    data: contextData
  })
}

export function getWorldline(caseId: string): Promise<any> {
  return request({
    url: `/cases/${caseId}/worldline`,
    method: 'get'
  })
}

export function getWorldlineProbe(caseId: string): Promise<any> {
  return request({
    url: `/cases/${caseId}/worldline/probe`,
    method: 'get'
  })
}

export function regenerateWorldline(caseId: string): Promise<any> {
  return request({
    url: `/cases/${caseId}/worldline/regenerate`,
    method: 'post'
  })
}

export function submitWorldlineIntervention(caseId: string, text: string): Promise<any> {
  return request({
    url: `/cases/${caseId}/worldline/intervene`,
    method: 'post',
    data: { text }
  })
}

export function getWhitepaper(caseId: string): Promise<any> {
  return request({
    url: `/cases/${caseId}/whitepaper`,
    method: 'get'
  })
}

export function submitWhitepaperFeedback(caseId: string, feedbackData: any): Promise<any> {
  return request({
    url: `/cases/${caseId}/feedbacks`,
    method: 'post',
    data: feedbackData
  })
}

// --- Phase 9: Historical Projects ---
export function getHistoricalCases(): Promise<any> {
  return request({
    url: '/cases/history',
    method: 'get'
  })
}

export function deleteHistoricalCase(caseId: string): Promise<any> {
  return request({
    url: `/cases/${caseId}`,
    method: 'delete'
  })
}

export function testLlmConnection(providerConfig: any): Promise<any> {
  return request({
    url: '/llm/test',
    method: 'post',
    data: providerConfig
  })
}
