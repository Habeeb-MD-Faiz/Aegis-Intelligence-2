import { useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card } from '@/components/ui/Card'
import { RiskBadge, StatusBadge } from '@/components/ui/Badge'
import { Table, type Column } from '@/components/ui/Table'
import { Tabs } from '@/components/ui/Tabs'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { ErrorState } from '@/components/ui/ErrorState'
import { EmptyState } from '@/components/ui/EmptyState'
import { useAsync } from '@/hooks/useAsync'
import { fetchPaymentRequests, decidePaymentRequest } from '@/services/paymentsService'
import { useToast } from '@/contexts/ToastContext'
import type { PaymentRequest } from '@/types'

const tabs = [
  { label: 'All', value: 'all' },
  { label: 'Pending', value: 'pending' },
  { label: 'Approved', value: 'approved' },
  { label: 'Rejected', value: 'rejected' },
]

export function PaymentRequestsPage() {
  const { data, loading, error, refetch, setData } = useAsync(fetchPaymentRequests)
  const { showToast } = useToast()
  const [tab, setTab] = useState('all')
  const [selected, setSelected] = useState<PaymentRequest | null>(null)

  const paymentRows = [...(data ?? [])]

  const filtered = paymentRows.filter((p) => {
    if (p.decision !== 'human_review') {
      return false
    }
    if (tab === 'all') {
      return true
    }
    return p.status === tab
  })

  async function decide(id: string, decision: 'approved' | 'rejected') {
    const updated = await decidePaymentRequest(id, decision)
    setData((data ?? []).map((p) => (p.id === id ? updated : p)))
    setSelected(null)
    showToast({
      title: decision === 'approved' ? 'Payment approved' : 'Payment rejected',
      description: `${id} marked as ${decision}.`,
      status: decision === 'approved' ? 'success' : 'danger',
    })
  }

  const columns: Column<PaymentRequest>[] = [
    {
      header: 'Request',
      key: 'vendor',
      render: (p) => (
        <div>
          <p className="font-medium text-ink">{p.vendor}</p>
          <p className="font-mono text-caption text-ink-faint">
            {p.id}
          </p>
        </div>
      ),
    },
    {
      header: 'Agent',
      key: 'agentId',
      render: (p) => (
        <span className="font-mono text-body-sm">
          {p.agentId}
        </span>
      ),
    },
    {
      header: 'Category',
      key: 'category',
    },
    {
      header: 'Risk',
      key: 'riskLevel',
      render: (p) => (
        <RiskBadge level={p.riskLevel} />
      ),
    },
    {
      header: 'Status',
      key: 'status',
      render: (p) => (
        <StatusBadge status={p.status} />
      ),
    },
    {
      header: 'Amount',
      key: 'amount',
      align: 'right',
      render: (p) => (
        <span className="font-mono font-medium">
          ${p.amount.toLocaleString()}
        </span>
      ),
    },
  ]
  return (
    <AppShell title="Payment Requests" breadcrumb="Payments">
      <PageHeader
        title="Payment Requests"
        description="Human-in-the-loop payment approvals governed by AEGIS guardrails."
      />

      <div className="mb-4">
        <Tabs tabs={tabs} active={tab} onChange={setTab} />
      </div>

      <Card padded={false}>
        <div className="p-4">
          {error ? (
            <ErrorState message={error} onRetry={refetch} />
          ) : loading ? (
            <div className="flex flex-col gap-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="skeleton h-12 w-full" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <EmptyState icon="payments" title="No payment requests" description="Nothing matches this filter right now." />
          ) : (
            <Table columns={columns} rows={filtered} rowKey={(r) => r.id} onRowClick={setSelected} />
          )}
        </div>
      </Card>

      <Modal
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.vendor ?? ''}
        description={selected?.id}
        footer={
          selected?.status === 'pending' ? (
            <>
              <Button variant="outline" onClick={() => selected && decide(selected.id, 'rejected')}>
                Reject
              </Button>
              <Button onClick={() => selected && decide(selected.id, 'approved')}>Approve</Button>
            </>
          ) : (
            <Button variant="secondary" onClick={() => setSelected(null)}>
              Close
            </Button>
          )
        }
      >
        {selected && (
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4 text-body-sm">
              <div>
                <p className="text-caption text-ink-faint">Amount</p>
                <p className="mt-1 font-mono text-h3 text-ink">${selected.amount.toLocaleString()}</p>
              </div>
              <div>
                <p className="text-caption text-ink-faint">Category</p>
                <p className="mt-1 text-ink">{selected.category}</p>
              </div>
              <div>
                <p className="text-caption text-ink-faint">Requesting agent</p>
                <p className="mt-1 font-mono text-ink">{selected.agentId}</p>
              </div>
              <div>
                <p className="text-caption text-ink-faint">Risk level</p>
                <p className="mt-1">
                  <RiskBadge level={selected.riskLevel} />
                </p>
              </div>
            </div>
            <div>
              <p className="text-caption text-ink-faint">Memo</p>
              <p className="mt-1 rounded-md border border-border bg-surface-low p-3 text-body-sm text-ink-muted">
                {selected.memo}
              </p>
            </div>
          </div>
        )}
      </Modal>
    </AppShell>
  )
}
