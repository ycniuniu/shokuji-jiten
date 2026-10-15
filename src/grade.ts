/** Calorie traffic-light grade per 100 g, with a one-step fat upgrade. */
export type LightGrade = 'green' | 'yellow' | 'red'

export const GRADE_LABEL: Record<LightGrade, string> = {
  green: '可常吃',
  yellow: '适量食用',
  red: '少吃为宜',
}

export type GradeInput = {
  kcal_100g: number | null | undefined
  carbs_g?: number | null
  protein_g?: number | null
  fat_g?: number | null
}

export type GradeResult = {
  grade: LightGrade
  /** Fat share of energy (0–1), or null when macro data is missing. */
  fatShare: number | null
  /** True when the grade was raised one step because of high fat. */
  fatUpgraded: boolean
}

function ok(n: number | null | undefined): n is number {
  return n != null && !Number.isNaN(n)
}

export function baseGrade(kcal: number): LightGrade {
  if (kcal < 150) return 'green'
  if (kcal < 400) return 'yellow'
  return 'red'
}

/** fat×9 ÷ (carbs×4 + protein×4 + fat×9); null if any macro is missing. */
export function fatEnergyShare(food: GradeInput): number | null {
  const { carbs_g: c, protein_g: p, fat_g: f } = food
  if (!ok(c) || !ok(p) || !ok(f)) return null
  const total = c * 4 + p * 4 + f * 9
  return total > 0 ? (f * 9) / total : null
}

export function gradeFood(food: GradeInput): GradeResult | null {
  const kcal = food.kcal_100g
  if (!ok(kcal)) return null
  const base = baseGrade(kcal)
  const fatShare = fatEnergyShare(food)
  let grade = base
  if (fatShare != null && fatShare >= 0.5) {
    if (base === 'green' && kcal >= 100) grade = 'yellow'
    else if (base === 'yellow' && kcal >= 250) grade = 'red'
  }
  return { grade, fatShare, fatUpgraded: grade !== base }
}
