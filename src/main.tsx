import { createRoot } from 'react-dom/client'
import App from './App'
import './styles/app.css'

// Avoid React StrictMode double-fetch in dev — API is rate-limited to 10 req/min.
createRoot(document.getElementById('root')!).render(<App />)
