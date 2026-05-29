import type { Source } from './types'

export async function uploadPaper(
  file: File,
): Promise<{ paper_id: string; chunk_count: number }> {
  const body = new FormData()
  body.append('file', file)
  const res = await fetch('/papers', { method: 'POST', body })
  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`)
  return res.json()
}

export async function sendChat(
  paper_id: string,
  message: string,
): Promise<{ answer: string; sources: Source[] }> {
  const res = await fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paper_id, message }),
  })
  if (!res.ok) throw new Error(`Chat failed: ${res.statusText}`)
  return res.json()
}
