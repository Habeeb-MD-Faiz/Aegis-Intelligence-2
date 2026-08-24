/**
 * What the backend reports about its own security posture.
 *
 * `GET /config` is how the deployment answers "are the planes actually locked,
 * is anchoring configured, is the guard failing open?" — so the UI can show
 * the real state instead of implying guarantees nobody has configured.
 *
 * Two components read this: the posture strip on Mission Control and the badge
 * in the top bar, which appears on every screen. They share one request via
 * the cache below rather than each firing their own.
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

// Posture is environment-driven and only changes when the backend restarts, so
// one request per page load is enough. The promise itself is cached, which also
// collapses the two mounts that happen on the same tick into a single call.
// A failure is not cached — a backend that was down at load should be
// reachable again on the next attempt.
let inFlight: Promise<SystemConfig> | null = null

export function loadSystemConfig(): Promise<SystemConfig> {
  if (!inFlight) {
    inFlight = fetchSystemConfig().catch((error) => {
      inFlight = null
      throw error
    })
  }

  return inFlight
}
