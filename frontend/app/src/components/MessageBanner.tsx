interface MessageBannerProps {
  type: 'success' | 'error'
  text: string
}

export default function MessageBanner({ type, text }: MessageBannerProps) {
  return (
    <div style={{
      padding: '1rem',
      marginBottom: '1.5rem',
      borderRadius: '8px',
      background: type === 'success' ? 'rgba(40, 167, 69, 0.2)' : 'rgba(220, 53, 69, 0.2)',
      border: `1px solid ${type === 'success' ? 'var(--color-pass)' : 'var(--color-critical)'}`,
      color: type === 'success' ? 'var(--color-pass)' : 'var(--color-critical)'
    }}>
      {text}
    </div>
  )
}
