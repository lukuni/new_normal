import React, { useEffect, useState } from 'react'
import { api, getAdminToken, setAdminToken } from '../api.js'
import { Err, Pill, SentPill, StatusPill, UrgPill, STATUS_LABEL } from '../components/ui.jsx'

export default function Admin() {
  const [token, setToken] = useState(getAdminToken())
  const [cons, setCons] = useState([])
  const [props, setProps] = useState([])
  const [filter, setFilter] = useState('received')
  const [notes, setNotes] = useState({})
  const [newCons, setNewCons] = useState({ title: '', summary: '', law_reference: '', organizer: '' })
  const [msg, setMsg] = useState('')
  const [err, setErr] = useState('')

  const load = () => {
    api.consultations().then(setCons).catch(() => {})
    api.proposals(`?limit=200${filter ? `&status=${filter}` : ''}`).then(setProps).catch((e) => setErr(e.message))
  }
  useEffect(load, [filter])

  const run = async (fn, ok) => { setErr(''); setMsg(''); try { await fn(); setMsg(ok); load() } catch (e) { setErr(e.message) } }

  return (
    <div className="grid">
      <div className="card">
        <h2>Админ нэвтрэлт</h2>
        <div className="row">
          <input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder="ADMIN_TOKEN" className="grow" />
          <button className="btn" onClick={() => { setAdminToken(token); setMsg('Токен хадгалагдлаа') }}>Хадгалах</button>
        </div>
        {msg && <div className="banner ok">{msg}</div>}
        <Err msg={err} />
      </div>

      <div className="grid g2e">
        <div className="card">
          <h2>Шинэ хэлэлцүүлэг нээх</h2>
          <label>Гарчиг (хуулийн төсөл / бодлого)</label>
          <input value={newCons.title} onChange={(e) => setNewCons({ ...newCons, title: e.target.value })} />
          <label>Товч агуулга</label>
          <textarea value={newCons.summary} onChange={(e) => setNewCons({ ...newCons, summary: e.target.value })} />
          <label>Хууль зүйн үндэслэл</label>
          <input value={newCons.law_reference} onChange={(e) => setNewCons({ ...newCons, law_reference: e.target.value })} placeholder="Хууль тогтоомжийн тухай хууль, 8.1.5" />
          <label>Зохион байгуулагч</label>
          <input value={newCons.organizer} onChange={(e) => setNewCons({ ...newCons, organizer: e.target.value })} />
          <button className="btn mt" onClick={() => run(() => api.createConsultation(newCons), 'Хэлэлцүүлэг нээгдлээ')}>Нээх</button>
          <h3 className="mt">Хэлэлцүүлгүүд</h3>
          {cons.map((c) => (
            <div className="row between line" key={c.id}>
              <span>{c.title} <span className="muted">({c.proposal_count})</span></span>
              {c.status === 'open'
                ? <button className="btn ghost small" onClick={() => run(() => api.closeConsultation(c.id), 'Хаагдлаа')}>Хаах</button>
                : <span className="pill p-neu">Хаагдсан</span>}
            </div>
          ))}
        </div>
        <div className="card">
          <h2>Блокчейн anchor</h2>
          <p>Шинэ блокуудыг Merkle root болгон нэгтгэнэ. Root-ийг <span className="mono">contracts/ProposalRegistry.sol</span> гэрээгээр Sepolia сүлжээнд бичээд гүйлгээний хэшийг API-д бүртгэнэ.</p>
          <button className="btn" onClick={() => run(() => api.createAnchor(), 'Anchor үүслээ')}>Anchor үүсгэх</button>
        </div>
      </div>

      <div className="card">
        <div className="row between toolbar">
          <h2 className="m0">Саналд хариу өгөх</h2>
          <select value={filter} onChange={(e) => setFilter(e.target.value)} className="auto">
            <option value="">Бүгд</option>
            {Object.entries(STATUS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <table className="rtable">
          <thead><tr><th>#</th><th>Санал</th><th>Ангилал</th><th>Төлөв</th><th>Хариу / үйлдэл</th></tr></thead>
          <tbody>
            {props.map((p) => (
              <tr key={p.id}>
                <td data-label="#">{p.id}</td>
                <td data-label="Санал" className="wide">{p.text ?? <span className="muted">(эзнийхээ хүсэлтээр устгагдсан)</span>}<div className="muted small">{p.age_group} · {p.location}</div></td>
                <td data-label="Ангилал"><Pill kind="cat">{p.category}</Pill><br /><SentPill s={p.sentiment} /> <UrgPill u={p.urgency} /></td>
                <td data-label="Төлөв"><StatusPill s={p.status} /></td>
                <td data-label="Хариу" className="actions wide">
                  <input placeholder="Иргэнд өгөх хариу" value={notes[p.id] ?? p.response_note}
                    onChange={(e) => setNotes({ ...notes, [p.id]: e.target.value })} />
                  <div className="row">
                    {['reviewed', 'reflected', 'not_reflected'].map((s) => (
                      <button key={s} className="btn ghost small" onClick={() => run(() => api.updateProposal(p.id, { status: s, response_note: notes[p.id] ?? p.response_note }), 'Шинэчлэгдлээ')}>{STATUS_LABEL[s]}</button>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
