import { useEffect, useState } from 'react'
import { creditFor, type PhotoCredit } from '../credits'
import { foodGrade, GRADE_LABEL, type LightGrade } from '../grade'
import { foodTitle, type FoodDetail, type Mode } from '../types'

const KJ_PER_KCAL = 4.184

// GB 28050-2011 表 A.1 营养素参考值（NRV）
// 出处：卫计委发布的《食品安全国家标准 预包装食品营养标签通则》GB 28050-2011 附录 A 表 A.1
const NRV = {
  energy_kj: 8400,
  protein_g: 60,
  fat_g: 60,
  carbs_g: 300,
  sodium_mg: 2000,
}

function num(n: number | null | undefined): number | null {
  return n == null || Number.isNaN(n) ? null : n
}

function fmt(n: number) {
  return `${Math.round(n * 10) / 10}`
}

type Ring = { key: string; label: string; share: number; color: string }

function macroRings(food: FoodDetail): Ring[] {
  const parts = [
    { key: 'carbs', label: '碳水', g: num(food.carbs_g), per: 4, color: 'var(--ring-carbs)' },
    { key: 'protein', label: '蛋白质', g: num(food.protein_g), per: 4, color: 'var(--ring-protein)' },
    { key: 'fat', label: '脂肪', g: num(food.fat_g), per: 9, color: 'var(--ring-fat)' },
  ]
  if (parts.some((p) => p.g == null)) return []
  const kcal = parts.map((p) => (p.g as number) * p.per)
  const total = kcal.reduce((a, b) => a + b, 0)
  if (total <= 0) return []
  return parts.map((p, i) => ({
    key: p.key,
    label: p.label,
    share: kcal[i] / total,
    color: p.color,
  }))
}

function RingChart({ ring }: { ring: Ring }) {
  const r = 26
  const c = 2 * Math.PI * r
  const pct = Math.round(ring.share * 100)
  return (
    <figure className="macro-ring">
      <svg viewBox="0 0 64 64" width="72" height="72" role="img" aria-label={`${ring.label}供能 ${pct}%`}>
        <circle cx="32" cy="32" r={r} fill="none" stroke="var(--line)" strokeWidth="6" />
        <circle
          cx="32"
          cy="32"
          r={r}
          fill="none"
          stroke={ring.color}
          strokeWidth="6"
          strokeDasharray={`${c * ring.share} ${c}`}
          strokeLinecap="round"
          transform="rotate(-90 32 32)"
        />
        <text x="32" y="36" textAnchor="middle" className="macro-ring-pct">
          {pct}%
        </text>
      </svg>
      <figcaption>{ring.label}供能</figcaption>
    </figure>
  )
}

function GradeBadge({ grade }: { grade: LightGrade }) {
  return (
    <span className={`grade-badge grade-${grade}`}>
      <span className="grade-dot" aria-hidden />
      {GRADE_LABEL[grade]}
    </span>
  )
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
  const [credit, setCredit] = useState<PhotoCredit | null>(null)

  useEffect(() => {
    let alive = true
    setCredit(null)
    if (food.image_path) {
      creditFor(food.image_path).then((c) => {
        if (alive) setCredit(c)
      })
    }
    return () => {
      alive = false
    }
  }, [food.image_path])

  const kcal = num(food.kcal_100g)
  const kj = kcal == null ? null : Math.round(kcal * KJ_PER_KCAL)
  const rings = macroRings(food)
  const grade = foodGrade(food)
  const title = foodTitle(food)

  const rows = [
    { label: '能量', value: kcal, unit: '千卡', denom: null as number | null, energyPct: kj },
    { label: '蛋白质', value: num(food.protein_g), unit: '克', denom: NRV.protein_g, energyPct: null },
    { label: '脂肪', value: num(food.fat_g), unit: '克', denom: NRV.fat_g, energyPct: null },
    { label: '碳水化合物', value: num(food.carbs_g), unit: '克', denom: NRV.carbs_g, energyPct: null },
    { label: '钠', value: num(food.sodium_mg), unit: '毫克', denom: NRV.sodium_mg, energyPct: null },
  ]
    .filter((r) => r.value != null)
    .map((r) => ({
      label: r.label,
      value: r.value as number,
      unit: r.unit,
      pct:
        r.label === '能量'
          ? r.energyPct == null
            ? null
            : Math.round((r.energyPct / NRV.energy_kj) * 100)
          : Math.round(((r.value as number) / (r.denom as number)) * 100),
    }))

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
            <img src={food.image_path} alt={title} />
          ) : (
            <div className="modal-hero-placeholder">{mode === 'child' ? '🥕' : '食'}</div>
          )}
        </div>
        {credit && (
          <p className="photo-credit">
            <a href={credit.page_url} target="_blank" rel="noopener noreferrer">
              照片：{credit.author} / {credit.license}
            </a>
          </p>
        )}
        <div className="modal-content">
          <div className="modal-title-row">
            <button
              type="button"
              id="food-modal-title"
              className="food-name-btn modal-title-btn"
              onClick={() => onSpeak(title)}
            >
              {title}
            </button>
            {grade && <GradeBadge grade={grade} />}
          </div>

          <div className="energy-hero">
            {kcal == null ? (
              <p className="energy-missing">暂无热量数据</p>
            ) : (
              <>
                <p className="energy-main">
                  <strong>{Math.round(kcal)}</strong>
                  <span className="energy-unit">千卡</span>
                </p>
                <p className="energy-sub">每 100 克 · {kj} 千焦</p>
              </>
            )}
          </div>

          {rings.length > 0 && (
            <div className="macro-rings" aria-label="三大营养素供能占比">
              {rings.map((r) => (
                <RingChart key={r.key} ring={r} />
              ))}
            </div>
          )}

          {rows.length > 0 && (
            <table className="nutrient-table nutrient-table-compact">
              <thead>
                <tr>
                  <th>营养素</th>
                  <th>每 100 克</th>
                  <th>占每日参考</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.label}>
                    <td>{r.label}</td>
                    <td>
                      {fmt(r.value)} {r.unit}
                    </td>
                    <td>{r.pct == null ? '—' : `${r.pct}%`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
