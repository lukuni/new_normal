import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { fmt } from '../components/ui.jsx'

const STEPS = [
  ['1', 'Санал илгээх', 'Залуучууд санал бодлоо энгийн хэлээр бичнэ.'],
  ['2', 'AI ангилал', 'Сэдэв, хандлага, яаралтай байдлаар автоматаар ангилна.'],
  ['3', 'Хэш бүртгэл', 'Санал бүр өөрчлөгдөшгүй баримт болж бүртгэгдэнэ.'],
  ['4', 'Бодлогын тайлан', 'Шийдвэр гаргагчид нэгтгэсэн дүгнэлт авна.'],
  ['5', 'Иргэнд хариу', 'Санал тань хэрхэн тусгагдсаныг баримтаараа шалгана.'],
]

export default function Home() {
  const [cons, setCons] = useState([])
  const [stats, setStats] = useState(null)
  useEffect(() => {
    api.consultations().then(setCons).catch(() => {})
    api.stats().then(setStats).catch(() => {})
  }, [])

  return (
    <div className="grid">
      <section className="hero card">
        <div>
          <h2>Таны санал шийдвэрт хүрэх ёстой.</h2>
          <p>Хуулийн төсөл, бодлогын хэлэлцүүлэгт саналаа илгээ. Систем таны саналыг ангилж, бодлого боловсруулагчдад
            хүргэх бөгөөд таны санал өөрчлөгдөөгүй, хэрхэн тусгагдсаныг та өөрөө баримтаараа шалгах боломжтой.</p>
          <div className="row">
            <a className="btn" href="#/submit">Санал илгээх</a>
            <a className="btn ghost" href="#/receipt">Баримт шалгах</a>
          </div>
        </div>
        {stats && (
          <div className="heroStats">
            <div><b>{stats.total}</b><span>санал</span></div>
            <div><b>{stats.by_category.length}</b><span>сэдэв</span></div>
            <div><b>{stats.reflected}</b><span>тусгагдсан</span></div>
          </div>
        )}
      </section>

      <section className="card">
        <h2>Систем хэрхэн ажилладаг вэ?</h2>
        <div className="steps">
          {STEPS.map(([n, t, d]) => (
            <div className="stepCard" key={n}><b>{n}</b><h3>{t}</h3><p>{d}</p></div>
          ))}
        </div>
      </section>

      <section className="card">
        <h2>Нээлттэй хэлэлцүүлгүүд</h2>
        {cons.length === 0 && <p className="muted">Хэлэлцүүлэг алга.</p>}
        <div className="consList">
          {cons.map((c) => (
            <div className="cons" key={c.id}>
              <div className="row between">
                <h3>{c.title}</h3>
                <span className={`pill ${c.status === 'open' ? 'p-pos' : 'p-neu'}`}>{c.status === 'open' ? 'Нээлттэй' : 'Хаагдсан'}</span>
              </div>
              <p>{c.summary}</p>
              <p className="muted small">{c.organizer} · {c.law_reference} · {c.proposal_count} санал{c.closes_at ? ` · ${fmt(c.closes_at)} хүртэл` : ''}</p>
              {c.status === 'open' && <a className="btn small" href={`#/submit/${c.id}`}>Энэ хэлэлцүүлэгт санал өгөх</a>}
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
