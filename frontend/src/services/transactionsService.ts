import type { Transaction } from '@/types'
import { API_BASE_URL } from '@/config'

export async function fetchTransactions(): Promise<Transaction[]> {
  const response = await fetch(`${API_BASE_URL}/transactions`)

  if (!response.ok) {
    const text = await response.text()
    throw new Error(`Failed to fetch transactions: ${text}`)
  }

  const data = await response.json()

  return data.map((r: any) => ({
    id: r.id,
    request_id: r.request_id,
    payment_id: r.payment_id,

    task: r.task,
    provider: r.provider,

    amount: Number(r.amount ?? 0),
    currency: r.currency ?? 'USDC',
    network: r.network ?? 'Base Sepolia',

    status: r.status,

    transaction_hash: r.transaction_hash ?? null,

    created_at: r.created_at,
    settled_at: r.settled_at ?? null,
  }))
}


export async function fetchTransaction(
  id: string
): Promise<Transaction | undefined> {
  const transactions = await fetchTransactions()

  return transactions.find(
    (transaction) => transaction.id === id
  )
}