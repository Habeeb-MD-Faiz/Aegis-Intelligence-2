import { ApiError } from './api'
import { API_BASE_URL } from '@/config'

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

export async function executeTask(
  message: string
): Promise<ExecuteTaskResponse> {
  const response = await fetch(`${API_BASE_URL}/execute-task`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
    }),
  })

  if (!response.ok) {
    throw new ApiError(`Backend request failed (${response.status})`)
  }

  return response.json()
}