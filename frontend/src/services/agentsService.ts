import { agents, agentLog } from '@/data/agents'
import { fixture } from './api'
import type { Agent, AgentLogEntry } from '@/types'

export async function fetchAgents(): Promise<Agent[]> {
  return fixture([...agents])
}

export async function fetchAgentLog(agentId: string): Promise<AgentLogEntry[]> {
  return fixture(agentLog.filter((l) => l.agentId === agentId))
}
