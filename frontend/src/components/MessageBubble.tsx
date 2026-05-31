import type { Message, Source } from '../types'

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
  // Format: "Section Name, p.X" or just "p.X" if no section
  const label =
    source.section && source.page
      ? `${source.section}, p.${source.page}`
      : source.section ?? (source.page ? `p.${source.page}` : 'Source')

  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs"
      style={{ background: 'var(--chip-bg)', color: 'var(--chip-text)' }}
      title={source.content}
    >
      {/* Prefix badges for figures/tables */}
      {source.is_table && (
        <span className="rounded px-1.5 py-0.5 font-medium text-xs" style={{ background: 'var(--accent-tint-bg)', color: 'var(--accent-tint-text)' }}>
          table
        </span>
      )}
      {source.is_figure && (
        <span className="rounded px-1.5 py-0.5 font-medium text-xs" style={{ background: 'var(--accent-tint-bg)', color: 'var(--accent-tint-text)' }}>
          fig
        </span>
      )}
      <span>{label}</span>
    </span>
  )
}

type Props = { message: Message }

export function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex max-w-[70%] flex-col gap-2 ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Answer bubble */}
        <div
          className="rounded-2xl px-4 py-2.5 text-sm leading-relaxed"
          style={
            isUser
              ? { background: 'var(--accent)', color: 'white' }
              : { background: 'var(--assistant-bubble)', color: 'var(--assistant-text)' }
          }
        >
          {message.content}
        </div>

        {/* Source chips - only for assistant messages with sources */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-1">
            {dedupSources(message.sources).map((s) => (
              <SourceChip key={s.id} source={s} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
