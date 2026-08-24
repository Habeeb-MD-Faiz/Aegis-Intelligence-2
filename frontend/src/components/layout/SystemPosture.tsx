/**
 * The system's real security posture, read from `GET /config`.
 *
 * Mission Control used to open with a hardcoded "System Status: Optimal".
 * That is exactly the claim invariant #7 exists to prevent: it read as a
 * guarantee while saying nothing about whether the control plane was actually
 * locked, whether the ledger was actually anchored, or whether the guard was
 * configured to fail open. It said "Optimal" whether or not the backend was
 * even reachable.
 *
 * Every signal here comes from the backend describing itself. An open plane is
 * reported as open — that is the deliberate posture for the public demo, not a
 * fault — and a guard configured to fail open is reported as a failure,
 * because it is one.
 */

import { Icon } from '@/components/icons/Icon'
import { useSystemConfig } from '@/hooks/useSystemConfig'
import type { SystemConfig } from '@/services/systemService'

type Tone = 'good' | 'watch' | 'bad' | 'idle'

const toneClasses: Record<Tone, string> = {
  good: 'text-success',
  watch: 'text-warning',
  bad: 'text-danger',
  idle: 'text-ink-faint',
}

interface Signal {
  label: string
  value: string
  tone: Tone
  detail: string
}

function signals(config: SystemConfig): Signal[] {
  return [
    {
      label: 'Control plane',
      value: config.controlPlaneLocked ? 'Locked' : 'Open',
      tone: config.controlPlaneLocked ? 'good' : 'watch',
      detail: config.controlPlaneLocked
        ? 'Policy changes require an operator credential.'
        : 'No AEGIS_OPERATOR_TOKEN set — anyone who can reach the API can change policy. Deliberate for the public demo.',
    },
    {
      label: 'Data plane',
      value: config.dataPlaneLocked ? 'Locked' : 'Open',
      tone: config.dataPlaneLocked ? 'good' : 'watch',
      detail: config.dataPlaneLocked
        ? 'Spending requires an agent credential.'
        : 'No AEGIS_AGENT_TOKEN set — any caller can submit a spend intent. Policy still evaluates every one.',
    },
    {
      label: 'Guard',
      value: config.guardFailOpen ? 'Fails OPEN' : 'Fails closed',
      tone: config.guardFailOpen ? 'bad' : 'good',
      detail: config.guardFailOpen
        ? 'AEGIS_GUARD_FAIL_OPEN is set. A policy-engine error will RELEASE the payment. This must not be on.'
        : 'A policy-engine error refuses the payment.',
    },
    {
      label: 'Anchoring',
      value: config.anchoringEnabled ? config.chainName : 'Not configured',
      tone: config.anchoringEnabled ? 'good' : 'idle',
      detail: config.anchoringEnabled
        ? `Ledger digests are anchored to ${config.chainName}.`
        : 'The ledger is hash-linked and verified locally. Nothing is written on chain.',
    },
    {
      label: 'Policy AI',
      value: config.llmEnabled ? 'Enabled' : 'Off',
      tone: 'idle',
      detail: config.llmEnabled
        ? 'An LLM proposes policy amendments. It never decides whether to release money.'
        : 'No GROQ_API_KEY set. Suggestions are unavailable; enforcement is unaffected — it never used an LLM.',
    },
  ]
}

export function SystemPosture() {
  const { config: data, loading, error } = useSystemConfig()

  if (loading) {
    return (
      <div className="mb-6 flex items-center gap-2 text-label uppercase tracking-widest text-ink-faint">
        <span className="h-1.5 w-1.5 rounded-full bg-ink-faint" />
        Reading system posture…
      </div>
    )
  }

  // Say nothing rather than something reassuring. A dashboard that cannot
  // reach the backend knows less about the system than one that can.
  if (error || !data) {
    return (
      <div
        className="mb-6 flex items-center gap-2 text-label uppercase tracking-widest text-warning"
        title={error ?? 'No response from /config'}
      >
        <Icon name="help" size={14} className="shrink-0" />
        System posture unknown — backend unreachable
      </div>
    )
  }

  const items = signals(data)
  const failingOpen = data.guardFailOpen

  return (
    <div className="mb-6">
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <span className="text-label uppercase tracking-widest text-ink-faint">
          System posture
        </span>

        {items.map((signal) => (
          <span
            key={signal.label}
            title={signal.detail}
            className="flex cursor-help items-center gap-1.5 text-label uppercase tracking-widest"
          >
            <span
              className={`h-1.5 w-1.5 rounded-full bg-current ${toneClasses[signal.tone]} ${
                signal.tone === 'bad' ? 'animate-pulse-glow' : ''
              }`}
            />
            <span className="text-ink-faint">{signal.label}</span>
            <span className={toneClasses[signal.tone]}>{signal.value}</span>
          </span>
        ))}
      </div>

      {failingOpen && (
        <p className="mt-2 flex items-center gap-1.5 text-body-sm text-danger">
          <Icon name="warning" size={16} className="shrink-0" filled />
          The guard is configured to fail open — a policy-engine error will
          release the payment rather than refuse it.
        </p>
      )}
    </div>
  )
}
