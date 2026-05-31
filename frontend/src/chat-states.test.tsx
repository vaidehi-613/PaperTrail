/**
 * Tests for two-state chat UI:
 * - STATE A: Normal content questions (retrieve_paper) → citation chips, no rail, full-width
 * - STATE B: Scholar search questions → Related Work rail with badged cards + summary line
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, test } from 'vitest'
import type { Message } from './types'
import { MessageBubble } from './components/MessageBubble'
import { CitationsPanel } from './components/CitationsPanel'

describe('Chat UI States', () => {
  describe('STATE A: Normal content question', () => {
    test('renders citation chips with section + page', () => {
      const message: Message = {
        id: '1',
        role: 'assistant',
        content: 'The Transformer uses scaled dot-product attention [Section 3.2.1, p.4].',
        sources: [
          {
            id: 'src1',
            content: 'Scaled dot-product attention...',
            section: '3.2.1 Scaled Dot-Product Attention',
            page: 4,
            is_table: false,
            is_figure: false,
          },
          {
            id: 'src2',
            content: 'Multi-head attention...',
            section: '3.2.2 Multi-Head Attention',
            page: 5,
            is_table: false,
            is_figure: false,
          },
        ],
      }

      render(<MessageBubble message={message} />)

      // Assistant bubble with warm grey background
      expect(screen.getByText(/The Transformer uses/)).toBeInTheDocument()

      // Citation chips
      expect(screen.getByText(/3.2.1 Scaled Dot-Product Attention, p.4/)).toBeInTheDocument()
      expect(screen.getByText(/3.2.2 Multi-Head Attention, p.5/)).toBeInTheDocument()
    })

    test('renders fig/table tags inside chips with purple background', () => {
      const message: Message = {
        id: '2',
        role: 'assistant',
        content: 'Table 2 shows the results [Table 2, p.7]. Figure 1 illustrates the architecture [Figure 1, p.3].',
        sources: [
          {
            id: 'src1',
            content: 'Results table...',
            section: 'Table 2',
            page: 7,
            is_table: true,
            is_figure: false,
          },
          {
            id: 'src2',
            content: 'Architecture diagram...',
            section: 'Figure 1',
            page: 3,
            is_table: false,
            is_figure: true,
          },
        ],
      }

      render(<MessageBubble message={message} />)

      // Table tag
      expect(screen.getByText('table')).toBeInTheDocument()

      // Figure tag
      expect(screen.getByText('fig')).toBeInTheDocument()
    })

    test('dedups sources by section + page', () => {
      const message: Message = {
        id: '3',
        role: 'assistant',
        content: 'Multiple chunks from same section.',
        sources: [
          { id: 'src1', content: 'Chunk 1', section: 'Introduction', page: 1, is_table: false, is_figure: false },
          { id: 'src2', content: 'Chunk 2', section: 'Introduction', page: 1, is_table: false, is_figure: false },
          { id: 'src3', content: 'Chunk 3', section: 'Methods', page: 3, is_table: false, is_figure: false },
        ],
      }

      const { container } = render(<MessageBubble message={message} />)

      // Should render only 2 chips (deduped by section+page)
      const chips = container.querySelectorAll('[title]')
      expect(chips.length).toBe(2)
    })
  })

  describe('STATE B: Scholar search question', () => {
    test('renders Related Work rail with summary line', () => {
      const citations = [
        {
          paper: {
            title: 'An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale',
            authors: ['Alexey Dosovitskiy', 'Lucas Beyer', 'Alexander Kolesnikov'],
            year: 2020,
            abstract: '',
            doi: '10.48550/arXiv.2010.11929',
            url: 'https://arxiv.org/abs/2010.11929',
          },
          verification: {
            title: 'An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale',
            status: 'verified' as const,
            reason: 'Paper exists in OpenAlex',
          },
        },
        {
          paper: {
            title: 'Highly accurate protein structure prediction with AlphaFold',
            authors: ['John Jumper', 'Richard Evans'],
            year: 2021,
            abstract: '',
            doi: '10.1038/s41586-021-03819-2',
            url: 'https://doi.org/10.1038/s41586-021-03819-2',
          },
          verification: {
            title: 'Highly accurate protein structure prediction with AlphaFold',
            status: 'verified' as const,
            reason: 'Paper exists in OpenAlex',
          },
        },
        {
          paper: {
            title: 'Fake Paper That Does Not Exist',
            authors: ['Unknown Author'],
            year: 2023,
            abstract: '',
            doi: null,
            url: null,
          },
          verification: {
            title: 'Fake Paper That Does Not Exist',
            status: 'not_found' as const,
            reason: 'Paper does not resolve in OpenAlex',
          },
        },
      ]

      render(<CitationsPanel citations={citations} />)

      // Header
      expect(screen.getByText('Related Work')).toBeInTheDocument()

      // Summary line: "3 papers found · 2 verified, 1 not found"
      expect(screen.getByText(/3 papers found · 2 verified, 1 not found/)).toBeInTheDocument()

      // Paper titles
      expect(screen.getByText(/An Image is Worth 16x16 Words/)).toBeInTheDocument()
      expect(screen.getByText(/Highly accurate protein structure/)).toBeInTheDocument()
      expect(screen.getByText(/Fake Paper That Does Not Exist/)).toBeInTheDocument()

      // Authors + year (check using text content matcher)
      expect(screen.getByText((content, element) => {
        return element?.textContent === 'Alexey Dosovitskiy, Lucas Beyer et al. · 2020'
      })).toBeInTheDocument()
      expect(screen.getByText((content, element) => {
        return element?.textContent === 'John Jumper, Richard Evans · 2021'
      })).toBeInTheDocument()
    })

    test('cards link to real DOI/URL', () => {
      const citations = [
        {
          paper: {
            title: 'Test Paper with DOI',
            authors: ['Author A'],
            year: 2020,
            abstract: '',
            doi: '10.1000/test123',
            url: null,
          },
          verification: { title: 'Test Paper with DOI', status: 'verified' as const, reason: 'OK' },
        },
        {
          paper: {
            title: 'Test Paper with URL',
            authors: ['Author B'],
            year: 2021,
            abstract: '',
            doi: null,
            url: 'https://example.com/paper',
          },
          verification: { title: 'Test Paper with URL', status: 'verified' as const, reason: 'OK' },
        },
      ]

      const { container } = render(<CitationsPanel citations={citations} />)

      // Find all links
      const links = container.querySelectorAll('a[href]')
      expect(links.length).toBe(2)

      // Check DOI link
      const doiLink = Array.from(links).find(link => link.getAttribute('href') === 'https://doi.org/10.1000/test123')
      expect(doiLink).toBeTruthy()
      expect(doiLink?.getAttribute('target')).toBe('_blank')

      // Check URL link
      const urlLink = Array.from(links).find(link => link.getAttribute('href') === 'https://example.com/paper')
      expect(urlLink).toBeTruthy()
      expect(urlLink?.getAttribute('target')).toBe('_blank')
    })

    test('renders circular badges with correct colors', () => {
      const citations = [
        {
          paper: { title: 'Verified Paper', authors: ['A'], year: 2020, abstract: '', doi: '10.1000/v', url: null },
          verification: { title: 'Verified Paper', status: 'verified' as const, reason: 'OK' },
        },
        {
          paper: { title: 'Not Found Paper', authors: ['B'], year: 2021, abstract: '', doi: null, url: null },
          verification: { title: 'Not Found Paper', status: 'not_found' as const, reason: 'Missing' },
        },
        {
          paper: { title: 'Flagged Paper', authors: ['C'], year: 2022, abstract: '', doi: null, url: null },
          verification: { title: 'Flagged Paper', status: 'flagged' as const, reason: 'Contradicted' },
        },
      ]

      const { container } = render(<CitationsPanel citations={citations} />)

      // Find badges (they're divs with rounded-full class)
      const badges = container.querySelectorAll('.rounded-full')
      expect(badges.length).toBe(3)

      // Check that badges have the correct symbols
      const badgeTexts = Array.from(badges).map(b => b.textContent)
      expect(badgeTexts).toContain('✓') // verified
      expect(badgeTexts).toContain('✗') // not found
      expect(badgeTexts).toContain('⚠') // flagged
    })

    test('summary line shows only verified count when no not_found papers', () => {
      const citations = [
        {
          paper: { title: 'Paper 1', authors: ['A'], year: 2020, abstract: '', doi: '10.1000/1', url: null },
          verification: { title: 'Paper 1', status: 'verified' as const, reason: 'OK' },
        },
        {
          paper: { title: 'Paper 2', authors: ['B'], year: 2021, abstract: '', doi: '10.1000/2', url: null },
          verification: { title: 'Paper 2', status: 'verified' as const, reason: 'OK' },
        },
      ]

      render(<CitationsPanel citations={citations} />)

      // Should NOT include "not found" in summary
      expect(screen.getByText(/2 papers found · 2 verified$/)).toBeInTheDocument()
    })
  })
})
