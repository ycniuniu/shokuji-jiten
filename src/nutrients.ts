import type { FoodDetail } from './types'

export type NutrientRow = { key: string; label: string; value: string; unit: string }

type ColumnKey = Extract<keyof FoodDetail, `${string}_${'g' | 'mg' | 'ug' | '100g'}`>

/** Database columns, in display order. */
const COLUMNS: { key: ColumnKey; label: string; unit: string }[] = [
  { key: 'kcal_100g', label: '能量', unit: '千卡' },
  { key: 'protein_g', label: '蛋白质', unit: '克' },
  { key: 'fat_g', label: '脂肪', unit: '克' },
  { key: 'carbs_g', label: '碳水化合物', unit: '克' },
  { key: 'sodium_mg', label: '钠', unit: '毫克' },
  { key: 'calcium_mg', label: '钙', unit: '毫克' },
  { key: 'iron_mg', label: '铁', unit: '毫克' },
  { key: 'zinc_mg', label: '锌', unit: '毫克' },
  { key: 'selenium_ug', label: '硒', unit: '微克' },
  { key: 'vitamin_a_ug', label: '维生素 A', unit: '微克' },
  { key: 'vitamin_b1_mg', label: '维生素 B1（硫胺素）', unit: '毫克' },
  { key: 'vitamin_b2_mg', label: '维生素 B2（核黄素）', unit: '毫克' },
  { key: 'vitamin_b3_mg', label: '维生素 B3（烟酸）', unit: '毫克' },
  { key: 'vitamin_c_mg', label: '维生素 C', unit: '毫克' },
  { key: 'vitamin_d_ug', label: '维生素 D', unit: '微克' },
  { key: 'vitamin_e_mg', label: '维生素 E', unit: '毫克' },
]

/** Extra indicators only stored in raw_json (China food composition table). */
const RAW_EXTRAS: { key: string; label: string; unit: string }[] = [
  { key: 'water', label: '水分', unit: '克' },
  { key: 'dietaryFiber', label: '膳食纤维', unit: '克' },
  { key: 'ash', label: '灰分', unit: '克' },
  { key: 'cholesterol', label: '胆固醇', unit: '毫克' },
  { key: 'carotene', label: '胡萝卜素', unit: '微克' },
  { key: 'retinol', label: '视黄醇', unit: '微克' },
  { key: 'vitaminE1', label: 'α-生育酚', unit: '毫克' },
  { key: 'vitaminE2', label: '(β+γ)-生育酚', unit: '毫克' },
  { key: 'vitaminE3', label: 'δ-生育酚', unit: '毫克' },
  { key: 'P', label: '磷', unit: '毫克' },
  { key: 'K', label: '钾', unit: '毫克' },
  { key: 'Mg', label: '镁', unit: '毫克' },
  { key: 'Cu', label: '铜', unit: '毫克' },
  { key: 'Mn', label: '锰', unit: '毫克' },
]

export const INDICATOR_COUNT = COLUMNS.length + RAW_EXTRAS.length

function fmtNum(n: number): string {
  return `${Math.round(n * 100) / 100}`
}

function rawValue(v: unknown): string | null {
  if (v == null) return null
  const s = String(v).trim()
  if (!s || s === '—' || s === '-' || s === '…') return null
  if (s.toLowerCase() === 'tr') return '微量'
  const n = Number(s)
  return Number.isFinite(n) ? fmtNum(n) : null
}

function parseRaw(raw: string | null | undefined): Record<string, unknown> {
  if (!raw) return {}
  try {
    const v = JSON.parse(raw)
    return v && typeof v === 'object' ? (v as Record<string, unknown>) : {}
  } catch {
    return {}
  }
}

/** Every nutrient with a value for this food, per 100 g. Empty values are skipped. */
export function allNutrients(food: FoodDetail): NutrientRow[] {
  const rows: NutrientRow[] = []
  for (const c of COLUMNS) {
    const v = food[c.key]
    if (typeof v === 'number' && Number.isFinite(v)) {
      rows.push({ key: c.key, label: c.label, value: fmtNum(v), unit: c.unit })
    }
  }
  const raw = parseRaw(food.raw_json)
  for (const e of RAW_EXTRAS) {
    const v = rawValue(raw[e.key])
    if (v != null) rows.push({ key: e.key, label: e.label, value: v, unit: v === '微量' ? '' : e.unit })
  }
  return rows
}
