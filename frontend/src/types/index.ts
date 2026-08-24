// ---------------------------------------------------------------------------
// Domain types shared across services, hooks and pages.
// ---------------------------------------------------------------------------

export type RiskLevel =
  | 'low'
  | 'medium'
  | 'high'
  | 'critical'

export type Status =
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'neutral'


// ---------------------------------------------------------------------------
// User
// ---------------------------------------------------------------------------

export interface User {
  id: string
  name: string
  role: 'Administrator' | 'Employee' | 'Auditor'
  enterpriseId: string
  avatarInitials: string
}


// ---------------------------------------------------------------------------
// Agent
// ---------------------------------------------------------------------------

export interface Agent {
  id: string
  name: string
  objective: string
  status: 'running' | 'idle' | 'paused' | 'error'
  riskLevel: RiskLevel
  coherence: number
  spendToday: number
  lastActive: string
}


// ---------------------------------------------------------------------------
// Agent Logs
// ---------------------------------------------------------------------------

export interface AgentLogEntry {
  id: string
  agentId: string
  timestamp: string
  actor:
    | 'SYSTEM'
    | 'AGENT'
    | 'RISK'
    | 'POLICY'
    | 'HUMAN'
  message: string
  kind:
    | 'info'
    | 'processing'
    | 'passed'
    | 'flagged'
    | 'blocked'
}


// ---------------------------------------------------------------------------
// Approvals
// ---------------------------------------------------------------------------

export interface Approval {
  id: string
  title: string
  requestedBy: string
  agentId: string
  amount: number
  currency: string
  riskLevel: RiskLevel
  status: 'pending' | 'approved' | 'rejected'
  createdAt: string
  reason: string
  policyRefs: string[]
}


// ---------------------------------------------------------------------------
// Payment Requests
// ---------------------------------------------------------------------------

export interface PaymentRequest {
  id: string
  vendor: string
  provider: string
  agentId: string
  amount: number
  currency: string
  category: string

  decision:
    | 'approved'
    | 'human_review'
    | 'blocked'

  status:
    | 'pending'
    | 'approved'
    | 'rejected'
    | 'processing'
    | 'settled'

  riskLevel: RiskLevel
  decisionBy: string
  createdAt: string
  memo: string
}


// ---------------------------------------------------------------------------
// Transactions
// ---------------------------------------------------------------------------

/**
 * A transaction as `GET /transactions` actually returns it.
 *
 * This interface used to additionally require `hash`, `agentId`, `from`, `to`,
 * `blockHeight`, `confirmations`, `networkFee` and a `steps: TransactionStep[]`
 * pipeline — left over from a fixture that no longer exists. Nothing produced
 * them and nothing read them; the mismatch was invisible because the service
 * parsed the response as `any` before mapping it. Keep this shape honest
 * against the backend.
 */
export interface Transaction {
  id: string

  amount: number
  currency: string

  // Transaction / payment lifecycle
  status:
    | 'confirmed'
    | 'pending'
    | 'failed'
    | 'payment_required'
    | 'authorized'
    | 'verified'
    | 'verification_failed'
    | 'settling'
    | 'settled'

  // Payment execution information
  task?: string
  provider?: string
  api?: string

  request_id?: string
  payment_id?: string

  payment_signature?: string | null
  transaction_hash?: string | null

  network?: string
  pay_to?: string

  // Timestamps
  timestamp?: string
  created_at?: string
  settled_at?: string | null
}



// ---------------------------------------------------------------------------
// Policies
// ---------------------------------------------------------------------------

export interface PolicyRule {
  id: string
  field: string
  operator: string
  value: string
}


export interface Policy {
  id: string
  name: string
  description: string

  status:
    | 'active'
    | 'draft'
    | 'archived'

  severity: RiskLevel
  rules: PolicyRule[]
  updatedAt: string
  appliesTo: string[]
}


// ---------------------------------------------------------------------------
// Guardrails
// ---------------------------------------------------------------------------

export interface Guardrail {
  id: string
  name: string

  category:
    | 'spending'
    | 'access'
    | 'compliance'
    | 'behavioral'

  description: string
  enabled: boolean
  threshold?: string
  triggeredCount: number
}


// ---------------------------------------------------------------------------
// Incidents
// ---------------------------------------------------------------------------

export interface Incident {
  id: string
  title: string
  severity: RiskLevel

  status:
    | 'open'
    | 'investigating'
    | 'contained'
    | 'resolved'

  agentId: string
  detectedAt: string
  summary: string
  timeline: IncidentEvent[]
}


export interface IncidentEvent {
  id: string
  timestamp: string
  label: string
  actor: string
}


// ---------------------------------------------------------------------------
// Blockchain
// ---------------------------------------------------------------------------

export interface BlockchainNode {
  id: string
  region: string

  status:
    | 'healthy'
    | 'degraded'
    | 'offline'

  latencyMs: number
  throughput: number
}


export interface BlockEntry {
  height: number
  hash: string
  txCount: number
  timestamp: string
  validator: string
}


// ---------------------------------------------------------------------------
// Audit
// ---------------------------------------------------------------------------

export interface AuditEntry {
  id: string
  timestamp: string
  actor: string
  action: string
  target: string

  result:
    | 'success'
    | 'failure'

  ip: string
}


// ---------------------------------------------------------------------------
// Analytics
// ---------------------------------------------------------------------------

export interface AnalyticsSeriesPoint {
  label: string
  value: number
}


export interface StatDelta {
  label: string
  value: string
  delta?: string

  deltaDirection?:
    | 'up'
    | 'down'
    | 'flat'

  status?: Status
  icon?: string
}


// ---------------------------------------------------------------------------
// x402-Style Payment Execution
// ---------------------------------------------------------------------------

export type PaymentExecutionStatus =
  | 'payment_required'
  | 'authorized'
  | 'verified'
  | 'verification_failed'
  | 'settling'
  | 'settled'


export interface PaymentExecution {
  /*
   * Generated by the AEGIS backend.
   */
  payment_id: string

  /*
   * Original AEGIS request identifier.
   */
  request_id: string

  /*
   * Internal transaction identifier.
   */
  transaction_id: string

  /*
   * Human-readable task being executed.
   */
  task: string

  /*
   * Payment/API provider.
   */
  provider: string

  /*
   * API being accessed.
   */
  api: string

  /*
   * Payment amount.
   */
  amount: number

  /*
   * Payment currency.
   */
  currency: string

  /*
   * Intended blockchain network.
   *
   * Currently Base Sepolia is prepared for integration.
   */
  network: string

  /*
   * Recipient address.
   *
   * This may be null/empty in the current prototype
   * because actual blockchain settlement is not implemented yet.
   */
  pay_to: string | null

  /*
   * Current x402-style lifecycle state.
   */
  status: PaymentExecutionStatus

  /*
   * Payment authorization signature.
   *
   * Null until authorization is actually performed.
   */
  payment_signature: string | null

  /*
   * Blockchain transaction hash.
   *
   * Null until an actual on-chain transaction is submitted.
   */
  transaction_hash: string | null

  /*
   * Backend creation timestamp.
   */
  created_at: string

  /*
   * Settlement timestamp.
   *
   * Undefined until settlement occurs.
   */
  settled_at?: string
}