/**
 * The one place an HTTP call to the backend is made.
 *
 * There used to be fifteen hand-written copies of
 * `fetch` → `if (!response.ok) throw` → `response.json()` spread over eight
 * service files. The only thing that varied was the error message, and it
 * varied inconsistently: some threw `Error` and some `ApiError`, some included
 * the response body and some discarded it, and two spelled out the
 * operator-credential case by hand while the rest reported a bare 403.
 *
 * That string is what the pages render in `ErrorState`, so a failure read
 * differently depending on which screen you were on. One helper makes every
 * failure legible the same way, and means the sixteenth call site cannot
 * forget the `.ok` check.
 */

import { API_BASE_URL } from '@/config'

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status = 0) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function describe(response: Response, path: string): Promise<string> {
  // The control plane rejects agent and anonymous callers with 401/403. That
  // is a configuration answer, not a server fault, so say what to do about it.
  if (response.status === 401 || response.status === 403) {
    return 'Operator credential required. Set VITE_OPERATOR_TOKEN to match the backend’s AEGIS_OPERATOR_TOKEN.'
  }

  const body = await response.text().catch(() => '')
  const detail = body.trim().slice(0, 300)

  return detail
    ? `${path} failed (${response.status}): ${detail}`
    : `${path} failed (${response.status}).`
}

/**
 * GET/POST a backend route and parse the JSON body. `path` is relative to
 * API_BASE_URL, so no service needs to know the host.
 */
export async function requestJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  let response: Response

  try {
    response = await fetch(`${API_BASE_URL}${path}`, init)
  } catch {
    // fetch only rejects when the request never reached the server — a wrong
    // API URL, CORS, or the backend being down. Naming the URL turns the
    // browser's opaque "Failed to fetch" into something actionable.
    throw new ApiError(`Could not reach the backend at ${API_BASE_URL}. Is it running?`)
  }

  if (!response.ok) {
    throw new ApiError(await describe(response, path), response.status)
  }

  return response.json() as Promise<T>
}

/**
 * Resolve with a value after a delay. Used only by the disconnected login
 * flow to fake a round-trip — see the "dormant on purpose" section of
 * AGENTS.md before touching that path.
 */
export function delay<T>(value: T, ms = 450): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms))
}

/**
 * Hand back fixture data as a Promise, so the fixture-backed screens
 * (Incident Center, Audit Logs, Approval Center — see MOCK_BACKED_ROUTES)
 * have the same async shape as the live ones.
 *
 * This was `withFlakiness`, which took a failure `rate` and threw at random so
 * error states were reachable by hand. Every one of its seven callers used the
 * default rate of 0, making `Math.random() < 0` — and the throw behind it —
 * unreachable for the life of the repo. Turning it on would have meant editing
 * all seven call sites anyway, since the rate was per-call rather than global.
 * The artificial 450ms went with it: it made the fixture screens feel slower
 * than the live ones for no reason.
 */
export function fixture<T>(value: T): Promise<T> {
  return Promise.resolve(value)
}
