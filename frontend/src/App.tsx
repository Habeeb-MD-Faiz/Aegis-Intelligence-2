import { AuthProvider } from '@/contexts/AuthContext'
import { ToastProvider } from '@/contexts/ToastContext'
import { RouterProvider, useRouter } from '@/contexts/RouterContext'
import { ROUTES } from '@/router/routes'

import { MissionControlPage } from '@/pages/MissionControlPage'
import { AICommandCenterPage } from '@/pages/AICommandCenterPage'
import { PaymentRequestsPage } from '@/pages/PaymentRequestsPage'
import { ApprovalCenterPage } from '@/pages/ApprovalCenterPage'
import { TransactionDetailsPage } from '@/pages/TransactionDetailsPage'
import { PolicyBuilderPage } from '@/pages/PolicyBuilderPage'
import { GuardrailsPage } from '@/pages/GuardrailsPage'
import { IncidentCenterPage } from '@/pages/IncidentCenterPage'
import { BlockchainCommandCenterPage } from '@/pages/BlockchainCommandCenterPage'
import { AnalyticsPage } from '@/pages/AnalyticsPage'
import { AuditLogsPage } from '@/pages/AuditLogsPage'
import { SettingsPage } from '@/pages/SettingsPage'

// LoginPage and AIWorkspacePage exist but are deliberately absent from this
// table — see "Dormant on purpose" in AGENTS.md.
const routeTable: Record<string, () => JSX.Element> = {
  [ROUTES.mission]: MissionControlPage,
  [ROUTES.commandCenter]: AICommandCenterPage,
  [ROUTES.paymentRequests]: PaymentRequestsPage,
  [ROUTES.approvals]: ApprovalCenterPage,
  [ROUTES.transactionDetails]: TransactionDetailsPage,
  [ROUTES.policyBuilder]: PolicyBuilderPage,
  [ROUTES.guardrails]: GuardrailsPage,
  [ROUTES.incidents]: IncidentCenterPage,
  [ROUTES.blockchain]: BlockchainCommandCenterPage,
  [ROUTES.analytics]: AnalyticsPage,
  [ROUTES.auditLogs]: AuditLogsPage,
  [ROUTES.settings]: SettingsPage,
}

function AppRouter() {
  const { path } = useRouter()

  const Page = routeTable[path] ?? MissionControlPage

  return <Page />
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <RouterProvider>
          <AppRouter />
        </RouterProvider>
      </ToastProvider>
    </AuthProvider>
  )
}