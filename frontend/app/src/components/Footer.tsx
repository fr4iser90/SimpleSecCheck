const REPO = 'https://github.com/fr4iser90/SimpleSecCheck'
const LICENSE = `${REPO}/blob/main/LICENSE`

export default function Footer() {
  return (
    <footer className="app-footer-minimal">
      <span>© {new Date().getFullYear()} Fr4iser</span>
      <span className="app-footer-minimal__sep" aria-hidden>
        ·
      </span>
      <a href={LICENSE} target="_blank" rel="noopener noreferrer">
        MIT License
      </a>
      <span className="app-footer-minimal__sep" aria-hidden>
        ·
      </span>
      <a href={REPO} target="_blank" rel="noopener noreferrer">
        GitHub <span aria-hidden>→</span>
      </a>
    </footer>
  )
}
