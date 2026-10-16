import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, getFood, RATE_MSG, searchFoods } from './api'
import { FoodCard } from './components/FoodCard'
import { FoodModal } from './components/FoodModal'
import { ModeSwitcher } from './components/ModeSwitcher'
import { useSpeech } from './hooks/useSpeech'
import { foodTitle, type FoodDetail, type FoodListItem, type Mode } from './types'

const SEARCH_DEBOUNCE_MS = 350


const BMR_ROWS: [string, number, number][] = [
  ['儿童 6–7 岁', 980, 920],
  ['儿童 10–11 岁', 1330, 1260],
  ['成年人 18–29 岁', 1490, 1130],
  ['成年人 30–49 岁', 1570, 1170],
  ['成年人 50–64 岁', 1510, 1120],
  ['老人 65–74 岁', 1390, 1090],
  ['老人 75 岁以上', 1310, 1020],
]

export default function App() {
  const [mode, setMode] = useState<Mode>('adult')
  const [voiceOn, setVoiceOn] = useState(false)
  const [query, setQuery] = useState('')
  const [debounced, setDebounced] = useState('')
  const [items, setItems] = useState<FoodListItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [detail, setDetail] = useState<FoodDetail | null>(null)

  const [composing, setComposing] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const { speak } = useSpeech(mode, voiceOn)

  // Debounce, and wait while an IME (e.g. pinyin) is still composing.
  useEffect(() => {
    if (composing) return
    const t = setTimeout(() => setDebounced(query.trim()), SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(t)
  }, [query, composing])

  useEffect(() => {
    if (mode === 'elder') setVoiceOn(true)
  }, [mode])

  const load = useCallback(async (q: string) => {
    abortRef.current?.abort()
    if (!q) {
      abortRef.current = null
      setItems([])
      setTotal(0)
      setError(null)
      setLoading(false)
      return
    }
    const ctrl = new AbortController()
    abortRef.current = ctrl
    setLoading(true)
    setError(null)
    try {
      const data = await searchFoods(q, 0, 36, {
        signal: ctrl.signal,
        onRetry: () => setError(RATE_MSG),
      })
      if (ctrl.signal.aborted) return
      setError(null)
      setItems(data.items)
      setTotal(data.total)
    } catch (e) {
      if (ctrl.signal.aborted || (e instanceof DOMException && e.name === 'AbortError')) return
      setError(e instanceof Error ? e.message : '加载失败')
      setItems([])
      setTotal(0)
    } finally {
      if (abortRef.current === ctrl) setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load(debounced)
  }, [debounced, load])

  const openDetail = async (id: number) => {
    setError(null)
    try {
      const food = await getFood(id, () => setError(RATE_MSG))
      setError(null)
      setDetail(food)
      if (mode === 'elder' && voiceOn) speak(foodTitle(food))
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 429
          ? e.message
          : e instanceof Error
            ? e.message
            : '加载详情失败',
      )
    }
  }

  return (
    <div className={`app mode-${mode}`}>
      <header className="site-header">
        <div className="brand">
          <img src="/logo.png" alt="" className="brand-logo" width={44} height={44} />
          <h1 className="brand-title">食事事典</h1>
        </div>
        <ModeSwitcher mode={mode} onChange={setMode} />
      </header>

      <main className="main">
        <section className="hero-block">
          <p className="lede">
            {mode === 'elder'
              ? '点食物名字可以听朗读。字大、对比强，方便长辈查看。'
              : mode === 'child'
                ? '找找你认识的食物，看看小星星营养提示！'
                : '检索多国食物成分，查看每 100 克热量与营养概要。'}
          </p>
          <div className="search-row">
            <input
              className="search-input"
              type="search"
              placeholder="搜索食物名称…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onCompositionStart={() => setComposing(true)}
              onCompositionEnd={(e) => {
                setComposing(false)
                setQuery(e.currentTarget.value)
              }}
              aria-label="搜索食物"
            />
            <label className="voice-toggle">
              <input
                type="checkbox"
                checked={voiceOn}
                onChange={(e) => setVoiceOn(e.target.checked)}
              />
              语音朗读
            </label>
          </div>
          <p className="result-count">
            {loading ? '加载中…' : debounced ? `共 ${total} 条` : '输入食物名称开始搜索'}
          </p>
          {error && (
            <div className="error-banner" role="alert">
              {error}
            </div>
          )}
        </section>

        <section className="food-grid" aria-live="polite">
          {items.map((f) => (
            <FoodCard
              key={f.id}
              food={f}
              mode={mode}
              onOpen={openDetail}
              onSpeak={speak}
            />
          ))}
          {!loading && debounced && items.length === 0 && !error && (
            <p className="empty">没有找到食物，换个关键词试试。</p>
          )}
        </section>
      </main>

      <section className="bmr-ref" aria-labelledby="bmr-title">
        <h2 id="bmr-title">基础代谢参考值</h2>
        <p className="bmr-intro">完全静息、一动不动时，一天大约消耗的热量（千卡/天）</p>
        <table className="nutrient-table bmr-table">
          <thead>
            <tr>
              <th>年龄段</th>
              <th>男</th>
              <th>女</th>
            </tr>
          </thead>
          <tbody>
            {BMR_ROWS.map(([age, male, female]) => (
              <tr key={age}>
                <td>{age}</td>
                <td>{male.toLocaleString()} 千卡</td>
                <td>{female.toLocaleString()} 千卡</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="bmr-note">个人差异大，仅供参考</p>
      </section>

      <footer className="site-footer">
        <p>食事事典 · 营养数据来自多国公开成分表 · 仅供参考</p>
        <p>食物照片来自 Wikimedia Commons，按各自许可证使用</p>
        <p>成年人轻度活动时，一天大约需要 1800 到 2000 千卡，因人而异，仅供参考。</p>
        <div className="grade-guide">
          <p className="grade-guide-title">红黄绿灯怎么分</p>
          <p>
            按每 100 克热量：<span className="grade-chip grade-green">绿灯</span> 低于 150 千卡；
            <span className="grade-chip grade-yellow">黄灯</span> 150 到 399 千卡；
            <span className="grade-chip grade-red">红灯</span> 400 千卡及以上。
          </p>
          <p>
            脂肪升档：脂肪供能占比 = 脂肪克数 × 9 ÷（碳水克数 × 4 + 蛋白克数 × 4 + 脂肪克数 × 9）。绿灯食物热量 ≥ 100 且脂肪供能占比 ≥ 50% 升为黄灯；黄灯食物热量 ≥ 250 且脂肪供能占比 ≥ 50% 升为红灯。最多升一档，缺少营养素数据时不升档。
          </p>
          <p>只看热量和脂肪，不代表营养好坏，糖尿病等特殊饮食请听医生建议。</p>
        </div>
        <p>1 千卡（kcal）= 1000 卡（cal）。如果要看以「卡」为单位的数，把千卡数乘以 1000 就是。日常说的「卡路里」，多半指的就是千卡。</p>
      </footer>

      {detail && (
        <FoodModal
          food={detail}
          mode={mode}
          onClose={() => setDetail(null)}
          onSpeak={speak}
        />
      )}
    </div>
  )
}
