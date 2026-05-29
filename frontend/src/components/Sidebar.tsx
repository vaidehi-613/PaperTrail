import type { Chat } from '../types'

type Group = { label: string; chats: Chat[] }

function groupByRecency(chats: Chat[]): Group[] {
  const now = Date.now()
  const DAY = 86_400_000
  const today: Chat[] = []
  const yesterday: Chat[] = []
  const older: Chat[] = []

  for (const chat of chats) {
    const age = now - new Date(chat.created_at).getTime()
    if (age < DAY) today.push(chat)
    else if (age < 2 * DAY) yesterday.push(chat)
    else older.push(chat)
  }

  return [
    ...(today.length ? [{ label: 'Today', chats: today }] : []),
    ...(yesterday.length ? [{ label: 'Yesterday', chats: yesterday }] : []),
    ...(older.length ? [{ label: 'Earlier', chats: older }] : []),
  ]
}

type Props = {
  chats: Chat[]
  activeChatId: string | null
  onNew: () => void
  onSelect: (id: string) => void
}

export function Sidebar({ chats, activeChatId, onNew, onSelect }: Props) {
  const groups = groupByRecency(chats)

  return (
    <aside
      className="flex h-full w-64 shrink-0 flex-col border-r"
      style={{ background: 'var(--surface-2)', borderColor: '#E5E3DE' }}
    >
      {/* Logo + new chat */}
      <div className="p-4">
        <span className="mb-4 block text-base font-semibold" style={{ color: 'var(--accent)' }}>
          PaperTrail
        </span>
        <button
          onClick={onNew}
          className="flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors hover:bg-white"
          style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 1v12M1 7h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          New chat
        </button>
      </div>

      {/* Chat history */}
      <nav className="flex-1 overflow-y-auto px-2 pb-2">
        {groups.map((group) => (
          <div key={group.label} className="mb-3">
            <p className="mb-1 px-2 text-xs font-medium text-gray-400">{group.label}</p>
            {group.chats.map((chat) => {
              const active = chat.id === activeChatId
              return (
                <button
                  key={chat.id}
                  onClick={() => onSelect(chat.id)}
                  className="flex w-full flex-col rounded-md px-2 py-2 text-left text-sm transition-colors hover:bg-white"
                  style={
                    active
                      ? {
                          borderLeft: '3px solid var(--accent)',
                          paddingLeft: '5px',
                          color: 'var(--accent)',
                          background: 'white',
                        }
                      : {}
                  }
                >
                  <span className="truncate font-medium">{chat.title}</span>
                  <span className="truncate text-xs text-gray-400">{chat.paper_name}</span>
                </button>
              )
            })}
          </div>
        ))}
      </nav>

      {/* User chip */}
      <div
        className="flex items-center gap-2 border-t p-3"
        style={{ borderColor: '#E5E3DE' }}
      >
        <div
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white"
          style={{ background: 'var(--accent)' }}
        >
          VP
        </div>
        <div className="min-w-0">
          <p className="truncate text-xs font-medium text-gray-700">Vaidehi Pawar</p>
          <p className="truncate text-xs text-gray-400">pawar.vaidehi613@gmail.com</p>
        </div>
      </div>
    </aside>
  )
}
