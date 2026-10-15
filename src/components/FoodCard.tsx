import { foodOriginal, foodTitle, type FoodListItem, type Mode } from '../types'
import { foodGrade, GRADE_LABEL } from '../grade'

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

export function FoodCard({
  food,
  mode,
  onOpen,
  onSpeak,
}: {
  food: FoodListItem
  mode: Mode
  onOpen: (id: number) => void
  onSpeak: (name: string) => void
}) {
  const title = foodTitle(food)
  const original = foodOriginal(food)
  const kcal =
    food.kcal_100g != null ? `${Math.round(food.kcal_100g)} 千卡/100g` : '—'
  const grade = foodGrade(food)

  return (
    <article className={`food-card mode-${mode}`} onClick={() => onOpen(food.id)}>
      <div className="food-card-image">
        {food.image_path ? (
          <img src={food.image_path} alt={title} loading="lazy" />
        ) : (
          <div className="food-card-placeholder" aria-hidden>
            {mode === 'child' ? '🍎' : '食'}
          </div>
        )}
      </div>
      <div className="food-card-body">
        <button
          type="button"
          className="food-name-btn"
          onClick={(e) => {
            e.stopPropagation()
            onSpeak(title)
          }}
          title="朗读名称"
        >
          {title}
        </button>
        {original && <p className="food-original">{original}</p>}
        <p className="food-meta">
          <span>{COUNTRY[food.source_country] || food.source_country}</span>
          <span className="dot">·</span>
          <span>{kcal}</span>
          {grade && (
            <>
              <span className="dot">·</span>
              <span className={`grade-chip grade-${grade}`}>{GRADE_LABEL[grade]}</span>
            </>
          )}
        </p>
      </div>
    </article>
  )
}
