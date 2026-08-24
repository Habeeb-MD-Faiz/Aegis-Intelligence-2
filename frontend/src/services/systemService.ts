/**
 * What the backend reports about its own security posture.
 *
 * `GET /config` is how the deployment answers "are the planes actually locked,
 * is anchoring configured, is the guard failing open?" without the UI implying
 * guarantees nobody has configured.
 *
 * NOTE: nothing renders this yet. It lived in `config.ts` — where it was also
 * the last raw `fetch` in the codebase — and is parked here so the posture is
 * one import away when a screen wants to show it.
 */

import { requestJson } from './api'

export interface SystemConfig {
  controlPlaneLocked: boolean
  dataPlaneLocked: boolean
  anchoringEnabled: boolean
  chainName: string
  llmEnabled: boolean
  guardFailOpen: boolean
}

export function fetchSystemConfig(): Promise<SystemConfig> {
  return requestJson<SystemConfig>('/config')
}
