import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { resolveApiUrl } from '../utils/resolveApiUrl'
import { legalDocumentLanguage, t as translate } from '../i18n'
import './LegalPage.css'

interface LegalPageContent {
  title: string
  content: string
}

function renderMarkdownSimple(text: string): JSX.Element[] {
  const lines = text.split('\n')
  const elements: JSX.Element[] = []
  let listItems: string[] = []

  const flushList = (key: string) => {
    if (listItems.length === 0) return
    elements.push(
      <ul key={key}>
        {listItems.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    )
    listItems = []
  }

  lines.forEach((line, idx) => {
    const trimmed = line.trim()
    if (trimmed.startsWith('## ')) {
      flushList(`list-${idx}`)
      elements.push(<h2 key={`h2-${idx}`}>{trimmed.slice(3)}</h2>)
      return
    }
    if (trimmed.startsWith('### ')) {
      flushList(`list-${idx}`)
      elements.push(<h3 key={`h3-${idx}`}>{trimmed.slice(4)}</h3>)
      return
    }
    if (trimmed.startsWith('- ')) {
      listItems.push(trimmed.slice(2))
      return
    }
    flushList(`list-${idx}`)
    if (trimmed === '---') {
      elements.push(<hr key={`hr-${idx}`} />)
      return
    }
    if (trimmed === '') {
      return
    }
    if (trimmed.startsWith('_') && trimmed.endsWith('_')) {
      elements.push(
        <p key={`em-${idx}`} className="legal-page__muted">
          {trimmed.slice(1, -1)}
        </p>
      )
      return
    }
    elements.push(<p key={`p-${idx}`}>{trimmed}</p>)
  })
  flushList('list-end')
  return elements
}

export default function LegalPage() {
  const { slug } = useParams<{ slug: string }>()
  const [page, setPage] = useState<LegalPageContent | null>(null)
  const [legalLocale, setLegalLocale] = useState<string>('de')
  const [enabled, setEnabled] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(resolveApiUrl('/api/legal'))
        if (!res.ok) throw new Error('load_failed')
        const data = await res.json()
        if (cancelled) return
        setEnabled(Boolean(data.enabled))
        setLegalLocale(data.locale || 'de')
        const pages = data.pages || {}
        const content = pages[slug || '']
        if (!content) {
          setPage(null)
          setError('not_found')
        } else {
          setPage(content)
        }
      } catch {
        if (!cancelled) setError('load_failed')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [slug])

  const legalLang = legalDocumentLanguage(legalLocale)
  const legalT = (key: string) => translate(key, undefined, legalLang)

  if (loading) {
    return (
      <div className="legal-page shell-content">
        <div className="card legal-page__card">{legalT('legal.pageLoading')}</div>
      </div>
    )
  }

  if (!enabled) {
    return (
      <div className="legal-page shell-content">
        <div className="card legal-page__card">
          <h1>{legalT('legal.pageDisabledTitle')}</h1>
          <p>{legalT('legal.pageDisabledBody')}</p>
          <Link to="/">{legalT('legal.backHome')}</Link>
        </div>
      </div>
    )
  }

  if (error || !page) {
    return (
      <div className="legal-page shell-content">
        <div className="card legal-page__card">
          <h1>{error === 'not_found' ? legalT('legal.pageNotFound') : legalT('legal.pageLoadFailed')}</h1>
          <Link to="/">{legalT('legal.backHome')}</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="legal-page shell-content">
      <article className="card legal-page__card">
        <h1>{page.title}</h1>
        <div className="legal-page__body">{renderMarkdownSimple(page.content)}</div>
        <p className="legal-page__back">
          <Link to="/">{legalT('legal.backHome')}</Link>
        </p>
      </article>
    </div>
  )
}
