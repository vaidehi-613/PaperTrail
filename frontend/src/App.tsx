import { useState, useMemo } from 'react'
import { sendChat, uploadPaper } from './api'
import { ChatThread } from './components/ChatThread'
import { CitationsPanel } from './components/CitationsPanel'
import { InputBar } from './components/InputBar'
import { PaperChip } from './components/PaperChip'
import { Sidebar } from './components/Sidebar'
import './index.css'
import type { Chat, Message, ScholarResult, VerificationResult } from './types'

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
      const { answer, sources, scholar_results, verifications } = await sendChat(activePaperId, text, activePaperName ?? "")
      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: answer,
        sources,
        scholar_results,
        verifications,
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

  // Extract citing papers from messages with verifications
  const citations = useMemo(() => {
    const citationsMap = new Map<string, { paper: ScholarResult; verification: VerificationResult | null }>()

    for (const msg of messages) {
      if (msg.role === 'assistant' && msg.scholar_results) {
        for (const paper of msg.scholar_results) {
          const verification = msg.verifications?.find((v) => v.title === paper.title) || null
          citationsMap.set(paper.title, { paper, verification })
        }
      }
    }

    return Array.from(citationsMap.values())
  }, [messages])

  // STATE B: Show panel if the latest assistant message has scholar_results
  const showPanel = useMemo(() => {
    const lastAssistant = [...messages].reverse().find(m => m.role === 'assistant')
    const hasResults = (lastAssistant?.scholar_results?.length ?? 0) > 0
    console.log('🔍 Panel visibility check:', {
      messageCount: messages.length,
      lastAssistantId: lastAssistant?.id,
      scholarCount: lastAssistant?.scholar_results?.length,
      showPanel: hasResults,
      scholarResults: lastAssistant?.scholar_results
    })
    return hasResults
  }, [messages])

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--page-bg)' }}>
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

      <main className={`flex flex-1 flex-col overflow-hidden ${showPanel ? 'chat-narrow' : 'chat-full'}`}>
        {/* Header */}
        <header
          className="flex items-center gap-3 border-b px-6 py-3"
          style={{ borderColor: 'var(--border-1)', background: 'var(--surface-white)' }}
        >
          <PaperChip filename={activePaperName} />
          {!activePaperName && (
            <span className="text-sm" style={{ color: 'var(--muted-text)' }}>No paper loaded — upload one to begin</span>
          )}
          {isLoading && (
            <span className="ml-auto text-xs animate-pulse" style={{ color: 'var(--muted-text)' }}>Processing…</span>
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

      {/* Citations panel - only visible in STATE B */}
      {showPanel && <CitationsPanel citations={citations} />}
    </div>
  )
}
