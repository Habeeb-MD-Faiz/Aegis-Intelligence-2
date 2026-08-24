import { useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardHeader } from '@/components/ui/Card'
import { Badge, riskTone } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Icon } from '@/components/icons/Icon'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Textarea } from '@/components/ui/Textarea'
import { Drawer } from '@/components/ui/Drawer'
import { SkeletonLines } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/ErrorState'
import { EmptyState } from '@/components/ui/EmptyState'
import { useAsync } from '@/hooks/useAsync'
import { useToast } from '@/contexts/ToastContext'
import type { Policy, PolicyRule, RiskLevel } from '@/types'
import {
  fetchPolicies,
  savePolicy,
  fetchPolicySuggestions,
  applyPolicySuggestion,
  type PolicySuggestion,
} from '@/services/policyService'

function emptyPolicy(): Policy {
  return {
    id: `POL-${Math.floor(100 + Math.random() * 900)}`,
    name: '',
    description: '',
    status: 'draft',
    severity: 'medium',
    rules: [{ id: 'r1', field: 'transaction.amount', operator: '>', value: '' }],
    updatedAt: 'just now',
    appliesTo: [],
  }
}

export function PolicyBuilderPage() {
  const { data, loading, error, refetch, setData } = useAsync(fetchPolicies)
  const { showToast } = useToast()
  const suggestionsState = useAsync(fetchPolicySuggestions)
  const [applyingSuggestion, setApplyingSuggestion] = useState<number | null>(null)
  const [editing, setEditing] = useState<Policy | null>(null)

  function updateRule(index: number, patch: Partial<PolicyRule>) {
    if (!editing) return
    const rules = editing.rules.map((r, i) => (i === index ? { ...r, ...patch } : r))
    setEditing({ ...editing, rules })
  }

  function addRule() {
    if (!editing) return
    setEditing({
      ...editing,
      rules: [...editing.rules, { id: `r${editing.rules.length + 1}`, field: '', operator: '=', value: '' }],
    })
  }

  function removeRule(index: number) {
    if (!editing) return
    setEditing({ ...editing, rules: editing.rules.filter((_, i) => i !== index) })
  }

  async function handleApplySuggestion(
    suggestion: PolicySuggestion,
    index: number
  ) {
    try {
      setApplyingSuggestion(index)

      const result = await applyPolicySuggestion(suggestion)

      if (!result.success) {
        throw new Error(result.message || 'Failed to apply policy')
      }

      showToast({
        title: 'Policy applied',
        description: result.message,
        status: 'success',
      })

      // Refresh actual policies
      await refetch()

      // Refresh AI suggestions
      await suggestionsState.refetch()

    } catch (error) {
      showToast({
        title: 'Failed to apply policy',
        description:
          error instanceof Error
            ? error.message
            : 'Something went wrong.',
        status: 'danger',
      })
    } finally {
      setApplyingSuggestion(null)
    }
  }

  async function handleSave() {
    if (!editing) return
    const saved = await savePolicy(editing)
    const exists = (data ?? []).some((p) => p.id === saved.id)
    setData(exists ? (data ?? []).map((p) => (p.id === saved.id ? saved : p)) : [saved, ...(data ?? [])])
    setEditing(null)
    showToast({ title: 'Policy saved', description: `${saved.name || saved.id} has been published.`, status: 'success' })
  }

  return (
    <AppShell title="Policy Builder" breadcrumb="Govern">
      <PageHeader
        title="Policy Builder"
        description="Codify the rules autonomous agents must obey before any transaction, access request, or decision executes."
        action={
          <Button icon="add" onClick={() => setEditing(emptyPolicy())}>
            New Policy
          </Button>
        }
      />

      {/* ========================================================= */}
      {/* AI POLICY ADVISOR */}
      {/* ========================================================= */}

      <Card className="mb-6">

        <CardHeader
          title="AI Policy Advisor"
          subtitle="Generative AI analyzes recent decisions and recommends governance improvements."
        />

        {suggestionsState.loading ? (

          <div className="mt-4 flex flex-col gap-3">
            <SkeletonLines count={4} />
            <SkeletonLines count={4} />
          </div>

        ) : suggestionsState.error ? (

          <div className="mt-4">
            <ErrorState
              message={suggestionsState.error}
              onRetry={suggestionsState.refetch}
            />
          </div>

        ) : (suggestionsState.data?.suggestions ?? []).length === 0 ? (

          <div className="mt-4 rounded-md border border-border-subtle bg-surface-low p-5">

            <div className="flex items-start gap-3">

              <Icon
                name="auto_awesome"
                size={20}
                className="text-accent"
              />

              <div>

                <p className="text-body-sm font-medium text-ink">
                  No policy changes recommended
                </p>

                <p className="mt-1 text-body-sm text-ink-muted">
                  AEGIS does not currently have enough evidence
                  to recommend a governance change.
                </p>

              </div>

            </div>

          </div>

        ) : (

          <div className="mt-4 flex flex-col gap-4">

            {(suggestionsState.data?.suggestions ?? []).map(
              (suggestion, index) => (

                <div
                  key={`${suggestion.title}-${index}`}
                  className="rounded-lg border border-border-subtle bg-surface-low p-5"
                >

                  {/* HEADER */}

                  <div className="flex items-start justify-between gap-4">

                    <div>

                      <div className="flex flex-wrap items-center gap-2">

                        <Badge tone="neutral">
                          AI Suggestion
                        </Badge>

                        <Badge
                          tone={
                            suggestion.recommendation === 'tighten'
                              ? 'warning'
                              : suggestion.recommendation === 'relax'
                                ? 'success'
                                : 'neutral'
                          }
                        >
                          {suggestion.recommendation}
                        </Badge>

                      </div>

                      <h3 className="mt-3 text-h3 text-ink">
                        {suggestion.title}
                      </h3>

                    </div>

                    <div className="shrink-0 text-right">

                      <p className="text-caption text-ink-faint">
                        CONFIDENCE
                      </p>

                      <p className="mt-1 font-mono text-h3 text-ink">
                        {suggestion.confidence}%
                      </p>

                    </div>

                  </div>


                  {/* POLICY CHANGE */}

                  {(suggestion.current_value ||
                    suggestion.suggested_value) && (

                    <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">

                      <div className="rounded-md border border-border-subtle p-4">

                        <p className="text-caption text-ink-faint">
                          CURRENT
                        </p>

                        <p className="mt-2 font-mono text-body-sm text-ink">
                          {suggestion.current_value ?? 'Not configured'}
                        </p>

                      </div>

                      <div className="rounded-md border border-border-subtle p-4">

                        <p className="text-caption text-ink-faint">
                          SUGGESTED
                        </p>

                        <p className="mt-2 font-mono text-body-sm text-ink">
                          {suggestion.suggested_value ?? '—'}
                        </p>

                      </div>

                    </div>
                  )}


                  {/* REASON */}

                  <div className="mt-4">

                    <p className="text-caption text-ink-faint">
                      AI ANALYSIS
                    </p>

                    <p className="mt-1 text-body-sm leading-relaxed text-ink-muted">
                      {suggestion.reason}
                    </p>

                  </div>


                  {/* EVIDENCE */}

                  <div className="mt-4 flex flex-wrap gap-4 text-caption text-ink-faint">

                    <span>
                      Evidence:{' '}
                      <strong className="text-ink">
                        {suggestion.evidence_count}
                      </strong>{' '}
                      request(s)
                    </span>

                    {suggestion.category && (
                      <span>
                        Category:{' '}
                        <strong className="text-ink">
                          {suggestion.category}
                        </strong>
                      </span>
                    )}

                    <span>
                      Type:{' '}
                      <strong className="text-ink">
                        {suggestion.suggestion_type.replace(/_/g, ' ')}
                      </strong>
                    </span>

                  </div>


                  {/* ACTIONS */}

                  <div className="mt-5 flex justify-end gap-2 border-t border-border pt-4">

                    <Button
                      variant="outline"
                      onClick={() => {
                        showToast({
                          title: 'Suggestion dismissed',
                          description: suggestion.title,
                          status: 'info',
                        })
                      }}
                    >
                      Dismiss
                    </Button>

                    <Button
                      disabled={applyingSuggestion === index}
                      onClick={() =>
                        handleApplySuggestion(
                          suggestion,
                          index
                        )
                      }
                    >
                      {applyingSuggestion === index
                        ? 'Applying...'
                        : 'Apply to Guardrails'}
                    </Button>

                  </div>

                </div>

              )
            )}

          </div>

        )}

      </Card>

      {error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : loading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <SkeletonLines count={3} />
            </Card>
          ))}
        </div>
      ) : (data ?? []).length === 0 ? (
        <EmptyState icon="gavel" title="No policies yet" description="Create your first governance policy to get started." />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {(data ?? []).map((policy) => (
            <Card key={policy.id} interactive onClick={() => setEditing(policy)}>
              <CardHeader
                title={policy.name}
                subtitle={<span className="font-mono">{policy.id}</span>}
                action={<Badge tone={policy.status === 'active' ? 'success' : 'neutral'}>{policy.status}</Badge>}
              />
              <p className="mb-4 text-body-sm text-ink-muted">{policy.description}</p>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Badge tone={riskTone[policy.severity]}>{policy.severity} severity</Badge>
                <span className="text-caption text-ink-faint">{policy.rules.length} rule(s) · updated {policy.updatedAt}</span>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Drawer
        open={!!editing}
        onClose={() => setEditing(null)}
        title={editing?.name ? `Edit ${editing.name}` : 'New Policy'}
        footer={
          <>
            <Button variant="outline" onClick={() => setEditing(null)}>
              Cancel
            </Button>
            <Button icon="save" onClick={handleSave}>
              Save Policy
            </Button>
          </>
        }
      >
        {editing && (
          <div className="flex flex-col gap-5">
            <Input label="Policy name" value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} placeholder="e.g. Spend Ceiling" />
            <Textarea
              label="Description"
              value={editing.description}
              onChange={(e) => setEditing({ ...editing, description: e.target.value })}
              placeholder="What does this policy prevent or require?"
            />
            <div className="grid grid-cols-2 gap-4">
              <Select
                label="Severity"
                value={editing.severity}
                onChange={(e) => setEditing({ ...editing, severity: e.target.value as RiskLevel })}
                options={[
                  { label: 'Low', value: 'low' },
                  { label: 'Medium', value: 'medium' },
                  { label: 'High', value: 'high' },
                  { label: 'Critical', value: 'critical' },
                ]}
              />
              <Select
                label="Status"
                value={editing.status}
                onChange={(e) => setEditing({ ...editing, status: e.target.value as Policy['status'] })}
                options={[
                  { label: 'Draft', value: 'draft' },
                  { label: 'Active', value: 'active' },
                  { label: 'Archived', value: 'archived' },
                ]}
              />
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <p className="text-label uppercase tracking-widest text-ink-muted">Rules</p>
                <Button size="sm" variant="ghost" icon="add" onClick={addRule}>
                  Add rule
                </Button>
              </div>
              <div className="flex flex-col gap-2">
                {editing.rules.map((rule, i) => (
                  <div key={rule.id} className="grid grid-cols-[1fr_80px_1fr_32px] gap-2">
                    <Input value={rule.field} onChange={(e) => updateRule(i, { field: e.target.value })} placeholder="field" />
                    <Select
                      value={rule.operator}
                      onChange={(e) => updateRule(i, { operator: e.target.value })}
                      options={[
                        { label: '=', value: '=' },
                        { label: '!=', value: '!=' },
                        { label: '>', value: '>' },
                        { label: '<', value: '<' },
                      ]}
                    />
                    <Input value={rule.value} onChange={(e) => updateRule(i, { value: e.target.value })} placeholder="value" />
                    <button
                      onClick={() => removeRule(i)}
                      className="focus-ring flex items-center justify-center rounded-md text-ink-faint hover:bg-surface-high hover:text-danger"
                      aria-label="Remove rule"
                    >
                      <Icon name="delete" size={18} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </Drawer>
    </AppShell>
  )
}
