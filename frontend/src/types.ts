export type Source = {
  id: string
  content: string
  section: string | null
  page: number | null
  is_table: boolean
  is_figure: boolean
  similarity: number
}

export type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
}

export type Chat = {
  id: string
  title: string
  paper_name: string
  created_at: string
}
