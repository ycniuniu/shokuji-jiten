import assert from 'node:assert/strict'
import { allNutrients, INDICATOR_COUNT } from '../src/nutrients.ts'
import type { FoodDetail } from '../src/types.ts'

const base = {
  id: 1, name: 'x', name_en: null, name_original: null, name_zh: null, source_country: 'CN',
  category: null, kcal_100g: 332, carbs_g: 55.4, protein_g: 8, fat_g: 8.7, image_path: null,
  serving_ref: null, source_id: null, sodium_mg: 211.9, calcium_mg: 242, iron_mg: 0.4, zinc_mg: null,
  selenium_ug: null, vitamin_a_ug: null, vitamin_c_mg: null, vitamin_d_ug: null, vitamin_e_mg: null,
  vitamin_b1_mg: null, vitamin_b2_mg: null, vitamin_b3_mg: null,
} satisfies FoodDetail

assert.equal(INDICATOR_COUNT, 30)
// null columns are skipped
const plain = allNutrients(base)
assert.deepEqual(plain.map((r) => r.label), ['能量', '蛋白质', '脂肪', '碳水化合物', '钠', '钙', '铁'])
// raw_json extras: numbers shown, "—" skipped, "Tr" shown as 微量
const rich = allNutrients({ ...base, raw_json: JSON.stringify({ water: '26.2', K: '309', Cu: '—', Mn: 'Tr', P: '' }) })
const byLabel = Object.fromEntries(rich.map((r) => [r.label, `${r.value}${r.unit}`]))
assert.equal(byLabel['水分'], '26.2克')
assert.equal(byLabel['钾'], '309毫克')
assert.equal(byLabel['锰'], '微量')
assert.equal(byLabel['铜'], undefined)
assert.equal(byLabel['磷'], undefined)
// bad raw_json does not crash
assert.equal(allNutrients({ ...base, raw_json: '{oops' }).length, 7)
console.log('nutrient tests passed')
