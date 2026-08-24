import { useAsync } from '@/hooks/useAsync'
import { loadSystemConfig, type SystemConfig } from '@/services/systemService'

/**
 * The backend's self-reported posture, shared between the top bar and the
 * Mission Control strip. Both call this; only one HTTP request is made.
 */
export function useSystemConfig() {
  const { data, loading, error } = useAsync<SystemConfig>(loadSystemConfig)

  return { config: data, loading, error }
}
