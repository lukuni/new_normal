import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { Err, Pill, SentPill, UrgPill } from '../components/ui.jsx'

export default function Submit({ arg }) {
  const [meta, setMeta] = useState(null)
  const [cons, setCons] = useState([])
  const [form, setForm] = useState({ text: '', age_group: '18–24', location: 'Улаанбаатар', consultation_id: arg || '' })
  const [receipt, setReceipt] = useState(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.meta().then(setMeta).catch((e) => setErr(e.message))
    api.consultations().then((c) => setCons(c.filter((x) => x.status === 'open'))).catch(() => {})
  }, [])

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  async function onSubmit(e) {
    e.preventDefault()
    setErr(''); setBusy(true)
    try {
      const body = { ...form, consultation_id: form.consultation_id ? Number(form.consultation_id) : null }
      setReceipt(await api.submit(body))
      setForm({ ...form, text: '' })
    } catch (ex) { setErr(ex.message) } finally { setBusy(false) }
  }

  const copy = (t) => navigator.clipboard?.writeText(t)

  return (
    <div className="grid g2">
      <form className="card" onSubmit={onSubmit}>
        <h2>Бодлогын санал илгээх</h2>
        <label>Хэлэлцүүлэг</label>
        <select value={form.consultation_id} onChange={set('consultation_id')}>
          <option value="">Ерөнхий санал (хэлэлцүүлэггүй)</option>
          {cons.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
        </select>
        <div className="grid g2e tight">
          <div>
            <label>Нас</label>
            <select value={form.age_group} onChange={set('age_group')}>
              {(meta?.age_groups || []).map((a) => <option key={a}>{a}</option>)}
            </select>
          </div>
          <div>
            <label>Байршил</label>
            <select value={form.location} onChange={set('location')}>
              {(meta?.locations || []).map((a) => <option key={a}>{a}</option>)}
            </select>
          </div>
        </div>
        <label>Таны санал (кирилл эсвэл латин галигаар)</label>
        <textarea value={form.text} onChange={set('text')} minLength={10} maxLength={4000} required
          placeholder="Жишээ: Их сургуулийн дотуур байрны тоо хүрэлцэхгүй байгаа тул..." />
        <p className="muted small">Утасны дугаар, регистр, и-мэйл автоматаар нуугдана. Нэр бичих шаардлагагүй.</p>
        <Err msg={err} />
        <button className="btn" disabled={busy}>{busy ? 'Илгээж байна…' : 'Илгээх'}</button>
      </form>

      <div className="card">
        {!receipt ? (
          <>
            <h2>Танд юу ирэх вэ?</h2>
            <p>Санал илгээмэгц танд <b>баримтын код</b> (блокийн хэш) болон <b>нууц код</b> өгөгдөнө.</p>
            <ul className="list">
              <li>Баримтын кодоор саналаа өөрчлөгдөөгүй эсэх, хэрхэн тусгагдсаныг шалгана.</li>
              <li>Нууц кодоор хүссэн үедээ саналаа устгуулна (Хүний хувийн мэдээлэл хамгаалах тухай хууль).</li>
            </ul>
          </>
        ) : (
          <div className="receipt">
            <div className="banner ok">✓ Санал бүртгэгдлээ — блок #{receipt.block_index}</div>
            <div className="row">
              <Pill kind="cat">{receipt.classification.category}</Pill>
              <SentPill s={receipt.classification.sentiment} />
              <UrgPill u={receipt.classification.urgency} />
              <span className="muted small">итгэл {Math.round(receipt.classification.confidence * 100)}% · {receipt.classification.classifier === 'llm' ? 'LLM' : 'дүрэм'}</span>
            </div>
            <label>Баримтын код (блокийн хэш)</label>
            <div className="mono box">{receipt.block_hash}</div>
            <button type="button" className="btn ghost small" onClick={() => copy(receipt.block_hash)}>Хуулах</button>
            <label>Нууц код — зөвхөн одоо харагдана, хадгалж аваарай</label>
            <div className="mono box warn">{receipt.owner_secret}</div>
            <button type="button" className="btn ghost small" onClick={() => copy(`${receipt.block_hash}\n${receipt.owner_secret}`)}>Хоёуланг хуулах</button>
            <label>Агуулгын хэш (SHA-256)</label>
            <div className="mono small">{receipt.content_hash}</div>
            <p><a href={`#/receipt/${receipt.block_hash}`}>Баримтаа шалгах →</a></p>
          </div>
        )}
      </div>
    </div>
  )
}
