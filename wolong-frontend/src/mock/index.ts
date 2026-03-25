import MockAdapter from 'axios-mock-adapter'

export function setupMock() {
  // Use a global mock adapter on the default axios instance,
  // or on the custom instance if exported. Here we intercept the global one
  // but it's better to intercept the exact instance. So we'll import it.
  
  // Actually, since we use `src/utils/request.ts`, let's mock the underlying axios.
  // We'll pass the axios instance to the mock setup in main.ts
}

// We will do another way: export a function that takes the axios instance.
export function initMock(requestInstance: any) {
  const mock = new MockAdapter(requestInstance, { delayResponse: 1500 })

  mock.onPost('/cases').reply(config => {
    const data = JSON.parse(config.data || '{}')
    return [200, {
      code: 200,
      message: 'success',
      data: {
        id: 'case_' + Math.floor(Math.random() * 10000),
        profile: data.profile || '',
        status: 'CREATED',
        created_at: new Date().toISOString()
      }
    }]
  })

  // Strategy Generation: 2s delay, returns keywords
  mock.onPost(/\/cases\/case_.*\/search-strategy/).reply(() => {
    return [200, {
      code: 200,
      data: {
        keywords: [
          "潍坊 IT开发 薪资 2025",
          "大专 三年经验 程序员 转型 潍坊"
        ],
        recommended_limit: 100
      }
    }]
  })

  // Start Collection
  mock.onPost(/\/cases\/case_.*\/start-collection/).reply(() => {
    return [200, {
      code: 200,
      message: 'Collection started'
    }]
  })

  // Collection Status (Simulate 0 -> 100%)
  // In a real mock server, we'd need state to increment progress.
  // We'll store a simple static variable here to simulate progress across calls.
  let progressMap: any = {}
  
  mock.onGet(/\/cases\/(case_.*)\/collection-status/).reply(config => {
    const match = config.url?.match(/\/cases\/(case_.*)\/collection-status/)
    const caseId = match ? match[1] : 'unknown'
    
    if (!caseId) return [400, {}]

    if (progressMap[caseId] === undefined) {
      progressMap[caseId] = 0
    }
    
    // Increment progress
    progressMap[caseId] += 25
    
    if (progressMap[caseId] >= 100) {
      return [200, {
        code: 200,
        data: {
          status: "COMPLETED",
          progress: 100,
          total_scraped: 150,
          filtered: {
            ads: 30,
            duplicates: 20,
            emotional_venting: 15
          },
          valid_sources: 85
        }
      }]
    } else {
      return [200, {
        code: 200,
        data: {
          status: "COLLECTING",
          progress: progressMap[caseId]
        }
      }]
    }
  })

  // Cycle 3: Feedback
  mock.onPost(/\/cases\/case_.*\/facts\/fact_.*\/feedback/).reply(() => {
    return [200, {
      code: 200,
      message: 'Feedback received'
    }]
  })

  // Cycle 4: Sandbox Graph Initialization
  mock.onGet(/\/cases\/case_.*\/sandbox/).reply(() => {
    return [200, {
      code: 200,
      data: {
        nodes: [
          {id: "n1", name: "大专学历门槛", status: "fixed", type: "objective", val: 1},
          {id: "n2", name: "面试邀请率", status: "variable", type: "objective", val: 0.3},
          {id: "n3", name: "脱产备考期", status: "variable", type: "action", val: 0},
          {id: "n4", name: "期望薪资(>10k)", status: "variable", type: "action", val: 1},
          {id: "n5", name: "外包接受度", status: "variable", type: "action", val: 0}
        ],
        edges: [
          {source: "n1", target: "n2", polarity: "negative", desc: "学历限制导致简历初审被刷"},
          {source: "n3", target: "n2", polarity: "negative", desc: "脱产时间越久，HR顾虑越大"},
          {source: "n4", target: "n2", polarity: "negative", desc: "当地薪资中位数低，高期望致使匹配度下降"},
          {source: "n5", target: "n2", polarity: "positive", desc: "接受外包能大幅增加流程推进的概率"}
        ]
      }
    }]
  })

  // Cycle 4: Submitting Intervention (Simulate counterfactual calculation)
  mock.onPost(/\/cases\/case_.*\/sandbox\/intervene/).reply((config) => {
    const data = JSON.parse(config.data || '{}')
    const intervs = data.interventions || []
    const text = data.text || ''
    
    let n2_new_val = 0.3
    let trend = 'flat'
    let reason = '保持现状不变。'
    let risk = ''

    if (text) {
      if (text.includes('外卖') || text.includes('兼职') || text.includes('滴滴')) {
        n2_new_val = 0.4
        trend = 'up'
        reason = '【文本溯源解析】兼职（如外卖/滴滴）能在短期内缓解资金压力，使得可承受的“低薪底线”上调，从而增加了部分要求坐班但薪水极低的传统企业面试机会。'
        risk = '隐患风险：重体力兼职会大量挤兑技术复习栈的维护时间。'
      } else {
        n2_new_val = 0.2
        trend = 'down'
        reason = `【文本溯源解析】系统对假设“${text}”进行逻辑推演：该行动路径未能有效击中潍坊本地IT市场的核心痛点（即插即用的工业软件熟练工要求），对整体大盘无正向收益。`
        risk = '无效干预：建议改变方向。'
      }
    } else {
      const n3_interv = intervs.find((i: any) => i.node_id === 'n3')
      const n5_interv = intervs.find((i: any) => i.node_id === 'n5')
      
      if (n3_interv && n3_interv.new_val > 0) {
        n2_new_val = 0.1
        trend = 'down'
        reason = '由于拉长了脱产备考期，与本地传统IT企业偏好“即插即用”熟练工的诉求相违背，导致原本就受限的面试邀请率进一步下降。'
        risk = '高风险操作：长时间空窗可能带来求职心态崩盘。'
      } else if (n5_interv && n5_interv.new_val > 0) {
        n2_new_val = 0.8
        trend = 'up'
        reason = '放开外包接受度后，匹配到了大量工厂和政务数字化的外包岗位，面试机会显著增加。'
        risk = '隐患：外包经历可能对下一段职业生涯产生履历折损。'
      }
    }

    return [200, {
      code: 200,
      data: {
        affected_nodes: [
          {id: "n2", new_val: n2_new_val, trend: trend}
        ],
        logic_explanation: reason,
        risk_warning: risk
      }
    }]
  })

  // Cycle 5: Worldline Text Interventions
  mock.onPost(/\/cases\/case_.*\/worldline\/intervene/).reply((config) => {
    const data = JSON.parse(config.data || '{}')
    const text = data.text || ''
    
    let newPaths: any[] = []
    let explanation = ''
    let risk = ''

    if (text.includes('外包') || text.includes('兼职') || text.includes('降薪') || text.includes('外卖')) {
      explanation = '【文本推演解析】侦测到极强的现实妥协倾向。当您将底线边界下移后，短期现金流危机立刻解除，世界线收束为稳定存续的状态。'
      risk = '隐患：舒适区下移可能消磨向外突破的斗志。'
      newPaths = [
        {
          type: "best_case",
          color: "success",
          nodes: [
            {time: "T + 1个月", desc: "入职当地驻场外包，月薪7k维持温饱", triggers: ["接受降薪与外包"]},
            {time: "T + 6个月", desc: "转正稳定输出，利用业余时间补充微服务架构知识", triggers: ["现金流企稳"]},
            {time: "T + 2年", desc: "跳槽至甲方，成为数字化业务骨干", triggers: ["业务梳理能力提升"]}
          ]
        }
      ]
    } else {
      explanation = `【文本推演解析】对干预“${text}”进行测算：此决策路径具有较高烈度，如果强行执行，在当前（大环境低迷、本地无对应坑位）的约束下，世界线更容易向高风险坍缩。`
      risk = '高风险警告：硬碰硬可能导致空窗期无限拉长。'
      newPaths = [
        {
          type: "baseline",
          color: "info",
          nodes: [
            {time: "T + 2个月", desc: "坚持高薪诉求，连续数十面被挂", triggers: ["未妥协底线"]},
            {time: "T + 6个月", desc: "焦虑巅峰，开始怀疑自身技术能力", triggers: ["零offer"]}
          ]
        },
        {
          type: "worst_case",
          color: "danger",
          nodes: [
            {time: "T + 1年", desc: "彻底断档，技术栈更新停滞", triggers: ["脱离开发环境过久"]},
            {time: "T + 2年", desc: "无奈转行，彻底离开IT业", triggers: ["接受其他行业保底"]}
          ]
        }
      ]
    }

    return [200, {
      code: 200,
      data: {
        new_paths: newPaths,
        logic_explanation: explanation,
        risk_warning: risk
      }
    }]
  })

  // Cycle 5: Worldline Context Injection
  mock.onPut(/\/cases\/case_.*\/context/).reply(() => {
    return [200, {
      code: 200,
      message: '个人语境已注入成功'
    }]
  })

  // Cycle 5: Worldline Data Fetching
  mock.onGet(/\/cases\/case_.*\/worldline/).reply(() => {
    return [200, {
      code: 200,
      data: {
        timeline: ["T + 6个月", "T + 1年", "T + 3年"],
        paths: [
          {
            type: "baseline",
            color: "info",
            nodes: [
              {time: "T + 6个月", desc: "耗尽积蓄，仍未获得满意的开发岗Offer", triggers: ["未主动降薪", "未改变求职地域"]},
              {time: "T + 1年", desc: "开始妥协，进入潍坊某传统制造厂IT部", triggers: ["资金链断裂"]}
            ]
          },
          {
            type: "best_case",
            color: "success",
            nodes: [
              {time: "T + 6个月", desc: "通过低薪外包入行，积累了第一套成熟的微服务实施经验", triggers: ["接受首年薪资折损(仅6-8k)"]},
              {time: "T + 1年", desc: "跳板成功，跳槽至本地数字农业核心企业", triggers: ["沉淀了完整的项目架构经验"]}
            ]
          },
          {
            type: "worst_case",
            color: "danger",
            nodes: [
              {time: "T + 6个月", desc: "持续空窗，技术栈生疏，产生求职焦虑", triggers: ["拒绝所有低于预期的外包和传统厂"]},
              {time: "T + 3年", desc: "彻底转行退出IT业", triggers: ["脱离IT圈子过久"]}
            ]
          }
        ]
      }
    }]
  })

  // Cycle 6: Whitepaper Generation
  mock.onGet(/\/cases\/case_.*\/whitepaper/).reply(() => {
    return [200, {
      code: 200,
      data: {
        main_conflict: "当前脱产备考导致的‘应届生身份流失’与‘潍坊本地偏好即插即用熟练工’之间的结构性矛盾。",
        critical_warnings: [
          "脱产期限若超过6个月，简历被初筛淘汰的概率将呈指数级上升。"
        ],
        mvp_actions: [
          {
            id: "act_1",
            title: "测试水温：盲投3份本地最差的外包岗位",
            objective: "验证本地HR对‘三年专科空窗期’的真实压价底线，而不是继续在家闭门造车。",
            cost: "只需2天时间试错",
            status: "pending"
          },
          {
            id: "act_2",
            title: "更新个人语境：预设下底线薪水",
            objective: "明确‘接受降薪先入行’的决心点，防止焦虑蔓延。",
            cost: "内心博弈1天",
            status: "pending"
          }
        ],
        unknowns: [
          "潍坊本地几家头部制造企业的内部IT是否会在Q3释放校招/社招补录名额？（建议实地打听或托人脉摸排）"
        ]
      }
    }]
  })

  // Cycle 6: Whitepaper Feedback
  mock.onPost(/\/cases\/case_.*\/feedbacks/).reply(() => {
    return [200, {
      code: 200,
      message: '反馈已记录'
    }]
  })

  // Phase 9: Historical Cases
  mock.onGet('/cases/history').reply(() => {
    return [200, {
      code: 200,
      data: [
        {
          id: 'case_101',
          title: '三年大专前端回三线老家的求职突围',
          status: 'WHITE_PAPER',
          created_at: '2026-03-01T10:00:00Z',
          tags: ['前端', '降薪', '三线城市']
        },
        {
          id: 'case_205',
          title: '35岁互联网裁员后的海外远程接单尝试',
          status: 'WORLDLINE_EVOLUTION',
          created_at: '2026-03-05T14:30:00Z',
          tags: ['35岁危机', 'Web3远程', '接单']
        },
        {
          id: 'case_334',
          title: '考公失利两年的脱产开发如何恢复技术体能',
          status: 'FACT_AUDIT',
          created_at: '2026-03-09T09:15:00Z',
          tags: ['考公空窗', '简历美化']
        }
      ]
    }]
  })
}
