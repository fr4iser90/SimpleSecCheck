import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { resolveApiUrl } from '../utils/resolveApiUrl'
import { useTranslation } from '../i18n'
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
  const { t } = useTranslation()
  const [page, setPage] = useState<LegalPageContent | null>(null)
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

  if (loading) {
    return (
      <div className="legal-page shell-content">
        <div className="card legal-page__card">{t('legal.pageLoading')}</div>
      </div>
    )
  }

  if (!enabled) {
    return (
      <div className="legal-page shell-content">
        <div className="card legal-page__card">
          <h1>{t('legal.pageDisabledTitle')}</h1>
          <p>{t('legal.pageDisabledBody')}</p>
          <Link to="/">{t('legal.backHome')}</Link>
        </div>
      </div>
    )
  }

  if (error || !page) {
    return (
      <div className="legal-page shell-content">
        <div className="card legal-page__card">
          <h1>{error === 'not_found' ? t('legal.pageNotFound') : t('legal.pageLoadFailed')}</h1>
          <Link to="/">{t('legal.backHome')}</Link>
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
          <Link to="/">{t('legal.backHome')}</Link>
        </p>
      </article>
    </div>
  )
}
