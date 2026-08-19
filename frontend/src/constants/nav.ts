import { ROUTES } from '@/router/routes'
import { HIDE_MOCK_SCREENS } from '@/config'

export interface NavItem {
  label: string
  path: string
  icon: string
}

export interface NavGroup {
  label: string
  items: NavItem[]
}

/**
 * Screens still backed by static fixtures in `src/data/` rather than live
 * backend data.
 *
 * These are worth hiding before a demo. Analytics in particular computes
 * "Total Spent" from mock payments, so a viewer who runs three transactions
 * and then opens it sees numbers with no relationship to what they just did —
 * which casts doubt on the screens that *are* real.
 *
 * Set VITE_HIDE_MOCK_SCREENS=true to drop them from the navigation.
 */
export const MOCK_BACKED_ROUTES: string[] = [
  // Analytics now reads /requests and is no longer listed here.
  ROUTES.incidents,
  ROUTES.auditLogs,
  ROUTES.approvals,
]

export function isMockBacked(path: string): boolean {
  return MOCK_BACKED_ROUTES.includes(path)
}

const allNavGroups: NavGroup[] = [
  {
    label: 'Operate',
    items: [
      {
        label: 'Mission Control',
        path: ROUTES.mission,
        icon: 'space_dashboard',
      },
      {
        label: 'AI Command Center',
        path: ROUTES.commandCenter,
        icon: 'terminal',
      },
    ],
  },

  {
    label: 'Payments',
    items: [
      {
        label: 'Payment Requests',
        path: ROUTES.paymentRequests,
        icon: 'payments',
      },
      {
        label: 'Approval Center',
        path: ROUTES.approvals,
        icon: 'verified_user',
      },
      {
        label: 'Transaction Details',
        path: ROUTES.transactionDetails,
        icon: 'receipt_long',
      },
    ],
  },

  {
    label: 'Govern',
    items: [
      {
        label: 'Policy Builder',
        path: ROUTES.policyBuilder,
        icon: 'gavel',
      },
      {
        label: 'Guardrails',
        path: ROUTES.guardrails,
        icon: 'shield',
      },
      {
        label: 'Incident Center',
        path: ROUTES.incidents,
        icon: 'emergency',
      },
      {
        label: 'Blockchain Command Center',
        path: ROUTES.blockchain,
        icon: 'hub',
      },
    ],
  },

  {
    label: 'Insights',
    items: [
      {
        label: 'Analytics',
        path: ROUTES.analytics,
        icon: 'monitoring',
      },
      {
        label: 'Audit Logs',
        path: ROUTES.auditLogs,
        icon: 'history',
      },
    ],
  },
]

/**
 * Navigation as rendered. Fixture-backed screens drop out when
 * VITE_HIDE_MOCK_SCREENS=true, and any group left empty drops with them.
 */
export const navGroups: NavGroup[] = HIDE_MOCK_SCREENS
  ? allNavGroups
      .map((group) => ({
        ...group,
        items: group.items.filter((item) => !isMockBacked(item.path)),
      }))
      .filter((group) => group.items.length > 0)
  : allNavGroups

export const settingsNav: NavItem = {
  label: 'Settings',
  path: ROUTES.settings,
  icon: 'settings',
}