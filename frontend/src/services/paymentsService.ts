import { approvals, paymentRequests } from '@/data/payments'
import { withFlakiness } from './api'

import { API_BASE_URL } from '@/config'

import type {
  Approval,
  PaymentRequest,
  PaymentExecution,
} from '@/types'

/* -------------------------------------------------------------------------- */
/* Configuration                                                              */
/* -------------------------------------------------------------------------- */

/* -------------------------------------------------------------------------- */
/* Local stores                                                               */
/* -------------------------------------------------------------------------- */

let approvalsStore = [...approvals]
let paymentsStore = [...paymentRequests]

/* -------------------------------------------------------------------------- */
/* Helpers                                                                    */
/* -------------------------------------------------------------------------- */

function getErrorMessage(response: Response, fallback: string): Promise<string> {
  return response
    .text()
    .then((text) => text || fallback)
    .catch(() => fallback)
}

/* -------------------------------------------------------------------------- */
/* Approvals                                                                  */
/* -------------------------------------------------------------------------- */

export async function fetchApprovals(): Promise<Approval[]> {
  return withFlakiness([...approvalsStore])
}

export async function decideApproval(
  id: string,
  decision: 'approved' | 'rejected'
): Promise<Approval> {
  approvalsStore = approvalsStore.map((a) =>
    a.id === id
      ? { ...a, status: decision }
      : a
  )

  const updated = approvalsStore.find((a) => a.id === id)

  if (!updated) {
    throw new Error('Approval not found')
  }

  return withFlakiness(updated, 0)
}

/* -------------------------------------------------------------------------- */
/* Payment Requests                                                           */
/* -------------------------------------------------------------------------- */

export async function fetchPaymentRequests(): Promise<PaymentRequest[]> {
  const response = await fetch(
    `${API_BASE_URL}/requests`
  )

  if (!response.ok) {
    const errorText = await getErrorMessage(
      response,
      'Failed to fetch requests'
    )

    throw new Error(errorText)
  }

  const data = await response.json()

  return data.map((r: any) => ({
    id: r.id,
    vendor: r.task ?? r.vendor ?? 'Unknown',
    provider: r.provider ?? 'Unknown',
    agentId: r.agentId ?? r.agent_id ?? 'AEGIS',
    amount: Number(r.amount ?? 0),
    currency: r.currency ?? 'USD',
    category: r.category ?? 'general',
    status: r.status,
    decision: r.decision,
    riskLevel: r.riskLevel ?? r.risk_level ?? 'low',
    decisionBy: r.decisionBy ?? r.decision_by ?? 'SYSTEM',
    createdAt:
      r.createdAt ??
      r.created_at ??
      new Date().toISOString(),
    memo: r.reason ?? r.memo ?? '',
  }))
}

/* -------------------------------------------------------------------------- */
/* Approve / Reject Payment Request                                           */
/* -------------------------------------------------------------------------- */

export async function decidePaymentRequest(
  id: string,
  decision: 'approved' | 'rejected'
): Promise<PaymentRequest> {
  const response = await fetch(
    `${API_BASE_URL}/requests/${id}/decision`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        decision,
      }),
    }
  )

  if (!response.ok) {
    const errorText = await getErrorMessage(
      response,
      'Failed to update request'
    )

    throw new Error(
      `Failed to update request: ${errorText}`
    )
  }

  const r = await response.json()

  return {
    id: r.id,
    vendor: r.task ?? r.vendor ?? 'Unknown',
    provider: r.provider ?? 'Unknown',
    agentId: r.agentId ?? r.agent_id ?? 'AEGIS',
    amount: Number(r.amount ?? 0),
    currency: r.currency ?? 'USD',
    category: r.category ?? 'general',
    status: r.status,
    decision: r.decision,
    riskLevel: r.riskLevel ?? r.risk_level ?? 'low',
    decisionBy: r.decisionBy ?? r.decision_by ?? 'SYSTEM',
    createdAt:
      r.createdAt ??
      r.created_at ??
      new Date().toISOString(),
    memo: r.reason ?? r.memo ?? '',
  }
}

