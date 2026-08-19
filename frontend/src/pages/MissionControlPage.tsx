import { useEffect, useRef, useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { StatCard } from '@/components/ui/StatCard'
import { Card, CardHeader } from '@/components/ui/Card'
import { Badge, RiskBadge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Icon } from '@/components/icons/Icon'
import { SkeletonCard } from '@/components/ui/Skeleton'
import { ErrorState } from '@/components/ui/ErrorState'
import { useAsync } from '@/hooks/useAsync'
import { fetchAgents } from '@/services/agentsService'
import { fetchApprovals } from '@/services/paymentsService'
import { useRouter } from '@/contexts/RouterContext'
import { ROUTES } from '@/router/routes'
import type { RiskLevel } from '@/types'
import { executeTask } from '@/services/taskService'
import type { ExecuteTaskResponse } from '@/services/taskService'
import { useTask } from '@/contexts/TaskContext'


// ---------------------------------------------------------------------------
// AI Task Composer — execution simulation
// ---------------------------------------------------------------------------

type ExecutionStatus = 'idle' | 'running' | 'complete'

const EXECUTION_STEPS = [
  'Request received',
  'Initializing AI Task Agent…',
  'AI Task Agent ready',
  'Understanding your request…',
  'Selecting required external services…',
  'Checking payment requirements…',
  'Generating payment request…',
  'Preparing secure transaction…',
]

const STEP_DURATION_MS = 480 // 8 steps × 480ms ≈ 3.8s, close to the ~4s target

const TASK_PLACEHOLDER = `Examples:

Research Tesla's latest earnings using premium financial APIs.

Book a flight to Singapore under ₹50,000.

Generate a competitive analysis report.

Summarize today's cybersecurity news.

Analyze this dataset and prepare a presentation.`

interface ExecutionTimelineProps {
  currentStepIndex: number
  status: ExecutionStatus
}

/** Shared progressive step list used both inside the composer and the Task Execution card. */
function ExecutionTimeline({ currentStepIndex, status }: ExecutionTimelineProps) {
  if (status === 'idle') return null

  return (
    <ol className="flex flex-col gap-2.5">
      {EXECUTION_STEPS.slice(0, currentStepIndex + 1).map((label, i) => {
        const isDone = i < currentStepIndex || status === 'complete'
        const isActive = i === currentStepIndex && status === 'running'
        return (
          <li key={label} className="flex animate-fade-in items-center gap-2.5">
            {isDone ? (
              <Icon name="check_circle" size={18} className="shrink-0 text-success" filled />
            ) : (
              <span className="relative flex h-[18px] w-[18px] shrink-0 items-center justify-center">
                <span className={`h-2 w-2 rounded-full bg-accent ${isActive ? 'animate-pulse-glow' : ''}`} />
              </span>
            )}
            <span className={`text-body-sm ${isDone ? 'text-ink-muted' : 'text-ink'}`}>{label}</span>
          </li>
        )
      })}
    </ol>
  )
}

export function MissionControlPage() {
  const { navigate } = useRouter()
  const agentsState = useAsync(fetchAgents)
  const approvalsState = useAsync(fetchApprovals)

  const pendingApprovals = approvalsState.data?.filter((a) => a.status === 'pending') ?? []
  const todaySpend = (agentsState.data ?? []).reduce((sum, a) => sum + a.spendToday, 0)

  // -- Task composer state ---------------------------------------------------
  const [taskInput, setTaskInput] = useState('')
  const { taskResult, setTaskResult } = useTask()
  const [executionStatus, setExecutionStatus] = useState<ExecutionStatus>('idle')
  const [currentStepIndex, setCurrentStepIndex] = useState(-1)
  const timeoutsRef = useRef<ReturnType<typeof setTimeout>[]>([])

  useEffect(() => {
    return () => {
      timeoutsRef.current.forEach(clearTimeout)
    }
  }, [])

  async function handleExecuteTask() {
    if (!taskInput.trim() || executionStatus === 'running') return

    timeoutsRef.current.forEach(clearTimeout)
    timeoutsRef.current = []

    setExecutionStatus('running')
    setCurrentStepIndex(0)

    // Start backend immediately
    const taskPromise = executeTask(taskInput)

    // Run animation
    EXECUTION_STEPS.forEach((_, i) => {
      if (i === 0) return

      const id = setTimeout(() => {
        setCurrentStepIndex(i)
      }, i * STEP_DURATION_MS)

      timeoutsRef.current.push(id)
    })

    // Wait until animation finishes
    await new Promise((resolve) =>
      setTimeout(resolve, EXECUTION_STEPS.length * STEP_DURATION_MS)
    )


    try {

      const result = await taskPromise

      if (result.decision === "blocked") {

        setExecutionStatus("idle")

        alert(`Blocked by Guardrails\n\n${result.reason}`)

        return
      }

      if (result.decision === "approved") {

        setTaskResult(result)

        setExecutionStatus("complete")

        return
      }

      if (result.decision === "human_review") {

        setTaskResult(result)

        setExecutionStatus("complete")

        setTimeout(() => {
          navigate(ROUTES.paymentRequests)
        }, 800)

        return
      }
    } catch (err) {
      console.error(err)

      setExecutionStatus('idle')

    }

    
  }

  function handleNewTask() {
    timeoutsRef.current.forEach(clearTimeout)
    timeoutsRef.current = []
    setExecutionStatus('idle')
    setCurrentStepIndex(-1)
    setTaskInput('')
  }

  const isRunning = executionStatus === 'running'
  const isComplete = executionStatus === 'complete'

  return (
    <AppShell title="Mission Control" breadcrumb="Operate">
      <div className="mb-6 flex items-center gap-2 text-label uppercase tracking-widest text-success">
        <span className="h-1.5 w-1.5 animate-pulse-glow rounded-full bg-success" />
        System Status: Optimal
      </div>

      {/* AI Task Composer — primary entry point */}
      <div className="mb-8 rounded-xl border border-border bg-gradient-to-br from-surface-low to-surface p-8">
        <div className="mx-auto max-w-2xl text-center">
          <h1 className="text-display text-ink">AEGIS AI</h1>
          <p className="mt-3 text-body-lg text-ink-muted">Tell AEGIS what you'd like to accomplish.</p>

          <div className="mt-6 text-left">
            <textarea
              value={taskInput}
              onChange={(e) => setTaskInput(e.target.value)}
              disabled={isRunning || isComplete}
              placeholder={TASK_PLACEHOLDER}
              rows={6}
              className="focus-ring w-full resize-none rounded-lg border border-border-strong bg-surface-low p-4 text-body text-ink placeholder:text-ink-faint disabled:cursor-not-allowed disabled:opacity-60"
            />

            {executionStatus === 'idle' && (
              <Button size="lg" className="mt-4 w-full" icon="bolt" onClick={handleExecuteTask} disabled={!taskInput.trim()}>
                Execute Task
              </Button>
            )}

            {isRunning && (
              <div className="mt-5 rounded-lg border border-border bg-surface-low p-5">
                <ExecutionTimeline currentStepIndex={currentStepIndex} status={executionStatus} />
              </div>
            )}

            {isComplete && (
              <div className="mt-5 flex items-center justify-between rounded-lg border border-success/30 bg-success-container p-5">
                <div className="flex items-center gap-2.5 text-success">
                  <Icon name="check_circle" size={20} filled />
                  <span className="text-body-sm font-medium">Payment request generated successfully.</span>
                </div>
                <Button variant="ghost" size="sm" onClick={handleNewTask}>
                  New task
                </Button>
              </div>
            )}

            {taskResult && (
              <div className="mt-5 rounded-lg border border-border bg-surface-low p-4 text-left">
                <h3 className="mb-3 text-body font-medium text-ink">
                  Backend Response
                </h3>

                <p className="text-body-sm">
                  <strong>Provider:</strong> {taskResult.provider}
                </p>

                <p className="text-body-sm">
                  <strong>API:</strong> {taskResult.api}
                </p>

                <p className="text-body-sm">
                  <strong>Category:</strong> {taskResult.category}
                </p>

                <p className="text-body-sm">
                  <strong>Amount:</strong> ₹{taskResult.amount}
                </p>

                <p className="text-body-sm">
                  <strong>Decision:</strong> {taskResult.decision}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* {agentsState.loading ? (
        <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : agentsState.error ? (
        <div className="mb-8">
          <ErrorState message={agentsState.error} onRetry={agentsState.refetch} />
        </div>
      ) : (
        <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard label="AI Tasks" value={String(TASKS_EXECUTED_TODAY)} delta="Tasks executed today" deltaDirection="up" icon="smart_toy" />
          <StatCard
            label="Today's Spend"
            value={`$${todaySpend.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
            delta="/ $500,000 cap"
            deltaDirection="flat"
            icon="payments"
          />
          <StatCard
            label="Pending Approvals"
            value={String(pendingApprovals.length)}
            delta={pendingApprovals.length > 2 ? 'Needs attention' : 'Nominal'}
            deltaDirection={pendingApprovals.length > 2 ? 'down' : 'flat'}
            icon="verified_user"
          />
          <StatCard label="Network Coherence" value="Secure" delta="99.2%" deltaDirection="up" icon="hub" />
        </div>
      )} */}

      {/* <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader
            title={
              <span className="flex items-center gap-2">
                Task Execution
                {isRunning && (
                  <Badge tone="accent" dot>
                    Live
                  </Badge>
                )}
              </span>
            }
            subtitle="Live execution status of your current AI request."
          />
          {executionStatus === 'idle' && (
            <div className="flex flex-col items-center justify-center gap-1 py-10 text-center">
              <p className="text-body-sm font-medium text-ink">No active task.</p>
              <p className="text-body-sm text-ink-muted">Submit a request above to begin.</p>
            </div>
          )}
          {isRunning && <ExecutionTimeline currentStepIndex={currentStepIndex} status={executionStatus} />}
          {isComplete && (
            <div className="flex items-center gap-2.5 text-success">
              <Icon name="check_circle" size={18} filled />
              <div>
                <p className="text-body-sm font-medium">Payment request generated successfully.</p>
                <p className="text-caption text-ink-faint">Redirecting…</p>
              </div>
            </div>
          )}
        </Card>

        <Card>
          <CardHeader
            title="Pending Approvals"
            action={
              <Button size="sm" variant="ghost" onClick={() => navigate(ROUTES.approvals)}>
                View all
              </Button>
            }
          />
          {approvalsState.loading ? (
            <div className="flex flex-col gap-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="skeleton h-12 w-full" />
              ))}
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {pendingApprovals.length === 0 && (
                <p className="text-body-sm text-ink-muted">No approvals waiting on you right now.</p>
              )}
              {pendingApprovals.slice(0, 4).map((a) => (
                <button
                  key={a.id}
                  onClick={() => navigate(ROUTES.approvals)}
                  className="focus-ring flex items-center justify-between rounded-md border border-border-subtle bg-surface-low p-3 text-left transition-colors hover:border-border-strong"
                >
                  <div className="min-w-0">
                    <p className="truncate text-body-sm font-medium text-ink">{a.title}</p>
                    <p className="text-caption text-ink-faint">{a.agentId}</p>
                  </div>
                  <RiskBadge level={a.riskLevel} />
                </button>
              ))}
            </div>
          )}
        </Card>
      </div> */}

      {/* <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {RECENT_TASKS.map((task) => {
          const tone = taskStatusTone[task.status]
          return (
            <Card key={task.id} interactive onClick={() => navigate(ROUTES.paymentRequests)}>
              <div className="mb-3 flex items-start justify-between gap-3">
                <p className="text-body font-medium text-ink">{task.title}</p>
                <Badge tone={tone} dot>
                  {task.status}
                </Badge>
              </div>
              <div className="flex items-center justify-between text-caption text-ink-faint">
                <span className="flex items-center gap-1">
                  <Icon name="bolt" size={14} /> {task.detail}
                </span>
                {task.risk && <RiskBadge level={task.risk} />}
              </div>
            </Card>
          )
        })}
      </div> */}
    </AppShell>
  )
}
