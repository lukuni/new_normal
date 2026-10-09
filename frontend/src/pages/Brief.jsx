import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { Err, fmt } from '../components/ui.jsx'

export default function Brief() {
  const [cons, setCons] = useState([])
  const [cid, setCid] = useState('')
  const [b, setB] = useState(null)
  const [err, setErr] = useState('')

  useEffect(() => { api.consultations().then(setCons).catch(() => {}) }, [])
  useEffect(() => { setB(null); api.brief(cid).then(setB).catch((e) => setErr(e.message)) }, [cid])

  return (
    <div className="card brief">
      <div className="row between toolbar noprint">
        <h2 className="m0">Автомат бодлогын зөвлөмж</h2>
        <div className="row">
          <select value={cid} onChange={(e) => setCid(e.target.value)} className="auto">
            <option value="">Бүх санал</option>
            {cons.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
          </select>
          <button className="btn ghost" onClick={() => window.print()}>Хэвлэх / PDF</button>
        </div>
      </div>
      <Err msg={err} />
      {b && (
        <>
          <h3 className="briefTitle">{b.title}</h3>
          {b.period && <p className="muted">Хамрах хүрээ: {b.total} санал · {fmt(b.period.from)} – {fmt(b.period.to)} · хэш бүртгэлээр баталгаажсан</p>}
          <h3>Гол дүгнэлт</h3>
          <p>{b.summary}</p>
          {b.sections.map((s, i) => (
            <section key={s.category}>
              <h3>{i + 1}. {s.category} — {s.count} санал ({s.share}%, сөрөг {s.negative_share}%)</h3>
              {s.quotes.map((q, k) => (
                <blockquote key={k}>“{q.text}” <span className="muted">— {q.age_group} нас, {q.location}</span>
                  {q.block_hash && <> · <a href={`#/receipt/${q.block_hash}`} className="mono small">{q.block_hash.slice(0, 10)}…</a></>}
                </blockquote>
              ))}
              <p><b>Санал болгож буй арга хэмжээ:</b> {s.recommendation}</p>
            </section>
          ))}
          <p className="note">{b.note}</p>
        </>
      )}
    </div>
  )
}
