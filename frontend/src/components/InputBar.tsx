import { useRef, type KeyboardEvent } from 'react'

type Props = {
  value: string
  onChange: (v: string) => void
  onSend: () => void
  onFileSelect: (file: File) => void
  disabled: boolean
}

export function InputBar({ value, onChange, onSend, onFileSelect, disabled }: Props) {
  const fileRef = useRef<HTMLInputElement>(null)

  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!disabled && value.trim()) onSend()
    }
  }

  return (
    <div
      className="border-t px-4 py-3"
      style={{ background: 'var(--page-bg)', borderColor: 'var(--border-1)' }}
    >
      <div className="flex items-end gap-2 rounded-xl border px-3 py-2" style={{ borderColor: 'var(--border-1)', background: 'var(--surface-white)' }}>
        {/* Attach button */}
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="mb-0.5 shrink-0 transition-colors"
          style={{ color: 'var(--muted-text)' }}
          onMouseEnter={(e) => e.currentTarget.style.color = 'var(--assistant-text)'}
          onMouseLeave={(e) => e.currentTarget.style.color = 'var(--muted-text)'}
          title="Upload PDF"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path
              d="M3 10.5V13.5C3 14.3 3.7 15 4.5 15H13.5C14.3 15 15 14.3 15 13.5V10.5"
              stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"
            />
            <path d="M9 3v8M6 6l3-3 3 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) onFileSelect(f)
            e.target.value = ''
          }}
        />

        {/* Text input */}
        <textarea
          rows={1}
          className="flex-1 resize-none bg-transparent text-sm leading-relaxed outline-none"
          style={{ color: 'var(--assistant-text)' }}
          placeholder="Ask about the paper… (Enter to send, Shift+Enter for newline)"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKey}
          disabled={disabled}
        />

        {/* Send button */}
        <button
          type="button"
          onClick={onSend}
          disabled={disabled || !value.trim()}
          className="mb-0.5 shrink-0 rounded-lg p-1.5 text-white transition-opacity disabled:opacity-40"
          style={{ background: 'var(--accent)' }}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M2 8h12M8 2l6 6-6 6" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>
    </div>
  )
}
