import { createRequire } from 'node:module'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import type { Database, SqlJsStatic } from 'sql.js'

const require = createRequire(import.meta.url)
const initSqlJs = require('sql.js') as (config?: {
  wasmBinary?: Uint8Array
}) => Promise<SqlJsStatic>

let SQL: SqlJsStatic | null = null
let db: Database | null = null

function firstExisting(candidates: string[]): string {
  for (const file of candidates) {
    if (fs.existsSync(file)) return file
  }
  throw new Error(`not found:\n${candidates.join('\n')}`)
}

function wasmBinary(): Uint8Array {
  const here = path.dirname(fileURLToPath(import.meta.url))
  const candidates = [
    path.join(here, 'sql-wasm.wasm'),
    path.join(process.cwd(), 'api', '_lib', 'sql-wasm.wasm'),
    path.join(process.cwd(), 'node_modules', 'sql.js', 'dist', 'sql-wasm.wasm'),
  ]
  try {
    candidates.unshift(require.resolve('sql.js/dist/sql-wasm.wasm'))
  } catch {
    /* package path is optional when the vendored wasm is present */
  }
  return fs.readFileSync(firstExisting(candidates))
}

function resolveDbPath(): string {
  return firstExisting([
    path.join(process.cwd(), 'data', 'food.db'),
    path.join(process.cwd(), 'food-nutrition', 'data', 'food.db'),
  ])
}

export async function getDb(): Promise<Database> {
  if (db) return db
  if (!SQL) {
    // Pass the bytes directly. A missing wasm URL makes sql.js abort the
    // process, which Vercel reports as FUNCTION_INVOCATION_FAILED.
    SQL = await initSqlJs({ wasmBinary: wasmBinary() })
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
    WHERE (? = '' OR name LIKE ? OR IFNULL(name_en,'') LIKE ? OR IFNULL(name_zh,'') LIKE ? OR IFNULL(name_original,'') LIKE ? OR IFNULL(category,'') LIKE ?)
  `)
  countStmt.bind([q, like, like, like, like, like])
  countStmt.step()
  const countRow = countStmt.getAsObject() as { n: number }
  countStmt.free()

  const listStmt = database.prepare(`
    SELECT id, name, name_en, name_original, name_zh, source_country, category, kcal_100g, image_path, serving_ref
    FROM foods
    WHERE (? = '' OR name LIKE ? OR IFNULL(name_en,'') LIKE ? OR IFNULL(name_zh,'') LIKE ? OR IFNULL(name_original,'') LIKE ? OR IFNULL(category,'') LIKE ?)
    ORDER BY
      CASE WHEN ? != '' AND (name LIKE ? OR IFNULL(name_zh,'') LIKE ?) THEN 0 ELSE 1 END,
      kcal_100g IS NULL, name
    LIMIT ? OFFSET ?
  `)
  listStmt.bind([q, like, like, like, like, like, q ? 'x' : '', prefix, prefix, limit, offset])
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
