import { policies } from '@/data/governance'
import { fixture, requestJson } from './api'
import type { Policy } from '@/types'
import { operatorHeaders } from '@/config'

let store = [...policies]


// ============================================================
// EXISTING POLICY FUNCTIONS
// ============================================================

export async function fetchPolicies(): Promise<Policy[]> {
  const config = await requestJson<any>('/policies')

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

  return fixture(policy)
}


// ============================================================
// AI POLICY SUGGESTIONS
// ============================================================

export interface PolicySuggestion {
  // Mirrors the Literal in backend/policy_builder.py. Every member must have a
  // handler in backend/policy_store.py — see the note there.
  suggestion_type:
    | 'spending_limit'
    | 'provider_allowlist'
    | 'frequency_limit'
    | 'daily_budget'

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


export function fetchPolicySuggestions(): Promise<PolicySuggestionsResponse> {
  return requestJson<PolicySuggestionsResponse>('/policy-suggestions')
}


export async function applyPolicySuggestion(
  suggestion: PolicySuggestion
) {
  return requestJson<{ success: boolean; message: string; config: unknown }>(
    '/policies/apply',
    {
      method: 'POST',

      // Control plane: a suggestion only takes effect when a human applies it
      // with an operator credential. Nothing here applies itself.
      headers: operatorHeaders(),

      body: JSON.stringify(suggestion),
    },
  )
}