import type { FoodListItem } from './types'

/** Energy-density grade for every 100 g (kcal). */
export type LightGrade = 'green' | 'yellow' | 'red'

export function calorieGrade(kcal: number | null | undefined): LightGrade | null {
  if (kcal == null || Number.isNaN(kcal)) return null
  if (kcal < 150) return 'green'
  if (kcal < 400) return 'yellow'
  return 'red'
}

export const GRADE_LABEL: Record<LightGrade, string> = {
  green: '可常吃',
  yellow: '适量食用',
  red: '限量食用',
}

export function foodGrade(food: Pick<FoodListItem, 'kcal_100g'>): LightGrade | null {
  return calorieGrade(food.kcal_100g)
}
