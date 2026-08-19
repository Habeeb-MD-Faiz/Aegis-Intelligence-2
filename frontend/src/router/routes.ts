// `login` and `workspace` intentionally map to no page — commit 17f2382
// ("Open dashboard without login") disconnected the login flow so the public
// demo opens straight onto the dashboard. See "Dormant on purpose" in
// AGENTS.md before removing or re-enabling them.
export const ROUTES = {
  login: '/login',
  mission: '/',
  workspace: '/workspace',
  commandCenter: '/command-center',
  paymentRequests: '/payments',
  approvals: '/approvals',
  transactionDetails: '/transactions',
  policyBuilder: '/policies',
  guardrails: '/guardrails',
  incidents: '/incidents',
  blockchain: '/blockchain',
  analytics: '/analytics',
  auditLogs: '/audit-logs',
  settings: '/settings',
} as const

export type RoutePath = (typeof ROUTES)[keyof typeof ROUTES]
