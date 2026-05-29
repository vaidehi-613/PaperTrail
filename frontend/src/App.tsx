import { useState } from 'react'
import { sendChat, uploadPaper } from './api'
import { ChatThread } from './components/ChatThread'
import { InputBar } from './components/InputBar'
import { PaperChip } from './components/PaperChip'
import { Sidebar } from './components/Sidebar'
import './index.css'
import type { Chat, Message } from './types'

const MOCK_CHATS: Chat[] = [
  {
    id: '1',
    title: 'What is the main contribution?',
    paper_name: 'attention_is_all_you_need.pdf',
    created_at: new Date().toISOString(),
  },
  {
    id: '2',
    title: 'Explain the results table',
    paper_name: 'bert_paper.pdf',
    created_at: new Date(Date.now() - 86_400_000).toISOString(),
  },
  {
    id: '3',
    title: 'How does retrieval work?',
    paper_name: 'rag_paper.pdf',
    created_at: new Date(Date.now() - 3 * 86_400_000).toISOString(),
  },
]

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [activePaperId, setActivePaperId] = useState<string | null>(null)
  const [activePaperName, setActivePaperName] = useState<string | null>(null)
  const [activeChatId, setActiveChatId] = useState<string | null>(null)

  async function handleSend() {
    const text = input.trim()
    if (!text || isLoading) return
    if (!activePaperId) {
      alert('Please upload a paper first.')
      return
    }

    const userMsg: Message = { id: crypto.randomUUID(), role: 'user', content: text }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsLoading(true)

    try {
      const { answer, sources } = await sendChat(activePaperId, text)
      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: answer,
        sources,
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      const errMsg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: 'Something went wrong. Please try again.',
      }
      setMessages((prev) => [...prev, errMsg])
    } finally {
      setIsLoading(false)
    }
  }

  async function handleFileSelect(file: File) {
    setIsLoading(true)
    try {
      const { paper_id, chunk_count } = await uploadPaper(file)
      setActivePaperId(paper_id)
      setActivePaperName(file.name)
      setMessages([])
      console.info(`Uploaded ${file.name}: ${chunk_count} chunks (paper_id=${paper_id})`)
    } catch (err) {
      alert('Failed to upload PDF. Make sure the backend is running.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--surface-1)' }}>
      <Sidebar
        chats={MOCK_CHATS}
        activeChatId={activeChatId}
        onNew={() => {
          setMessages([])
          setActivePaperId(null)
          setActivePaperName(null)
          setActiveChatId(null)
        }}
        onSelect={(id) => setActiveChatId(id)}
      />

      <main className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header
          className="flex items-center gap-3 border-b px-6 py-3"
          style={{ borderColor: '#E5E3DE' }}
        >
          <PaperChip filename={activePaperName} />
          {!activePaperName && (
            <span className="text-sm text-gray-400">No paper loaded — upload one to begin</span>
          )}
          {isLoading && (
            <span className="ml-auto text-xs text-gray-400 animate-pulse">Processing…</span>
          )}
        </header>

        {/* Chat thread */}
        <ChatThread messages={messages} />

        {/* Input bar */}
        <InputBar
          value={input}
          onChange={setInput}
          onSend={handleSend}
          onFileSelect={handleFileSelect}
          disabled={isLoading}
        />
      </main>
    </div>
  )
}
