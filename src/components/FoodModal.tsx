import { useMemo, useState } from 'react'
import type { FoodDetail, Mode } from '../types'

const COUNTRY: Record<string, string> = {
  CN: '中国',
  JP: '日本',
  KR: '韩国',
  SG: '新加坡',
  US: '美国',
  UK: '英国',
  FR: '法国',
  DE: '德国',
}

function fmt(n: number | null | undefined, unit = '') {
  if (n == null || Number.isNaN(n)) return '—'
  const v = Math.round(n * 100) / 100
  return `${v}${unit}`
}

const CHILD_TIPS = [
  '蛋白质帮你长高长壮，像小超人加油！',
  '蔬菜水果里有维生素 C，保护身体小卫士。',
  '少吃太咸的食物，心脏会更开心哦。',
  '每餐吃得彩虹一点：红黄绿都尝一尝。',
]

function parseServingGrams(ref: string | null): number {
  if (!ref) return 100
  const m = ref.match(/(\d+(?:\.\d+)?)\s*(?:g|克|ml|毫升)/i)
  return m ? Number(m[1]) : 100
}

export function FoodModal({
  food,
  mode,
  onClose,
  onSpeak,
}: {
  food: FoodDetail
  mode: Mode
  onClose: () => void
  onSpeak: (name: string) => void
}) {
  const servingG = parseServingGrams(food.serving_ref)
  const [grams, setGrams] = useState(servingG)

  const scale = grams / 100
  const tip = useMemo(
    () => CHILD_TIPS[food.id % CHILD_TIPS.length],
    [food.id],
  )

  const rows: { label: string; value: number | null; unit: string }[] = [
    { label: '能量', value: food.kcal_100g, unit: ' kcal' },
    { label: '蛋白质', value: food.protein_g, unit: ' g' },
    { label: '脂肪', value: food.fat_g, unit: ' g' },
    { label: '碳水化合物', value: food.carbs_g, unit: ' g' },
    { label: '钠', value: food.sodium_mg, unit: ' mg' },
    { label: '钙', value: food.calcium_mg, unit: ' mg' },
    { label: '铁', value: food.iron_mg, unit: ' mg' },
    { label: '锌', value: food.zinc_mg, unit: ' mg' },
    { label: '硒', value: food.selenium_ug, unit: ' µg' },
    { label: '维生素 A', value: food.vitamin_a_ug, unit: ' µg' },
    { label: '维生素 C', value: food.vitamin_c_mg, unit: ' mg' },
    { label: '维生素 D', value: food.vitamin_d_ug, unit: ' µg' },
    { label: '维生素 E', value: food.vitamin_e_mg, unit: ' mg' },
    { label: '维生素 B1', value: food.vitamin_b1_mg, unit: ' mg' },
    { label: '维生素 B2', value: food.vitamin_b2_mg, unit: ' mg' },
    { label: '维生素 B3', value: food.vitamin_b3_mg, unit: ' mg' },
  ]

  const showDetailed = mode === 'adult' || mode === 'elder'
  const displayRows =
    mode === 'elder'
      ? rows.filter((r) =>
          ['能量', '蛋白质', '脂肪', '碳水化合物', '钠', '钙', '铁'].includes(r.label),
        )
      : mode === 'child'
        ? rows.filter((r) =>
            ['能量', '蛋白质', '脂肪', '碳水化合物', '维生素 C'].includes(r.label),
          )
        : rows

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className={`modal mode-${mode}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="food-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <button type="button" className="modal-close" onClick={onClose} aria-label="关闭">
          ×
        </button>
        <div className="modal-hero">
          {food.image_path ? (
            <img src={food.image_path} alt="" />
          ) : (
            <div className="modal-hero-placeholder">{mode === 'child' ? '🥕' : '食'}</div>
          )}
        </div>
        <div className="modal-content">
          <button
            type="button"
            id="food-modal-title"
            className="food-name-btn modal-title-btn"
            onClick={() => onSpeak(food.name)}
          >
            {food.name}
          </button>
          {food.name_en && <p className="modal-en">{food.name_en}</p>}
          <p className="food-meta">
            {COUNTRY[food.source_country] || food.source_country}
            {food.category ? ` · ${food.category}` : ''}
          </p>

          <div className="serving-box">
            <label htmlFor="serving-grams">常见份量换算</label>
            <p className="serving-ref">{food.serving_ref || '按每 100 g 基准'}</p>
            <div className="serving-controls">
              <input
                id="serving-grams"
                type="range"
                min={10}
                max={500}
                step={5}
                value={grams}
                onChange={(e) => setGrams(Number(e.target.value))}
              />
              <span className="serving-value">{grams} g</span>
            </div>
          </div>

          {mode === 'child' && (
            <div className="child-tip">
              <span className="child-tip-icon" aria-hidden>
                ⭐
              </span>
              <p>{tip}</p>
            </div>
          )}

          <table className="nutrient-table">
            <thead>
              <tr>
                <th>营养素</th>
                <th>每 100 g</th>
                <th>当前份量</th>
              </tr>
            </thead>
            <tbody>
              {displayRows.map((r) => (
                <tr key={r.label}>
                  <td>{r.label}</td>
                  <td>{fmt(r.value, r.unit)}</td>
                  <td>{r.value == null ? '—' : fmt(r.value * scale, r.unit)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {showDetailed && mode === 'adult' && (
            <p className="footnote">数值均以每 100 g 可食部为基准换算；微量元素缺测显示为 —。</p>
          )}
        </div>
      </div>
    </div>
  )
}
