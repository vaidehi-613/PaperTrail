import type { Message, ScholarResult, Source, VerificationResult } from '../types'

function dedupSources(sources: Source[]): Source[] {
  const seen = new Set<string>()
  return sources.filter((s) => {
    const key = `${s.section ?? ''}|${s.page ?? ''}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function SourceChip({ source }: { source: Source }) {
  const label =
    source.section && source.page
      ? `${source.section}, p.${source.page}`
      : source.section ?? (source.page ? `p.${source.page}` : 'Source')

  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium"
      style={{ background: 'var(--surface-2)', color: '#555' }}
      title={source.content}
    >
      {source.is_table && (
        <span className="rounded bg-blue-100 px-1 text-blue-700">table</span>
      )}
      {source.is_figure && (
        <span className="rounded bg-purple-100 px-1 text-purple-700">fig</span>
      )}
      {label}
    </span>
  )
}

function ScholarCard({ result, verification }: { result: ScholarResult; verification?: VerificationResult }) {
  const authors = result.authors.slice(0, 2).join(', ') +
    (result.authors.length > 2 ? ' et al.' : '')

  const badge = verification ? (
    <span
      className="absolute top-2 right-2 flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold"
      style={{
        background: verification.status === 'verified' ? '#10b981' :
                    verification.status === 'flagged' ? '#f59e0b' :
                    '#ef4444',
        color: 'white'
      }}
      title={verification.note || verification.status}
    >
      {verification.status === 'verified' ? '✓' :
       verification.status === 'flagged' ? '⚠' : '✗'}
    </span>
  ) : null

  const inner = (
    <div
      className="relative rounded-lg border px-3 py-2 text-xs transition-colors hover:bg-white"
      style={{ borderColor: '#E5E3DE' }}
    >
      {badge}
      <p className="font-medium text-gray-800 line-clamp-1 pr-6">{result.title}</p>
      <p className="mt-0.5 text-gray-500">
        {authors}{result.year ? ` · ${result.year}` : ''}
      </p>
    </div>
  )

  return result.url ? (
    <a href={result.url} target="_blank" rel="noopener noreferrer" className="block">
      {inner}
    </a>
  ) : inner
}

type Props = { message: Message }

export function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'

  // Build a lookup map for verifications by title
  const verificationMap = new Map<string, VerificationResult>()
  if (message.verifications) {
    for (const v of message.verifications) {
      verificationMap.set(v.title.toLowerCase(), v)
    }
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex max-w-[70%] flex-col gap-2 ${isUser ? 'items-end' : 'items-start'}`}>
        <div
          className="rounded-2xl px-4 py-2.5 text-sm leading-relaxed"
          style={
            isUser
              ? { background: 'var(--accent)', color: 'white' }
              : { background: 'var(--surface-2)', color: '#1a1a1a' }
          }
        >
          {message.content}
        </div>

        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-1">
            {dedupSources(message.sources).map((s) => (
              <SourceChip key={s.id} source={s} />
            ))}
          </div>
        )}

        {!isUser && message.scholar_results && message.scholar_results.length > 0 && (
          <div className="flex w-full flex-col gap-1.5 px-1">
            <p className="text-xs font-medium text-gray-400">Related papers</p>
            {message.scholar_results.map((r, i) => (
              <ScholarCard
                key={i}
                result={r}
                verification={verificationMap.get(r.title.toLowerCase())}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
