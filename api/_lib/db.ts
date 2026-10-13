import fs from 'node:fs'
import path from 'node:path'
import initSqlJs, { type Database, type SqlJsStatic } from 'sql.js'

let SQL: SqlJsStatic | null = null
let db: Database | null = null

function resolveDbPath(): string {
  const candidates = [
    path.join(process.cwd(), 'data', 'food.db'),
    path.join(process.cwd(), 'food-nutrition', 'data', 'food.db'),
  ]
  for (const p of candidates) {
    if (fs.existsSync(p)) return p
  }
  throw new Error('food.db not found — ensure data/food.db is included in the deploy')
}

export async function getDb(): Promise<Database> {
  if (db) return db
  if (!SQL) {
    SQL = await initSqlJs({
      locateFile: (file) => {
        // Prefer package wasm next to sql.js
        const pkg = path.join(process.cwd(), 'node_modules', 'sql.js', 'dist', file)
        if (fs.existsSync(pkg)) return pkg
        return `https://sql.js.org/dist/${file}`
      },
    })
  }
  const file = resolveDbPath()
  const buf = fs.readFileSync(file)
  db = new SQL.Database(new Uint8Array(buf))
  return db
}

export function rowsFrom(result: ReturnType<Database['exec']>): Record<string, unknown>[] {
  if (!result.length) return []
  const { columns, values } = result[0]
  return values.map((row) => {
    const obj: Record<string, unknown> = {}
    columns.forEach((c, i) => {
      obj[c] = row[i]
    })
    return obj
  })
}

export async function searchFoods(q: string, limit: number, offset: number) {
  const database = await getDb()
  const like = q ? `%${q.replace(/%/g, '')}%` : ''
  const prefix = q ? `${q.replace(/%/g, '')}%` : ''

  const countStmt = database.prepare(`
    SELECT COUNT(*) AS n FROM foods
    WHERE (? = '' OR name LIKE ? OR IFNULL(name_en,'') LIKE ? OR IFNULL(category,'') LIKE ?)
  `)
  countStmt.bind([q, like, like, like])
  countStmt.step()
  const countRow = countStmt.getAsObject() as { n: number }
  countStmt.free()

  const listStmt = database.prepare(`
    SELECT id, name, name_en, source_country, category, kcal_100g, image_path, serving_ref
    FROM foods
    WHERE (? = '' OR name LIKE ? OR IFNULL(name_en,'') LIKE ? OR IFNULL(category,'') LIKE ?)
    ORDER BY
      CASE WHEN ? != '' AND name LIKE ? THEN 0 ELSE 1 END,
      kcal_100g IS NULL, name
    LIMIT ? OFFSET ?
  `)
  listStmt.bind([q, like, like, like, q ? 'x' : '', prefix, limit, offset])
  const items: Record<string, unknown>[] = []
  while (listStmt.step()) {
    items.push(listStmt.getAsObject())
  }
  listStmt.free()
  return { total: Number(countRow.n) || 0, items }
}

export async function getFoodById(id: number) {
  const database = await getDb()
  const stmt = database.prepare('SELECT * FROM foods WHERE id = ?')
  stmt.bind([id])
  if (!stmt.step()) {
    stmt.free()
    return null
  }
  const row = stmt.getAsObject()
  stmt.free()
  return row
}

export async function healthCount() {
  const database = await getDb()
  const stmt = database.prepare('SELECT COUNT(*) AS n FROM foods')
  stmt.step()
  const row = stmt.getAsObject() as { n: number }
  stmt.free()
  return Number(row.n) || 0
}
