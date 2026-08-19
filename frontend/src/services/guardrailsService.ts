import type { Guardrail } from '@/types'
import { API_BASE_URL, operatorHeaders } from '@/config'

export async function fetchGuardrails(): Promise<Guardrail[]> {
  const response = await fetch(
    `${API_BASE_URL}/guardrails`
  )

  if (!response.ok) {
    throw new Error('Failed to fetch guardrails')
  }

  return response.json()
}

export async function toggleGuardrail(
  id: string,
  enabled: boolean
): Promise<Guardrail> {
  const response = await fetch(
    `${API_BASE_URL}/guardrails/${id}/toggle`,
    {
      method: 'POST',

      // Control plane: arming and disarming guardrails needs an operator
      // credential. Agents are rejected here by construction.
      headers: operatorHeaders(),

      body: JSON.stringify({
        enabled,
      }),
    }
  )

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      throw new Error(
        'Operator credential required to change guardrails.',
      )
    }

    throw new Error('Failed to update guardrail')
  }

  return response.json()
}