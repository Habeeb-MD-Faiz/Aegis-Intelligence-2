import { requestJson } from './api'

export interface ExecuteTaskRequest {
  message: string
}

export interface GuardrailCheck {
  policy: string
  passed: boolean
  message: string
}

export interface ExecuteTaskResponse {
  task: string
  provider: string
  api: string
  amount: number
  category: string
  riskLevel: 'low' | 'medium' | 'high' | 'critical'
  decision: 'approved' | 'human_review' | 'blocked'
  reason: string
  checks: GuardrailCheck[]
}

export function executeTask(
  message: string
): Promise<ExecuteTaskResponse> {
  return requestJson<ExecuteTaskResponse>('/execute-task', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
    }),
  })
}