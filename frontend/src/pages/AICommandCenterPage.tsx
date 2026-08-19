import { useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card } from '@/components/ui/Card'
import { StatCard } from '@/components/ui/StatCard'
import { StatusBadge, RiskBadge } from '@/components/ui/Badge'
import { Table, type Column } from '@/components/ui/Table'
import type { PaymentRequest } from '@/types'
import { Input } from '@/components/ui/Input'
import { SkeletonCard } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/ErrorState'
import { useAsync } from '@/hooks/useAsync'
import {
  fetchPaymentRequests,
  fetchDashboardStats,
} from '@/services/paymentsService'


export function AICommandCenterPage() {
  const requestsState = useAsync(fetchPaymentRequests)
  const dashboardState = useAsync(fetchDashboardStats)
  const [query, setQuery] = useState('')

  const filtered = (requestsState.data ?? []).filter(
    (r) =>
      r.vendor.toLowerCase().includes(query.toLowerCase()) ||
      r.category.toLowerCase().includes(query.toLowerCase()),
  )

  const columns: Column<PaymentRequest>[] = [
    {
      header: 'Task',
      key: 'vendor',
      render: (r) => (
        <div>
          <p className="font-medium text-ink">{r.vendor}</p>
          <p className="font-mono text-caption text-ink-faint">
            {r.id}
          </p>
        </div>
      ),
    },
    {
      header: 'Provider',
      key: 'provider',
      render: (r) => (
        <span className="text-body-sm text-ink">
          {r.provider}
        </span>
      ),
    },
    {
      header: 'Decision By',
      key: 'decisionBy',
      render: (r) => (
        <span className="text-body-sm text-ink-muted">
          {r.status === 'pending'
            ? 'Waiting for User'
            : r.decisionBy}
        </span>
      ),
    },
    {
      header: 'Status',
      key: 'status',
      render: (r) => <StatusBadge status={r.status} />,
    },
    {
      header: 'Risk',
      key: 'riskLevel',
      render: (r) => <RiskBadge level={r.riskLevel} />,
    },
    {
      header: 'Amount',
      key: 'amount',
      align: 'right',
      render: (r) => (
        <span className="font-mono font-medium">
          ${r.amount.toLocaleString()}
        </span>
      ),
    },
  ]

  return (
    <AppShell title="AI Command Center" breadcrumb="Operate">
      <PageHeader
        title="AI Command Center"
        description="Fleet-wide visibility and control across every autonomous agent operating under AEGIS governance."
      />

      {dashboardState.loading ? (
        <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : (
        <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard
            label="Total Requests"
            value={String(dashboardState.data?.totalRequests ?? 0)}
            icon="description"
          />

          <StatCard
            label="Pending Review"
            value={String(dashboardState.data?.pending ?? 0)}
            delta="awaiting user"
            deltaDirection="flat"
            icon="pending_actions"
          />

          <StatCard
            label="Approved"
            value={String(dashboardState.data?.approved ?? 0)}
            delta="all decisions"
            deltaDirection="up"
            icon="verified_user"
          />

          <StatCard
            label="Today's Spend"
            value={`$${(dashboardState.data?.todaySpend ?? 0).toLocaleString()}`}
            icon="account_balance_wallet"
          />
        </div>
      )}
      <Card padded={false}>
        <div className="flex items-center justify-between gap-4 border-b border-border p-4">
          <Input
            icon="search"
            placeholder="Search by task or category…" value={query} onChange={(e) => setQuery(e.target.value)} className="max-w-xs" />
        </div>
        <div className="p-4">
          {requestsState.error ? (
            <ErrorState
              message={requestsState.error}
              onRetry={requestsState.refetch}
            />
          ) : requestsState.loading ? (
            <div className="flex flex-col gap-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="skeleton h-12 w-full" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <p className="p-6 text-center text-body-sm text-ink-muted">
              No requests found.
            </p>
          ) : (
            <Table
              columns={columns}
              rows={filtered}
              rowKey={(r) => r.id}
            />
          )}
        </div>
      </Card>
    </AppShell>
  )
}
