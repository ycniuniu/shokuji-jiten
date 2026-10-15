import { useCallback, useEffect, useState } from 'react'
import { ApiError, getFood, searchFoods } from './api'
import { FoodCard } from './components/FoodCard'
import { FoodModal } from './components/FoodModal'
import { ModeSwitcher } from './components/ModeSwitcher'
import { useSpeech } from './hooks/useSpeech'
import { foodTitle, type FoodDetail, type FoodListItem, type Mode } from './types'

const RATE_MSG = '每分钟只能使用十次，超出了十次，等下一分钟再开始'

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

  const { speak } = useSpeech(mode, voiceOn)

  useEffect(() => {
    const t = setTimeout(() => setDebounced(query.trim()), 350)
    return () => clearTimeout(t)
  }, [query])

  useEffect(() => {
    if (mode === 'elder') setVoiceOn(true)
  }, [mode])

  const load = useCallback(async (q: string) => {
    setLoading(true)
    setError(null)
    try {
      const data = await searchFoods(q, 0, 36)
      setItems(data.items)
      setTotal(data.total)
    } catch (e) {
      if (e instanceof ApiError && e.status === 429) {
        setError(RATE_MSG)
      } else {
        setError(e instanceof Error ? e.message : '加载失败')
      }
      setItems([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load(debounced)
  }, [debounced, load])

  const openDetail = async (id: number) => {
    setError(null)
    try {
      const food = await getFood(id)
      setDetail(food)
      if (mode === 'elder' && voiceOn) speak(foodTitle(food))
    } catch (e) {
      if (e instanceof ApiError && e.status === 429) {
        setError(RATE_MSG)
      } else {
        setError(e instanceof Error ? e.message : '加载详情失败')
      }
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
                : '检索多国食物成分，查看每 100 g 营养与常见份量换算。'}
          </p>
          <div className="search-row">
            <input
              className="search-input"
              type="search"
              placeholder="搜索食物名称…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
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
            {loading ? '加载中…' : `共 ${total} 条`}
            <span className="rate-hint">（接口限流：每分钟 10 次）</span>
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
          {!loading && items.length === 0 && !error && (
            <p className="empty">没有找到食物，换个关键词试试。</p>
          )}
        </section>
      </main>

      <footer className="site-footer">
        <p>食事事典 · 营养数据来自多国公开成分表 · 仅供参考</p>
        <p>成年人轻度活动时，一天大约需要 1800 到 2000 千卡，因人而异，仅供参考。</p>
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
