import { incidents } from '@/data/governance'
import { fixture } from './api'
import type { Incident } from '@/types'

export async function fetchIncidents(): Promise<Incident[]> {
  return fixture([...incidents])
}
