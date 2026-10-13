import cors from 'cors'
import express from 'express'
import rateLimit from 'express-rate-limit'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import Database from 'better-sqlite3'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, '..')
const DB_FILE = path.join(ROOT, 'data', 'food.db')
const PORT = Number(process.env.PORT || 3001)
const isProd = process.env.NODE_ENV === 'production'

const app = express()
app.use(cors())
app.use(express.json())

const RATE_MSG = '每分钟只能使用五次，超出了五次，等下一分钟再开始'

const apiLimiter = rateLimit({
  windowMs: 60_000,
  max: 5,
  standardHeaders: true,
  legacyHeaders: false,
  handler: (_req, res) => {
    res.status(429).json({ error: RATE_MSG, message: RATE_MSG })
  },
  message: { error: RATE_MSG, message: RATE_MSG },
})

let db: Database.Database
try {
  db = new Database(DB_FILE, { readonly: true, fileMustExist: true })
} catch (err) {
  console.error('Failed to open SQLite DB at', DB_FILE, err)
  console.error('Run: npm run build:db')
  process.exit(1)
}

const listStmt = db.prepare(`
  SELECT id, name, name_en, source_country, category, kcal_100g, image_path, serving_ref
  FROM foods
  WHERE (? = '' OR name LIKE ? OR name_en LIKE ? OR category LIKE ?)
  ORDER BY
    CASE WHEN ? != '' AND name LIKE ? THEN 0 ELSE 1 END,
    kcal_100g IS NULL, name
  LIMIT ? OFFSET ?
`)

const countStmt = db.prepare(`
  SELECT COUNT(*) AS n FROM foods
  WHERE (? = '' OR name LIKE ? OR name_en LIKE ? OR category LIKE ?)
`)

const oneStmt = db.prepare(`SELECT * FROM foods WHERE id = ?`)

const statsStmt = db.prepare(`
  SELECT source_country AS country, COUNT(*) AS count
  FROM foods GROUP BY source_country ORDER BY count DESC
`)

app.get('/api/health', (_req, res) => {
  const total = db.prepare('SELECT COUNT(*) AS n FROM foods').get() as { n: number }
  res.json({ ok: true, foods: total.n })
})

app.get('/api/stats', apiLimiter, (_req, res) => {
  res.json({ byCountry: statsStmt.all() })
})

app.get('/api/foods', apiLimiter, (req, res) => {
  const q = String(req.query.q || '').trim()
  const limit = Math.min(Number(req.query.limit) || 24, 100)
  const offset = Math.max(Number(req.query.offset) || 0, 0)
  const like = q ? `%${q}%` : ''
  const prefix = q ? `${q}%` : ''
  const empty = q ? 'x' : ''
  const rows = listStmt.all(q, like, like, like, empty, prefix, limit, offset)
  const { n } = countStmt.get(q, like, like, like) as { n: number }
  res.json({ total: n, items: rows })
})

app.get('/api/foods/:id', apiLimiter, (req, res) => {
  const row = oneStmt.get(Number(req.params.id))
  if (!row) {
    res.status(404).json({ error: 'Not found' })
    return
  }
  res.json(row)
})

if (isProd) {
  const dist = path.join(ROOT, 'dist')
  app.use(express.static(dist))
  app.use('/images', express.static(path.join(ROOT, 'public', 'images')))
  app.get('*', (_req, res) => {
    res.sendFile(path.join(dist, 'index.html'))
  })
}

app.listen(PORT, () => {
  console.log(`食事事典 API on http://localhost:${PORT}`)
})
