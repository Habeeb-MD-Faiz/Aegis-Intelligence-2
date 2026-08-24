import type { ReactNode } from 'react'
import type { RiskLevel, Status } from '@/types'

type Tone = Status | 'accent'

interface BadgeProps {
  children: ReactNode
  tone?: Tone
  dot?: boolean
  className?: string
}

const toneClasses: Record<Tone, string> = {
  success: 'bg-success-container text-success border-success/30',
  warning: 'bg-warning-container text-warning border-warning/30',
  danger: 'bg-danger-container text-danger border-danger/30',
  info: 'bg-info-container text-info border-info/30',
  neutral: 'bg-surface-high text-ink-muted border-border-strong',
  accent: 'bg-accent-container text-accent border-accent/30',
}

export function Badge({ children, tone = 'neutral', dot = false, className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-label uppercase tracking-wide ${toneClasses[tone]} ${className}`}
    >
      {dot && <span className={`h-1.5 w-1.5 rounded-full bg-current`} />}
      {children}
    </span>
  )
}

// Exported: the design system owns risk -> colour. PolicyBuilderPage kept a
// byte-identical private copy, which is how two screens end up disagreeing
// about what "high" looks like after someone tunes one of them.
export const riskTone: Record<RiskLevel, Tone> = {
  low: 'success',
  medium: 'warning',
  high: 'danger',
  critical: 'danger',
}

export function RiskBadge({ level }: { level: RiskLevel }) {
  return (
    <Badge tone={riskTone[level]} dot>
      {level}
    </Badge>
  )
}

const statusStyles: Record<string, Tone> = {
  running: 'success',
  active: 'success',
  confirmed: 'success',
  approved: 'success',
  settled: 'success',
  resolved: 'success',
  healthy: 'success',
  success: 'success',
  idle: 'neutral',
  draft: 'neutral',
  neutral: 'neutral',
  paused: 'warning',
  pending: 'warning',
  processing: 'warning',
  investigating: 'warning',
  degraded: 'warning',
  warning: 'warning',
  error: 'danger',
  failed: 'danger',
  rejected: 'danger',
  blocked: 'danger',
  offline: 'danger',
  open: 'danger',
  danger: 'danger',
  failure: 'danger',
  contained: 'info',
  info: 'info',
  archived: 'neutral',
}

export function StatusBadge({ status }: { status: string }) {
  const tone = statusStyles[status.toLowerCase()] ?? 'neutral'
  return (
    <Badge tone={tone} dot>
      {status}
    </Badge>
  )
}
