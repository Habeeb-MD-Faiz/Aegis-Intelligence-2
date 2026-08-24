import { Icon } from '@/components/icons/Icon'
import { useSystemConfig } from '@/hooks/useSystemConfig'

interface TopBarProps {
  title: string
  breadcrumb?: string
}

export function TopBar({ title, breadcrumb }: TopBarProps) {
  return (
    <header className="sticky top-0 z-20 flex h-16 shrink-0 items-center justify-between border-b border-border bg-bg/90 px-6 backdrop-blur-md">
      <div>
        {breadcrumb && <p className="text-label uppercase tracking-widest text-ink-faint">{breadcrumb}</p>}
        <h1 className="text-h3 font-semibold text-ink">{title}</h1>
      </div>
      <div className="flex items-center gap-2">
        <div className="hidden items-center gap-2 rounded-md border border-border bg-surface-low px-3 py-1.5 text-body-sm text-ink-faint sm:flex">
          <Icon name="search" size={16} />
          <span>Search AEGIS…</span>
          <kbd className="ml-4 rounded border border-border-strong bg-surface px-1.5 py-0.5 font-mono text-[10px] text-ink-muted">
            ⌘K
          </kbd>
        </div>
        <button className="focus-ring relative rounded-md p-2 text-ink-muted transition-colors hover:bg-surface-high hover:text-ink" aria-label="Notifications">
          <Icon name="notifications" size={20} />
          <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-accent" />
        </button>
        <GuardStatus />
      </div>
    </header>
  )
}


/**
 * This badge used to be a hardcoded green "System Optimal" on every screen. It
 * said so whether or not the backend was reachable, and whether or not the
 * guard was configured to fail open — the one setting that would let a
 * policy-engine error release a payment. It now reports what the backend says
 * about itself. The full breakdown is on Mission Control.
 */
function GuardStatus() {
  const { config, loading, error } = useSystemConfig()

  if (loading) {
    return (
      <div className="flex items-center gap-1.5 rounded-md border border-border bg-surface-low px-2.5 py-1.5 text-caption font-medium text-ink-faint">
        <span className="h-1.5 w-1.5 rounded-full bg-ink-faint" />
        Checking…
      </div>
    )
  }

  if (error || !config) {
    return (
      <div
        title={error ?? 'No response from /config'}
        className="flex cursor-help items-center gap-1.5 rounded-md border border-warning/30 bg-warning-container px-2.5 py-1.5 text-caption font-medium text-warning"
      >
        <Icon name="help" size={14} />
        Backend unreachable
      </div>
    )
  }

  if (config.guardFailOpen) {
    return (
      <div
        title="AEGIS_GUARD_FAIL_OPEN is set. A policy-engine error will release the payment instead of refusing it."
        className="flex cursor-help items-center gap-1.5 rounded-md border border-danger/30 bg-danger-container px-2.5 py-1.5 text-caption font-medium text-danger"
      >
        <span className="h-1.5 w-1.5 animate-pulse-glow rounded-full bg-danger" />
        Guard fails open
      </div>
    )
  }

  const planes =
    config.controlPlaneLocked && config.dataPlaneLocked
      ? 'Both planes require a credential.'
      : config.controlPlaneLocked
        ? 'Control plane locked; data plane open.'
        : 'Both planes open — deliberate for the public demo. Policy still evaluates every request.'

  return (
    <div
      title={`Every payment goes through the guard, and a policy-engine error refuses it. ${planes}`}
      className="flex cursor-help items-center gap-1.5 rounded-md border border-success/30 bg-success-container px-2.5 py-1.5 text-caption font-medium text-success"
    >
      <span className="h-1.5 w-1.5 animate-pulse-glow rounded-full bg-success" />
      Guard enforcing
    </div>
  )
}
