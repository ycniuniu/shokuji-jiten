import type { VercelRequest, VercelResponse } from '@vercel/node'
import { healthCount } from './_lib/db.js'

export default async function handler(_req: VercelRequest, res: VercelResponse) {
  try {
    const foods = await healthCount()
    res.status(200).json({ ok: true, foods, runtime: 'vercel' })
  } catch (err) {
    res.status(500).json({ ok: false, error: String(err) })
  }
}
