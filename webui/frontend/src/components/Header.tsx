import { Link } from 'react-router-dom'

export default function Header() {
  return (
    <header className="header">
      <div>
        <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
          <h1>🛡️ SimpleSecCheck</h1>
        </Link>
      </div>
      <nav>
        <Link to="/" style={{ marginRight: '1rem', color: 'inherit', textDecoration: 'none' }}>
          Home
        </Link>
        <Link to="/results" style={{ color: 'inherit', textDecoration: 'none' }}>
          Results
        </Link>
      </nav>
    </header>
  )
}
