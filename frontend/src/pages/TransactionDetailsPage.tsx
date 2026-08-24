import { AppShell } from '@/components/layout/AppShell'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/Badge'
import { Icon } from '@/components/icons/Icon'
import { SkeletonLines } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/ErrorState'

import { useAsync } from '@/hooks/useAsync'

import { fetchTransactions } from '@/services/transactionsService'
import {
  createPaymentRequest,
} from '@/services/paymentsService'
import type { Transaction } from '@/types'


// Both timestamps are optional — the backend sends created_at, older records
// only carry timestamp, and a record may have neither. new Date(undefined)
// renders the string "Invalid Date" straight into the page, so say nothing
// instead.
function formatCreated(transaction: Transaction): string {
  const raw = transaction.created_at ?? transaction.timestamp

  if (!raw) return '—'

  const date = new Date(raw)

  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
}


export function TransactionDetailsPage() {

  const {
    data,
    loading,
    error,
    refetch,
  } = useAsync(fetchTransactions)


  /*
   * Transactions are created automatically by the backend
   * after an approved payment request.
   *
   * This page only displays transaction information.
   */

  const active: Transaction | undefined =
    data?.[0]


  // -------------------------------------------------------------------------
  // ERROR
  // -------------------------------------------------------------------------

  if (error) {

    return (
      <AppShell
        title="Transaction Details"
        breadcrumb="Payments"
      >

        <PageHeader
          title="Transaction Pipeline"
          description="Trace an approved payment request through the AEGIS transaction pipeline."
        />

        <ErrorState
          message={error}
          onRetry={refetch}
        />

      </AppShell>
    )
  }


  // -------------------------------------------------------------------------
  // LOADING
  // -------------------------------------------------------------------------

  if (loading) {

    return (
      <AppShell
        title="Transaction Details"
        breadcrumb="Payments"
      >

        <PageHeader
          title="Transaction Pipeline"
          description="Trace an approved payment request through the AEGIS transaction pipeline."
        />

        <SkeletonLines count={6} />

      </AppShell>
    )
  }


  // -------------------------------------------------------------------------
  // NO TRANSACTIONS
  // -------------------------------------------------------------------------

  if (!active) {

    return (
      <AppShell
        title="Transaction Details"
        breadcrumb="Payments"
      >

        <PageHeader
          title="Transaction Pipeline"
          description="Trace an approved payment request through the AEGIS transaction pipeline."
        />

        <Card>

          <div className="flex flex-col items-center justify-center py-16 text-center">

            <Icon
              name="payments"
              size={40}
              className="text-ink-faint"
            />

            <h3 className="mt-4 text-h3 text-ink">
              No transactions yet
            </h3>

            <p className="mt-2 max-w-md text-body-sm text-ink-muted">
              Approved payment requests will automatically
              appear here when AEGIS creates a transaction.
            </p>

          </div>

        </Card>

      </AppShell>
    )
  }


  // -------------------------------------------------------------------------
  // TRANSACTION DETAILS
  // -------------------------------------------------------------------------

  return (

    <AppShell
      title="Transaction Details"
      breadcrumb="Payments"
    >

      <PageHeader
        title="Transaction Pipeline"
        description="Trace an approved payment request through the AEGIS transaction pipeline."
      />


      <div className="flex flex-col gap-6">


        {/* ================================================================= */}
        {/* TRANSACTION INFORMATION                                          */}
        {/* ================================================================= */}

        <Card>

          <div className="flex flex-wrap items-start justify-between gap-4">

            <div>

              <p className="font-mono text-caption text-ink-faint">
                {active.id}
              </p>

              <h3 className="mt-1 text-h2 text-ink">
                ${active.amount.toLocaleString()}
              </h3>

              <p className="mt-1 text-body-sm text-ink-muted">
                {active.task}
              </p>

            </div>


            <StatusBadge
              status={
                active.status === 'settled'
                  ? 'confirmed'
                  : active.status === 'payment_required'
                    ? 'pending'
                    : 'pending'
              }
            />

          </div>


          {/* ================================================================= */}
          {/* IDENTIFIERS                                                       */}
          {/* ================================================================= */}

          <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-3">


            {/* Request ID */}

            <div className="rounded-md border border-border bg-surface-low p-3">

              <p className="text-caption text-ink-faint">
                Request ID
              </p>

              <p className="mt-1 break-all font-mono text-body-sm text-ink">
                {active.request_id}
              </p>

            </div>


            {/* Transaction ID */}

            <div className="rounded-md border border-border bg-surface-low p-3">

              <p className="text-caption text-ink-faint">
                Transaction ID
              </p>

              <p className="mt-1 break-all font-mono text-body-sm text-ink">
                {active.id}
              </p>

            </div>


            {/* Payment ID */}

            <div className="rounded-md border border-border bg-surface-low p-3">

              <p className="text-caption text-ink-faint">
                Payment ID
              </p>

              <p className="mt-1 break-all font-mono text-body-sm text-ink">
                {active.payment_id}
              </p>

            </div>

          </div>


          {/* ================================================================= */}
          {/* TRANSACTION DETAILS                                               */}
          {/* ================================================================= */}

          <div className="mt-5 grid grid-cols-2 gap-4 border-t border-border pt-4 text-body-sm sm:grid-cols-4">


            {/* Provider */}

            <div>

              <p className="text-caption text-ink-faint">
                Provider
              </p>

              <p className="mt-1 text-ink">
                {active.provider}
              </p>

            </div>


            {/* Currency */}

            <div>

              <p className="text-caption text-ink-faint">
                Currency
              </p>

              <p className="mt-1 font-mono text-ink">
                {active.currency}
              </p>

            </div>


            {/* Network */}

            <div>

              <p className="text-caption text-ink-faint">
                Network
              </p>

              <p className="mt-1 text-ink">
                {active.network}
              </p>

            </div>


            {/* Created */}

            <div>

              <p className="text-caption text-ink-faint">
                Created
              </p>

              <p className="mt-1 text-ink">
                {formatCreated(active)}
              </p>

            </div>

          </div>


          {/* ================================================================= */}
          {/* BLOCKCHAIN HASH                                                   */}
          {/* ================================================================= */}

          <div className="mt-4 flex items-center gap-2 rounded-md border border-border bg-surface-low px-3 py-2 font-mono text-caption text-ink-muted">

            <Icon
              name="tag"
              size={14}
            />

            <span className="truncate">

              {active.transaction_hash
                ? active.transaction_hash
                : 'Blockchain transaction hash — pending Base Sepolia integration'}

            </span>

          </div>

        </Card>


        {/* ================================================================= */}
        {/* TRANSACTION PIPELINE                                               */}
        {/* ================================================================= */}

        <Card>

          <p className="mb-5 text-label uppercase tracking-widest text-ink-faint">
            Transaction Pipeline
          </p>


          <div className="flex flex-col gap-5">


            {/* -----------------------------------------------------------------
                STEP 1 — PAYMENT REQUEST
            ----------------------------------------------------------------- */}

            <div className="flex items-start gap-3">

              <Icon
                name="check_circle"
                size={20}
                className="text-success"
                filled
              />

              <div>

                <p className="text-body-sm font-medium text-ink">
                  Payment Request
                </p>

                <p className="text-caption text-ink-muted">
                  Request {active.request_id} received by AEGIS.
                </p>

              </div>

            </div>


            {/* -----------------------------------------------------------------
                STEP 2 — TRANSACTION CREATED
            ----------------------------------------------------------------- */}

            <div className="flex items-start gap-3">

              <Icon
                name="check_circle"
                size={20}
                className="text-success"
                filled
              />

              <div>

                <p className="text-body-sm font-medium text-ink">
                  Transaction Created
                </p>

                <p className="text-caption text-ink-muted">
                  Transaction {active.id} was generated by the AEGIS backend.
                </p>

              </div>

            </div>


            {/* -----------------------------------------------------------------
                STEP 3 — PAYMENT CREATED
            ----------------------------------------------------------------- */}

            <div className="flex items-start gap-3">

              <Icon
                name="check_circle"
                size={20}
                className="text-success"
                filled
              />

              <div>

                <p className="text-body-sm font-medium text-ink">
                  Payment Created
                </p>

                <p className="text-caption text-ink-muted">
                  Payment {active.payment_id} is associated with this transaction.
                </p>

              </div>

            </div>


            {/* -----------------------------------------------------------------
                STEP 4 — BLOCKCHAIN SETTLEMENT
            ----------------------------------------------------------------- */}

            <div className="flex items-start gap-3">

              {active.transaction_hash ? (

                <Icon
                  name="check_circle"
                  size={20}
                  className="text-success"
                  filled
                />

              ) : (

                <Icon
                  name="radio_button_unchecked"
                  size={20}
                  className="text-ink-faint"
                />

              )}


              <div>

                <p
                  className={`text-body-sm font-medium ${
                    active.transaction_hash
                      ? 'text-ink'
                      : 'text-ink-faint'
                  }`}
                >
                  Blockchain Settlement
                </p>

                <p className="text-caption text-ink-muted">

                  {active.transaction_hash
                    ? `Transaction settled with hash ${active.transaction_hash}`
                    : 'Base Sepolia settlement integration coming soon.'}

                </p>

              </div>

            </div>


          </div>

        </Card>


      </div>

    </AppShell>
  )
}