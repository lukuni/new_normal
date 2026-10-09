import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { Err, Pill, StatusPill, fmt } from '../components/ui.jsx'

const FLOW = ['received', 'reviewed', 'reflected']
const FLOW_LABEL = { received: 'Хүлээн авсан', reviewed: 'Хянагдсан', reflected: 'Тусгагдсан' }

export default function Receipt({ arg }) {
  const [hash, setHash] = useState(arg || '')
  const [res, setRes] = useState(null)
  const [proof, setProof] = useState(null)
  const [err, setErr] = useState('')
  const [secret, setSecret] = useState('')
  const [msg, setMsg] = useState('')

  async function check(h = hash) {
    setErr(''); setRes(null); setProof(null); setMsg('')
    try {
      const r = await api.receipt(h.trim())
      setRes(r)
      api.proof(h.trim()).then(setProof).catch(() => setProof(null))
    } catch (e) { setErr(e.message) }
  }
  useEffect(() => { if (arg) check(arg) }, [arg]) // eslint-disable-line react-hooks/exhaustive-deps

  async function erase() {
    if (!window.confirm('Саналын бичвэр бүрмөсөн устгагдана. Үргэлжлүүлэх үү?')) return
    try { const r = await api.erase(res.block_hash, secret); setMsg(r.message); check(res.block_hash) } catch (e) { setErr(e.message) }
  }

  const step = res ? (res.status === 'not_reflected' ? 1 : FLOW.indexOf(res.status)) : -1
  return (
    <div className="grid g2">
      <div className="card">
        <h2>Саналаа шалгах</h2>
        <p className="muted">Санал илгээхэд авсан баримтын кодоо (64 тэмдэгт) оруулна уу.</p>
        <form onSubmit={(e) => { e.preventDefault(); check() }} className="row">
          <input value={hash} onChange={(e) => setHash(e.target.value)} placeholder="Баримтын код" className="grow mono" />
          <button className="btn">Шалгах</button>
        </form>
        <Err msg={err} />
        {msg && <div className="banner ok">{msg}</div>}
      </div>

      {res && (
        <div className="card">
          <div className={`banner ${res.integrity === 'intact' ? 'ok' : res.integrity === 'erased' ? 'neu' : 'bad'}`}>
            {res.integrity === 'intact' && '✓ Таны санал бүртгэгдсэн цагаасаа хойш өөрчлөгдөөгүй байна.'}
            {res.integrity === 'modified' && '✗ Анхааруулга: саналын агуулга бүртгэлтэй таарахгүй байна!'}
            {res.integrity === 'erased' && 'Саналын бичвэр таны хүсэлтээр устгагдсан. Бүртгэлийн хэш хэвээр.'}
          </div>
          <div className="timeline">
            {FLOW.map((s, i) => (
              <div key={s} className={`tl ${i <= step ? 'done' : ''}`}><span>{i + 1}</span>{FLOW_LABEL[s]}</div>
            ))}
          </div>
          <table className="kv"><tbody>
            <tr><th>Төлөв</th><td><StatusPill s={res.status} /></td></tr>
            <tr><th>Хариу</th><td>{res.response_note || <span className="muted">Хариу хараахан ирээгүй</span>}</td></tr>
            <tr><th>Сэдэв</th><td><Pill kind="cat">{res.category}</Pill></td></tr>
            {res.consultation_title && <tr><th>Хэлэлцүүлэг</th><td>{res.consultation_title}</td></tr>}
            <tr><th>Илгээсэн</th><td>{fmt(res.created_at)}</td></tr>
            <tr><th>Блок</th><td>#{res.block_index}</td></tr>
            <tr><th>Сүлжээнд баталгаажсан</th><td>{proof ? (proof.valid ? `Тийм — Merkle root ${proof.root.slice(0, 12)}…${proof.tx_hash ? `, tx ${proof.tx_hash.slice(0, 10)}…` : ' (локал anchor)'}` : 'Үгүй') : <span className="muted">Дараагийн anchor-д орно</span>}</td></tr>
          </tbody></table>
          {res.integrity !== 'erased' && (
            <details>
              <summary>Саналаа устгуулах</summary>
              <div className="row">
                <input value={secret} onChange={(e) => setSecret(e.target.value)} placeholder="Нууц код" className="grow mono" />
                <button className="btn danger" onClick={erase} disabled={secret.length < 8}>Устгах</button>
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  )
}
