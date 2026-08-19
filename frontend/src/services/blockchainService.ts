import { blockchainNodes, blocks } from '@/data/governance'
import { withFlakiness } from './api'
import type { BlockchainNode, BlockEntry } from '@/types'
import { API_BASE_URL } from '@/config'

export async function fetchBlockchainNodes(): Promise<BlockchainNode[]> {
  return withFlakiness([...blockchainNodes])
}

export async function fetchBlocks(): Promise<BlockEntry[]> {
  return withFlakiness([...blocks])
}

export interface BlockchainBlock {
  blockNumber: number
  requestId: string
  task: string
  provider: string
  amount: number
  category: string | null
  decision: string
  decisionType: string | null
  decisionBy: string | null
  reason: string | null
  timestamp: string
  previousHash: string
  hash: string
}

export interface BlockchainStats {
  totalBlocks: number
  chainStatus: "verified" | "compromised"
  verifiedBlocks: number
  tamperedBlocks: number
  latestBlock: BlockchainBlock | null
}

export interface BlockchainVerification {
  valid: boolean
  message: string
  blocks: number
  verifiedBlocks: number
  tamperedBlocks: number
  tamperedBlock?: number
}


export async function fetchBlockchain(): Promise<BlockchainBlock[]> {
  const response = await fetch(`${API_BASE_URL}/blockchain`)

  if (!response.ok) {
    throw new Error("Failed to fetch blockchain")
  }

  return response.json()
}


export async function fetchBlockchainStats(): Promise<BlockchainStats> {
  const response = await fetch(`${API_BASE_URL}/blockchain/stats`)

  if (!response.ok) {
    throw new Error("Failed to fetch blockchain stats")
  }

  return response.json()
}


export async function verifyBlockchain(): Promise<BlockchainVerification> {
  const response = await fetch(`${API_BASE_URL}/blockchain/verify`)

  if (!response.ok) {
    throw new Error("Failed to verify blockchain")
  }

  return response.json()
}


export async function fetchBlockchainBlock(
  blockNumber: number
): Promise<BlockchainBlock> {
  const response = await fetch(
    `${API_BASE_URL}/blockchain/${blockNumber}`
  )

  if (!response.ok) {
    throw new Error("Failed to fetch blockchain block")
  }

  return response.json()
}