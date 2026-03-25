import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'Home',
    redirect: '/case/create', // Redirect to case creation for now
  },
  {
    path: '/case/create',
    name: 'CaseCreate',
    component: () => import('../views/CaseCreateView.vue'),
    meta: { title: '创建决策案例' }
  },
  {
    path: '/case/:id/workflow',
    name: 'CaseWorkflow',
    component: () => import('../views/WorkflowLayout.vue'),
    meta: { title: '案例工作流' },
    redirect: to => {
      // Default to strategy config for step 1
      return { name: 'StrategyConfig', params: { id: to.params.id } }
    },
    children: [
      {
        path: 'strategy',
        name: 'StrategyConfig',
        component: () => import('../views/StrategyConfigView.vue'),
        meta: { title: '搜商策略与信息源配置' }
      },
      {
        path: 'collection',
        name: 'CollectionProgress',
        component: () => import('../views/CollectionProgressView.vue'),
        meta: { title: '采集进度大盘' }
      },
      {
        path: 'summary',
        name: 'InfoPoolSummary',
        component: () => import('../views/InfoPoolSummaryView.vue'),
        meta: { title: '信息池总览' }
      },
      {
        path: 'facts',
        name: 'FactsPool',
        component: () => import('../views/FactsPoolView.vue'),
        meta: { title: '信息池概览' }
      },
      {
        path: 'audit',
        name: 'FactAudit',
        component: () => import('../views/FactAuditView.vue'),
        meta: { title: '事实审查与认知审计' }
      },
      {
        path: 'sandbox',
        name: 'CausalSandbox',
        component: () => import('../views/CausalSandboxView.vue'),
        meta: { title: '因果沙盘与反事实推演' }
      },
      {
        path: 'worldline',
        name: 'WorldlineSimulator',
        component: () => import('../views/WorldlineSimulatorView.vue'),
        meta: { title: '世界线演化与个人语境' }
      },
      {
        path: 'whitepaper',
        name: 'WhitepaperReader',
        component: () => import('../views/WhitepaperReader.vue'),
        meta: { title: '破局白皮书' }
      }
    ]
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/SettingsView.vue'),
    meta: { title: '大模型配置' }
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('../views/HistoryView.vue'),
    meta: { title: '历史决策档案' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