/* -------------------------------------------------------------------------- */
/* x402-style Payment Execution                                               */
/* -------------------------------------------------------------------------- */

export interface CreatePaymentRequestInput {
  requestId: string
  task: string
  provider: string
  api: string
  amount: number
}

export async function createPaymentRequest(
  data: CreatePaymentRequestInput
): Promise<PaymentExecution> {

  const response = await fetch(
    `${API_BASE_URL}/payments/request`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        request_id: data.requestId,
        task: data.task,
        provider: data.provider,
        api: data.api,
        amount: data.amount,
      }),
    }
  )

  if (!response.ok) {
    const errorText = await getErrorMessage(
      response,
      'Failed to create payment request'
    )

    throw new Error(
      `Failed to create payment request: ${errorText}`
    )
  }

  const r = await response.json()

  /*
   * The backend is the source of truth for these identifiers.
   *
   * We allow camelCase/snake_case because FastAPI/frontend models
   * can use either naming convention.
   */

  const paymentId =
    r.payment_id ??
    r.paymentId

  const requestId =
    r.request_id ??
    r.requestId ??
    data.requestId

  // const transactionId =
  //   r.transaction_id ??
  //   r.transactionId ??
  //   data.transactionId

  const task =
    r.task ??
    r.task_name ??
    r.taskName ??
    data.task

  const provider =
    r.provider ??
    r.provider_name ??
    r.providerName ??
    data.provider

  const api =
    r.api ??
    r.api_name ??
    r.apiName ??
    data.api

  const amount =
    r.amount !== undefined &&
    r.amount !== null
      ? Number(r.amount)
      : data.amount

  const currency =
    r.currency ??
    'USDC'

  const network =
    r.network ??
    'Base Sepolia'

  const payTo =
    r.pay_to ??
    r.payTo ??
    null

  const status =
    r.status ??
    'payment_required'

  const paymentSignature =
    r.payment_signature ??
    r.paymentSignature ??
    null

  const transactionHash =
    r.transaction_hash ??
    r.transactionHash ??
    null

  const createdAt =
    r.created_at ??
    r.createdAt ??
    new Date().toISOString()

  const settledAt =
    r.settled_at ??
    r.settledAt

  /*
   * payment_id MUST come from the backend.
   *
   * We intentionally do not generate one here because that would
   * undermine the purpose of showing that the backend created it.
   */

  if (!paymentId) {
    console.error(
      'Payment API response is missing payment_id:',
      r
    )

    throw new Error(
      'Payment request was created, but the backend did not return a payment_id.'
    )
  }

  /*
   * request_id and transaction_id are also required for the
   * transaction/payment trace shown in the UI.
   */

  if (!requestId) {
    throw new Error(
      'Payment response is missing request_id.'
    )
  }
  const transactionId =
    r.transaction_id ?? r.transactionId
  if (!transactionId) {
    throw new Error(
      'Payment response is missing transaction_id.'
    )
  }

  const payment: PaymentExecution = {
    payment_id: paymentId,
    request_id: requestId,
    transaction_id: transactionId,
    task,
    provider,
    api,
    amount,
    currency,
    network,
    pay_to: payTo,
    status,
    payment_signature: paymentSignature,
    transaction_hash: transactionHash,
    created_at: createdAt,
    settled_at: settledAt,
  }

  console.log(
    'Payment request created:',
    payment
  )

  return payment
}

/* -------------------------------------------------------------------------- */
/* Dashboard                                                                  */
/* -------------------------------------------------------------------------- */

export interface DashboardStats {
  totalRequests: number
  pending: number
  approved: number
  rejected: number
  todaySpend: number
}

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const response = await fetch(
    `${API_BASE_URL}/dashboard`
  )

  if (!response.ok) {
    const errorText = await getErrorMessage(
      response,
      'Failed to fetch dashboard stats'
    )

    throw new Error(errorText)
  }

  return response.json()
}