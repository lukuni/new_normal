import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { Bars, Err, Pill, UrgPill, fmt } from '../components/ui.jsx'

const SENT_COLOR = { 'Сөрөг': '#d9534f', 'Төвийг сахисан': '#9aa3b2', 'Эерэг': '#1f9d6b' }

export default function Dashboard() {
  const [cons, setCons] = useState([])
  const [cid, setCid] = useState('')
  const [s, setS] = useState(null)
  const [urgent, setUrgent] = useState([])
  const [err, setErr] = useState('')

  useEffect(() => { api.consultations().then(setCons).catch(() => {}) }, [])
  useEffect(() => {
    api.stats(cid).then(setS).catch((e) => setErr(e.message))
    api.proposals(`?urgency=Өндөр&limit=8${cid ? `&consultation_id=${cid}` : ''}`).then(setUrgent).catch(() => {})
  }, [cid])

  if (err) return <Err msg={err} />
  if (!s) return <p className="muted">Ачаалж байна…</p>
  const n = s.total || 1
  return (
    <div className="grid">
      <div className="row between">
        <h2 className="m0">Хяналтын самбар</h2>
        <select value={cid} onChange={(e) => setCid(e.target.value)} className="auto">
          <option value="">Бүх санал</option>
          {cons.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
        </select>
      </div>
      <div className="grid g4">
        {[[s.total, 'Нийт санал'], [s.by_category.length, 'Сэдэв'], [s.urgent, 'Яаралтай санал'], [s.reflected, 'Шийдвэрт тусгагдсан']].map(([v, l]) => (
          <div className="card kpi" key={l}><div className="v">{v}</div><div className="l">{l}</div></div>
        ))}
      </div>
      <div className="grid g2e">
        <div className="card"><h2>Сэдвийн ангиллаар</h2><Bars rows={s.by_category} /></div>
        <div className="card">
          <h2>Хандлагын тархалт</h2>
          <div className="stack">
            {s.by_sentiment.map((x) => <div key={x.name} title={`${x.name}: ${x.count}`} style={{ width: `${(x.count / n) * 100}%`, background: SENT_COLOR[x.name] }} />)}
          </div>
          <div className="legend">
            {s.by_sentiment.map((x) => <span key={x.name}><i className="dot" style={{ background: SENT_COLOR[x.name] }} />{x.name} {Math.round((x.count / n) * 100)}%</span>)}
          </div>
          <h2 className="mt">Байршлаар</h2><Bars rows={s.by_location} color="#21a88a" />
        </div>
      </div>
      <div className="grid g2e">
        <div className="card"><h2>Насны бүлгээр</h2><Bars rows={s.by_age} color="#7a5af5" /></div>
        <div className="card"><h2>Шийдвэрлэлтийн төлөв</h2><Bars rows={s.by_status.map((x) => ({ ...x, name: { received: 'Хүлээн авсан', reviewed: 'Хянагдсан', reflected: 'Тусгагдсан', not_reflected: 'Тусгагдаагүй' }[x.name] || x.name }))} color="#e07b00" /></div>
      </div>
      <div className="card">
        <h2>Яаралтай анхаарах саналууд</h2>
        <table>
          <thead><tr><th>Огноо</th><th>Санал</th><th>Сэдэв</th><th>Байршил</th><th>Яаралтай</th></tr></thead>
          <tbody>
            {urgent.filter((p) => p.text).map((p) => (
              <tr key={p.id}><td className="nowrap">{fmt(p.created_at)}</td><td>{p.text}</td><td><Pill kind="cat">{p.category}</Pill></td><td>{p.location}</td><td><UrgPill u={p.urgency} /></td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
