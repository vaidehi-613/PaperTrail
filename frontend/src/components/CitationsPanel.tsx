import type { ScholarResult, VerificationResult } from '../types'

type CitationWithVerification = {
  paper: ScholarResult
  verification: VerificationResult | null
}

type CitationsPanelProps = {
  citations: CitationWithVerification[]
}

export function CitationsPanel({ citations }: CitationsPanelProps) {
  console.log('🎨 CitationsPanel rendering with', citations.length, 'citations')

  // Count verification statuses
  const verified = citations.filter(c => c.verification?.status === 'verified').length
  const notFound = citations.filter(c => c.verification?.status === 'not_found').length

  return (
    <aside
      className="flex flex-col border-l overflow-hidden panel-enter-active"
      style={{ width: '244px', borderColor: 'var(--border-1)', background: 'var(--surface-white)' }}
    >
      <header className="border-b px-3 py-2.5" style={{ borderColor: 'var(--border-1)' }}>
        <h2 className="text-sm font-semibold mb-1" style={{ color: 'var(--assistant-text)' }}>
          Related Work
        </h2>
        <p className="text-xs leading-tight" style={{ color: 'var(--muted-text)' }}>
          {citations.length} papers found · {verified} verified{notFound > 0 && `, ${notFound} not found`}
        </p>
      </header>

      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
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
      className="relative flex items-start gap-2.5 border transition-shadow hover:shadow-md"
      style={{
        borderColor: 'var(--border-1)',
        background: 'var(--card-bg)',
        borderRadius: '12px',
        padding: '10px 12px',
        cursor: url ? 'pointer' : 'default'
      }}
    >
      {/* Left: Paper info */}
      <div className="flex-1 min-w-0">
        {/* Title - bold, 2 lines max, right padding for badge */}
        <h3
          className="font-semibold leading-snug line-clamp-2 mb-1"
          style={{ color: 'var(--assistant-text)', fontSize: '13px', paddingRight: badge ? '24px' : '0' }}
        >
          {paper.title}
        </h3>

        {/* Authors · Year - muted grey */}
        <p className="text-xs" style={{ color: 'var(--muted-text-dark)' }}>
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
        bg: 'var(--verified)',
        title: 'Verified: DOI/identifier resolves in OpenAlex/Crossref'
      }
    case 'flagged':
      return {
        icon: '⚠',
        bg: '#F59E0B', // Amber (not in brand colors)
        title: 'Flagged: Paper exists but claim may be contradicted'
      }
    case 'not_found':
      return {
        icon: '✗',
        bg: 'var(--not-found)',
        title: 'Not found: Paper does not resolve in OpenAlex'
      }
    case 'retracted':
      return {
        icon: '⚠',
        bg: 'var(--not-found)',
        title: 'Retracted: Paper has been retracted'
      }
  }
}
