/**
 * Frontend configuration.
 *
 * The backend URL used to be a hardcoded production string duplicated across
 * six service files, so running against a local backend meant editing source
 * in six places (and remembering to revert before committing). It now comes
 * from one env var with the deployed backend as the fallback, so `npm run dev`
 * against localhost is a one-line .env change.
 */

export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? 'https://aegis-backend-lx1z.onrender.com'

/**
 * Credential the frontend presents on control-plane routes (policy edits,
 * guardrail toggles). Agents never receive this.
 *
 * Left empty in the public demo, where the backend runs with its control plane
 * open. Set VITE_OPERATOR_TOKEN alongside the backend's AEGIS_OPERATOR_TOKEN
 * to lock policy changes to operators.
 */
export const OPERATOR_TOKEN: string = import.meta.env.VITE_OPERATOR_TOKEN ?? ''

/**
 * Several screens are still backed by static fixtures rather than live data
 * (see MOCK_BACKED_ROUTES in constants/nav.ts). Set VITE_HIDE_MOCK_SCREENS=true
 * to hide them — worth doing before a demo, so nobody clicks into a screen
 * whose numbers have no relationship to the transactions they just watched.
 */
export const HIDE_MOCK_SCREENS: boolean =
  String(import.meta.env.VITE_HIDE_MOCK_SCREENS ?? '').toLowerCase() === 'true'

/**
 * Headers for control-plane requests.
 */
export function operatorHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  if (OPERATOR_TOKEN) {
    headers.Authorization = `Bearer ${OPERATOR_TOKEN}`
  }

  return headers
}

/**
 * What the backend reports about its own security posture, so the UI can show
 * the real state instead of implying guarantees that are not configured.
 */
export interface SystemConfig {
  controlPlaneLocked: boolean
  dataPlaneLocked: boolean
  anchoringEnabled: boolean
  chainName: string
  llmEnabled: boolean
  guardFailOpen: boolean
}

export async function fetchSystemConfig(): Promise<SystemConfig> {
  const response = await fetch(`${API_BASE_URL}/config`)

  if (!response.ok) {
    throw new Error('Failed to fetch system configuration')
  }

  return response.json()
}
