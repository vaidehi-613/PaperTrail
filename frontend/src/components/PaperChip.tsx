type Props = { filename: string | null }

export function PaperChip({ filename }: Props) {
  if (!filename) return null

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-medium"
      style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }}
    >
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
        <path
          d="M2 1h6l3 3v8H2V1z"
          stroke="currentColor"
          strokeWidth="1.2"
          strokeLinejoin="round"
        />
        <path d="M8 1v3h3" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
      </svg>
      {filename}
    </span>
  )
}
