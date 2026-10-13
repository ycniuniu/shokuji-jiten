import type { Mode } from '../types'

const MODES: { id: Mode; label: string }[] = [
  { id: 'elder', label: '长辈' },
  { id: 'child', label: '儿童' },
  { id: 'adult', label: '成人' },
]

export function ModeSwitcher({
  mode,
  onChange,
}: {
  mode: Mode
  onChange: (m: Mode) => void
}) {
  return (
    <div className="mode-switcher" role="tablist" aria-label="阅读模式">
      {MODES.map((m) => (
        <button
          key={m.id}
          type="button"
          role="tab"
          aria-selected={mode === m.id}
          className={mode === m.id ? 'active' : ''}
          onClick={() => onChange(m.id)}
        >
          {m.label}
        </button>
      ))}
    </div>
  )
}
