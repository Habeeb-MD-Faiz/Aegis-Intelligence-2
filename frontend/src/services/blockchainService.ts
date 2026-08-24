import { requestJson } from './api'

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


export function fetchBlockchain(): Promise<BlockchainBlock[]> {
  return requestJson<BlockchainBlock[]>('/blockchain')
}


export function fetchBlockchainStats(): Promise<BlockchainStats> {
  return requestJson<BlockchainStats>('/blockchain/stats')
}


export function verifyBlockchain(): Promise<BlockchainVerification> {
  return requestJson<BlockchainVerification>('/blockchain/verify')
}
