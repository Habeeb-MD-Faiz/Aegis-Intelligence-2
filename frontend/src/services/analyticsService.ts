/**
 * Analytics, computed from live backend data.
 *
 * This previously derived every figure from the static fixtures in
 * `@/data/payments`, so "Total Spent" had no relationship to the transactions
 * a viewer had just made. Running three payments and then opening Analytics
 * showed unrelated numbers, which cast doubt on the screens that were real.
 *
 * It now reads `/requests` and derives everything from actual decisions. The
 * output shape is unchanged, so AnalyticsPage did not need rewriting.
 */

import { API_BASE_URL } from '@/config'

interface RequestRecord {
  id: string
  task?: string
  provider?: string
  amount?: number
  category?: string
  status?: string
  decision?: string
  riskLevel?: string
  riskScore?: number
  createdAt?: string
}

async function fetchRequests(): Promise<RequestRecord[]> {
  const response = await fetch(`${API_BASE_URL}/requests`)

  if (!response.ok) {
    throw new Error('Failed to load analytics data')
  }

  return response.json()
}

function dayLabel(iso?: string): string {
  if (!iso) return 'Unknown'

  const date = new Date(iso)

  return Number.isNaN(date.getTime())
    ? 'Unknown'
    : date.toLocaleDateString(undefined, { weekday: 'short' })
}

export async function fetchAnalytics() {
  const requests = await fetchRequests()

  const totalPayments = requests.length

  const approved = requests.filter((r) => r.status === 'approved')
  const rejected = requests.filter((r) => r.status === 'rejected')
  const pending = requests.filter((r) => r.status === 'pending')

  // Only approved requests represent money actually committed.
  const totalSpent = approved.reduce((sum, r) => sum + Number(r.amount ?? 0), 0)

  // ---- Spend by category (percentage of committed spend) ----
  const categoryTotals = new Map<string, number>()

  approved.forEach((r) => {
    const key = r.category ?? 'uncategorised'
    categoryTotals.set(key, (categoryTotals.get(key) ?? 0) + Number(r.amount ?? 0))
  })

  const totalCategorySpend =
    Array.from(categoryTotals.values()).reduce((sum, v) => sum + v, 0) || 1

  const spendByCategory = Array.from(categoryTotals.entries())
    .map(([label, value]) => ({
      label,
      value: Math.round((value / totalCategorySpend) * 100),
    }))
    .sort((a, b) => b.value - a.value)

  // ---- Average payment by category ----
  const categoryStats = new Map<string, { total: number; count: number }>()

  approved.forEach((r) => {
    const key = r.category ?? 'uncategorised'
    const current = categoryStats.get(key) ?? { total: 0, count: 0 }

    current.total += Number(r.amount ?? 0)
    current.count += 1

    categoryStats.set(key, current)
  })

  const averagePaymentByCategory = Array.from(categoryStats.entries())
    .map(([label, stats]) => ({
      label,
      value: stats.count ? Math.round(stats.total / stats.count) : 0,
    }))
    .sort((a, b) => b.value - a.value)

  // ---- Provider usage ----
  const providerCounts = new Map<string, number>()

  requests.forEach((r) => {
    const key = r.provider ?? 'Unknown'
    providerCounts.set(key, (providerCounts.get(key) ?? 0) + 1)
  })

  const providerUsage = Array.from(providerCounts.entries())
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => b.value - a.value)

  // ---- Governance decisions by category ----
  const decisionMap = new Map<
    string,
    { approved: number; review: number; rejected: number }
  >()

  requests.forEach((r) => {
    const key = r.category ?? 'uncategorised'
    const current = decisionMap.get(key) ?? {
      approved: 0,
      review: 0,
      rejected: 0,
    }

    if (r.status === 'rejected') current.rejected += 1
    else if (r.status === 'pending') current.review += 1
    else current.approved += 1

    decisionMap.set(key, current)
  })

  const policyDecisions = Array.from(decisionMap.entries()).map(
    ([label, values]) => ({ label, ...values }),
  )

  // ---- Payment volume over time, from real timestamps ----
  const volumeMap = new Map<string, number>()

  requests.forEach((r) => {
    const label = dayLabel(r.createdAt)
    volumeMap.set(label, (volumeMap.get(label) ?? 0) + 1)
  })

  const paymentVolumeSeries = Array.from(volumeMap.entries()).map(
    ([label, value]) => ({ label, value }),
  )

  // ---- Risk vs amount ----
  // Uses the backend's behavioural risk score where present, falling back to
  // the level when an older record predates scoring.
  const riskPoints = requests.map((r) => ({
    id: r.id,
    amount: Number(r.amount ?? 0),
    riskScore:
      typeof r.riskScore === 'number'
        ? r.riskScore
        : r.riskLevel === 'low'
          ? 25
          : r.riskLevel === 'medium'
            ? 50
            : 75,
    riskLevel: r.riskLevel ?? 'low',
    category: r.category ?? 'uncategorised',
  }))

  return {
    totalSpent,
    totalPayments,
    approvedPayments: approved.length,
    rejectedPayments: rejected.length,
    pendingPayments: pending.length,
    autoApprovalRate: totalPayments
      ? Math.round((approved.length / totalPayments) * 100)
      : 0,
    spendByCategory,
    paymentVolumeSeries,
    averagePaymentByCategory,
    providerUsage,
    policyDecisions,
    riskPoints,
  }
}
