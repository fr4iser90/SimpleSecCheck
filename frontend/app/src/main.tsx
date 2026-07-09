import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles/design-tokens.css'
import './styles/app-shell.css'
import './styles/panels.css'
import './styles/target-card.css'
import './styles/scan-progress.css'
import './styles/toast.css'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
