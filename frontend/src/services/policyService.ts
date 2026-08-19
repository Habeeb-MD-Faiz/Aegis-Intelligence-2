import { policies } from '@/data/governance'
import { withFlakiness } from './api'
import type { Policy } from '@/types'
import { API_BASE_URL, operatorHeaders } from '@/config'

let store = [...policies]


// ============================================================
// EXISTING POLICY FUNCTIONS
// ============================================================

export async function fetchPolicies(): Promise<Policy[]> {
  const response = await fetch(
    `${API_BASE_URL}/policies`
  )

  if (!response.ok) {
    throw new Error('Failed to fetch policies')
  }

  const config = await response.json()

  const backendPolicies: Policy[] = [
    {
      id: 'provider-allow-list',
      name: 'Provider Allow List',
      description: 'Controls which providers agents may use.',
      status: 'active',
      severity: 'high',

      rules: config.allowed_providers.map(
        (provider: string, index: number) => ({
          id: `provider-${index}`,
          field: 'provider',
          operator: 'allowed',
          value: provider,
        })
      ),

      updatedAt: new Date().toISOString(),
      appliesTo: ['all'],
    },

    {
      id: 'auto-approval-limit',
      name: 'Autonomous Approval Limit',
      description:
        'Maximum amount that can be automatically approved.',
      status: 'active',
      severity: 'medium',

      rules: [
        {
          id: 'auto-limit',
          field: 'amount',
          operator: '<=',
          value: `$${config.auto_approve_limit}`,
        },
      ],

      updatedAt: new Date().toISOString(),
      appliesTo: ['all'],
    },

    {
      id: 'human-review-limit',
      name: 'Human Review Threshold',
      description:
        'Transactions above the autonomous limit require human approval.',
      status: 'active',
      severity: 'medium',

      rules: [
        {
          id: 'human-limit',
          field: 'amount',
          operator: '<=',
          value: `$${config.human_review_limit}`,
        },
      ],

      updatedAt: new Date().toISOString(),
      appliesTo: ['all'],
    },

    {
      id: 'daily-budget',
      name: 'Daily Spending Budget',
      description:
        'Maximum allowed autonomous spending per day.',
      status: 'active',
      severity: 'high',

      rules: [
        {
          id: 'daily-budget',
          field: 'daily_spend',
          operator: '<=',
          value: `$${config.daily_budget}`,
        },
      ],

      updatedAt: new Date().toISOString(),
      appliesTo: ['all'],
    },
  ]

  return backendPolicies
}


export async function savePolicy(
  policy: Policy
): Promise<Policy> {
  store = store.some(
    (p) => p.id === policy.id
  )
    ? store.map(
        (p) => p.id === policy.id ? policy : p
      )
    : [policy, ...store]

  return withFlakiness(
    policy,
    0
  )
}


// ============================================================
// AI POLICY SUGGESTIONS
// ============================================================

export interface PolicySuggestion {
  suggestion_type:
    | 'spending_limit'
    | 'provider_allowlist'
    | 'frequency_limit'
    | 'category_limit'
    | 'daily_budget'
    | 'risk_rule'

  title: string

  category?: string | null

  current_value?: string | null

  suggested_value?: string | null

  reason: string

  confidence: number

  evidence_count: number

  recommendation:
    | 'tighten'
    | 'relax'
    | 'add'
    | 'remove'
    | 'monitor'
}


export interface PolicySuggestionsResponse {
  suggestions: PolicySuggestion[]
  message?: string
}


export async function fetchPolicySuggestions(): Promise<PolicySuggestionsResponse> {
  const response = await fetch(
    `${API_BASE_URL}/policy-suggestions`
  )

  if (!response.ok) {
    throw new Error(
      'Failed to generate policy suggestions'
    )
  }

  return response.json()
}


export async function applyPolicySuggestion(
  suggestion: PolicySuggestion
) {
  const response = await fetch(
    `${API_BASE_URL}/policies/apply`,
    {
      method: 'POST',

      // Control plane: a suggestion only takes effect when a human applies it
      // with an operator credential. Nothing here applies itself.
      headers: operatorHeaders(),

      body: JSON.stringify(suggestion),
    }
  )

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      throw new Error(
        'Operator credential required to apply policy changes.',
      )
    }

    throw new Error(
      'Failed to apply policy suggestion'
    )
  }

  return response.json()
}