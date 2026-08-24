import type { ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'

interface AppShellProps {
  title: string
  breadcrumb?: string
  children: ReactNode
}

export function AppShell({ title, breadcrumb, children }: AppShellProps) {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-bg">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <TopBar title={title} breadcrumb={breadcrumb} />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-[1440px] px-6 py-6">{children}</div>
        </main>
      </div>
    </div>
  )
}
