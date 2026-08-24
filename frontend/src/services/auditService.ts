import { auditEntries } from '@/data/governance'
import { fixture } from './api'
import type { AuditEntry } from '@/types'

export async function fetchAuditLog(): Promise<AuditEntry[]> {
  return fixture([...auditEntries])
}
