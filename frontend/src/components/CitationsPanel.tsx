import type { ScholarResult, VerificationResult } from '../types'

type CitationWithVerification = {
  paper: ScholarResult
  verification: VerificationResult | null
}

type CitationsPanelProps = {
  citations: CitationWithVerification[]
}

export function CitationsPanel({ citations }: CitationsPanelProps) {
  if (citations.length === 0) {
    return (
      <aside
        className="flex w-80 flex-col border-l"
        style={{ borderColor: '#E5E3DE', background: 'var(--surface-0)' }}
      >
        <header className="border-b px-4 py-3" style={{ borderColor: '#E5E3DE' }}>
          <h2 className="text-sm font-semibold" style={{ color: '#3E3C38' }}>
            Related Work
          </h2>
        </header>
        <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-gray-400">
          Ask "What came after this paper?" to discover citing papers.
        </div>
      </aside>
    )
  }

  return (
    <aside
      className="flex w-80 flex-col border-l overflow-hidden"
      style={{ borderColor: '#E5E3DE', background: 'var(--surface-0)' }}
    >
      <header className="border-b px-4 py-3" style={{ borderColor: '#E5E3DE' }}>
        <h2 className="text-sm font-semibold" style={{ color: '#3E3C38' }}>
          Related Work ({citations.length})
        </h2>
      </header>

      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {citations.map((item, idx) => (
          <CitationCard key={idx} {...item} />
        ))}
      </div>
    </aside>
  )
}

function CitationCard({ paper, verification }: CitationWithVerification) {
  const badge = verification ? getCircularBadge(verification.status) : null
  const url = paper.url || (paper.doi ? `https://doi.org/${paper.doi}` : null)

  // Format authors: "First Author, Second Author et al."
  const authorsText = paper.authors.length > 0
    ? paper.authors.slice(0, 2).join(', ') + (paper.authors.length > 2 ? ' et al.' : '')
    : 'Unknown authors'

  const CardContent = (
    <div
      className="relative flex items-start gap-3 rounded-xl border p-3.5 transition-shadow hover:shadow-md"
      style={{
        borderColor: '#E5E3DE',
        background: '#FFFFFF',
        cursor: url ? 'pointer' : 'default'
      }}
    >
      {/* Left: Paper info */}
      <div className="flex-1 min-w-0">
        {/* Title - bold, 2 lines max */}
        <h3
          className="font-semibold leading-snug line-clamp-2 mb-1.5"
          style={{ color: '#1a1a1a', fontSize: '14px' }}
        >
          {paper.title}
        </h3>

        {/* Authors · Year - muted grey */}
        <p className="text-xs text-gray-500">
          {authorsText}
          {paper.year && ` · ${paper.year}`}
        </p>
      </div>

      {/* Right: Circular badge - vertically centered */}
      {badge && (
        <div className="flex items-center shrink-0" style={{ height: '100%' }}>
          <div
            className="flex items-center justify-center rounded-full"
            style={{
              width: '20px',
              height: '20px',
              background: badge.bg,
            }}
            title={badge.title}
          >
            <span className="text-white font-bold" style={{ fontSize: '11px' }}>
              {badge.icon}
            </span>
          </div>
        </div>
      )}
    </div>
  )

  // If URL exists, make the whole card clickable
  if (url) {
    return (
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="block no-underline"
      >
        {CardContent}
      </a>
    )
  }

  return CardContent
}

function getCircularBadge(status: VerificationResult['status']) {
  switch (status) {
    case 'verified':
      return {
        icon: '✓',
        bg: '#10B981', // Green
        title: 'Verified: DOI/identifier resolves in OpenAlex/Crossref'
      }
    case 'flagged':
      return {
        icon: '⚠',
        bg: '#F59E0B', // Amber
        title: 'Flagged: Paper exists but claim may be contradicted'
      }
    case 'not_found':
      return {
        icon: '✗',
        bg: '#EF4444', // Red
        title: 'Not found: Paper does not resolve in OpenAlex'
      }
    case 'retracted':
      return {
        icon: '⚠',
        bg: '#EF4444', // Red
        title: 'Retracted: Paper has been retracted'
      }
  }
}
