import type { Guardrail } from '@/types'
import { requestJson } from './api'
import { operatorHeaders } from '@/config'

export function fetchGuardrails(): Promise<Guardrail[]> {
  return requestJson<Guardrail[]>('/guardrails')
}

export function toggleGuardrail(
  id: string,
  enabled: boolean
): Promise<Guardrail> {
  return requestJson<Guardrail>(`/guardrails/${id}/toggle`, {
    method: 'POST',

    // Control plane: arming and disarming guardrails needs an operator
    // credential. Agents are rejected here by construction — requestJson
    // reports the 401/403 as a credential problem rather than a server fault.
    headers: operatorHeaders(),

    body: JSON.stringify({
      enabled,
    }),
  })
}