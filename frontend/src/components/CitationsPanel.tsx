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

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {citations.map((item, idx) => (
          <CitationCard key={idx} {...item} />
        ))}
      </div>
    </aside>
  )
}

function CitationCard({ paper, verification }: CitationWithVerification) {
  const badge = verification ? getVerificationBadge(verification.status) : null

  return (
    <article
      className="rounded-lg border p-3 text-sm"
      style={{ borderColor: '#E5E3DE', background: '#FFFFFB' }}
    >
      {/* Title with badge */}
      <div className="mb-2 flex items-start gap-2">
        <h3 className="flex-1 font-semibold leading-tight" style={{ color: '#3E3C38' }}>
          {paper.title}
        </h3>
        {badge && (
          <span
            className="shrink-0 rounded px-1.5 py-0.5 text-xs font-medium"
            style={{ background: badge.bg, color: badge.text }}
          >
            {badge.label}
          </span>
        )}
      </div>

      {/* Authors & Year */}
      <p className="mb-2 text-xs text-gray-500">
        {paper.authors.slice(0, 3).join(', ')}
        {paper.authors.length > 3 && ` +${paper.authors.length - 3}`}
        {paper.year && ` • ${paper.year}`}
      </p>

      {/* Abstract snippet */}
      {paper.abstract && (
        <p className="mb-2 line-clamp-3 text-xs leading-relaxed text-gray-600">
          {paper.abstract}
        </p>
      )}

      {/* Verification note */}
      {verification?.note && (
        <p className="mb-2 text-xs italic text-gray-500">
          {verification.note}
        </p>
      )}

      {/* Link */}
      {(paper.url || paper.doi) && (
        <a
          href={paper.url || `https://doi.org/${paper.doi}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs font-medium hover:underline"
          style={{ color: '#6557D6' }}
        >
          View paper
          <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
      )}
    </article>
  )
}

function getVerificationBadge(status: VerificationResult['status']) {
  switch (status) {
    case 'verified':
      return { label: '✓ Verified', bg: '#D1FAE5', text: '#065F46' }
    case 'flagged':
      return { label: '⚠ Flagged', bg: '#FEF3C7', text: '#92400E' }
    case 'not_found':
      return { label: '✗ Not Found', bg: '#FEE2E2', text: '#991B1B' }
    case 'retracted':
      return { label: '⚠ Retracted', bg: '#FEE2E2', text: '#991B1B' }
  }
}
