export type Source = {
  id: string
  content: string
  section: string | null
  page: number | null
  is_table: boolean
  is_figure: boolean
  similarity: number
}

export type ScholarResult = {
  title: string
  authors: string[]
  year: number | null
  abstract: string | null
  doi: string | null
  url: string | null
}

export type VerificationResult = {
  title: string
  status: 'verified' | 'flagged' | 'not_found' | 'retracted'
  doi: string | null
  url: string | null
  note: string | null
}

export type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  scholar_results?: ScholarResult[]
  verifications?: VerificationResult[]
}

export type Chat = {
  id: string
  title: string
  paper_name: string
  created_at: string
}
