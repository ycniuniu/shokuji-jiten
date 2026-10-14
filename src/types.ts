export type Mode = 'elder' | 'child' | 'adult'

export interface FoodListItem {
  id: number
  name: string
  name_en: string | null
  name_original: string | null
  name_zh: string | null
  source_country: string
  category: string | null
  kcal_100g: number | null
  image_path: string | null
  serving_ref: string | null
}

export interface FoodDetail extends FoodListItem {
  source_id: string | null
  protein_g: number | null
  fat_g: number | null
  carbs_g: number | null
  sodium_mg: number | null
  calcium_mg: number | null
  iron_mg: number | null
  zinc_mg: number | null
  selenium_ug: number | null
  vitamin_a_ug: number | null
  vitamin_c_mg: number | null
  vitamin_d_ug: number | null
  vitamin_e_mg: number | null
  vitamin_b1_mg: number | null
  vitamin_b2_mg: number | null
  vitamin_b3_mg: number | null
}

export interface FoodsResponse {
  total: number
  items: FoodListItem[]
}

export function foodTitle(food: { name: string; name_zh?: string | null }) {
  const zh = food.name_zh?.trim()
  return zh || food.name
}

export function foodOriginal(food: {
  name: string
  name_original?: string | null
  name_zh?: string | null
}) {
  const original = (food.name_original || food.name).trim()
  return original && original !== foodTitle(food) ? original : null
}
