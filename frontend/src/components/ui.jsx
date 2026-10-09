import React from 'react'

export const STATUS_LABEL = {
  received: 'Хүлээн авсан', reviewed: 'Хянагдсан', reflected: 'Тусгагдсан', not_reflected: 'Тусгагдаагүй',
}

export function Pill({ kind = 'neu', children }) {
  return <span className={`pill p-${kind}`}>{children}</span>
}

export function SentPill({ s }) {
  return <Pill kind={s === 'Сөрөг' ? 'neg' : s === 'Эерэг' ? 'pos' : 'neu'}>{s}</Pill>
}

export function UrgPill({ u }) {
  return <Pill kind={u === 'Өндөр' ? 'neg' : u === 'Дунд' ? 'mid' : 'neu'}>{u}</Pill>
}

export function StatusPill({ s }) {
  return <Pill kind={s === 'reflected' ? 'pos' : s === 'not_reflected' ? 'neg' : s === 'reviewed' ? 'mid' : 'neu'}>{STATUS_LABEL[s] || s}</Pill>
}

export function Bars({ rows, color = 'var(--brand)' }) {
  const max = Math.max(1, ...rows.map((r) => r.count))
  return (
    <div>
      {rows.map((r) => (
        <div className="bar" key={r.name} title={`${r.name}: ${r.count}`}>
          <span>{r.name}</span>
          <div className="t"><div className="f" style={{ width: `${(r.count / max) * 100}%`, background: color }} /></div>
          <b>{r.count}</b>
        </div>
      ))}
    </div>
  )
}

export function Hash({ h, n = 12 }) {
  if (!h) return null
  return <span className="mono" title={h}>{h.slice(0, n)}…</span>
}

export function Err({ msg }) {
  return msg ? <div className="banner bad">{msg}</div> : null
}

// Mongolian convention: YYYY.MM.DD HH:mm (local time)
export const fmt = (iso) => {
  const d = new Date(iso)
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}.${p(d.getMonth() + 1)}.${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}
