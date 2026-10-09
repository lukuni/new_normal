import React, { useEffect, useState } from 'react'
import { api, getAdminToken } from '../api.js'
import { Err, Hash, fmt } from '../components/ui.jsx'

const PROBLEM = {
  content_modified: 'саналын агуулга өөрчлөгдсөн', block_modified: 'блокийн талбар өөрчлөгдсөн',
  broken_link: 'гинжин холбоос тасарсан', missing_block_before: 'өмнөх блок дутсан', proposal_missing: 'санал устсан',
}

export default function Ledger() {
  const [data, setData] = useState(null)
  const [anchors, setAnchors] = useState([])
  const [v, setV] = useState(null)
  const [err, setErr] = useState('')
  const isAdmin = !!getAdminToken()

  const load = () => {
    api.ledger(200).then(setData).catch((e) => setErr(e.message))
    api.anchors().then(setAnchors).catch(() => {})
  }
  useEffect(load, [])

  async function verify() { setErr(''); try { setV(await api.verify()) } catch (e) { setErr(e.message) } }
  async function tamper() {
    const target = data.blocks[data.blocks.length - 4] || data.blocks[0]
    try { await api.tamper(target.proposal_id); setV(null); await verify() } catch (e) { setErr(e.message) }
  }
  async function restore() { try { await api.restore(); await verify() } catch (e) { setErr(e.message) } }

  const bad = new Map((v?.issues || []).map((i) => [i.index, i.problems]))
  return (
    <div className="grid">
      {v && (v.ok
        ? <div className="banner ok">✓ Бүх {v.checked} блок баталгаатай.{v.erased ? ` (${v.erased} санал эзнийхээ хүсэлтээр хуулийн дагуу устгагдсан)` : ''}</div>
        : <div className="banner bad">✗ Зөрчил илэрлээ: {v.issues.map((i) => `блок #${i.index} — ${i.problems.map((p) => PROBLEM[p] || p).join(', ')}`).join('; ')}</div>)}
      <Err msg={err} />
      <div className="card">
        <div className="row between toolbar">
          <h2 className="m0">Хэш гинжин бүртгэл {data && <span className="muted">({data.total} блок)</span>}</h2>
          <div className="row btns">
            <button className="btn" onClick={verify}>Бүрэн бүтэн байдлыг шалгах</button>
            {isAdmin && <button className="btn danger" onClick={tamper}>Демо: саналыг нууцаар засах</button>}
            {isAdmin && <button className="btn ghost" onClick={restore}>Сэргээх</button>}
          </div>
        </div>
        <div className="scroll">
          <table className="rtable">
            <thead><tr><th>#</th><th>Цаг</th><th>Сэдэв</th><th>Агуулгын хэш</th><th>Өмнөх хэш</th><th>Блокийн хэш</th><th>Төлөв</th></tr></thead>
            <tbody>
              {data?.blocks.map((b) => (
                <tr key={b.index} className={bad.has(b.index) ? 'broken' : ''}>
                  <td data-label="#">{b.index}</td><td data-label="Цаг" className="nowrap">{fmt(b.timestamp)}</td><td data-label="Сэдэв">{b.category}</td>
                  <td data-label="Агуулгын хэш"><Hash h={b.content_hash} /></td><td data-label="Өмнөх хэш"><Hash h={b.prev_hash} /></td>
                  <td data-label="Блокийн хэш"><a href={`#/receipt/${b.block_hash}`}><Hash h={b.block_hash} /></a></td>
                  <td data-label="Төлөв">{!v ? <span className="muted">—</span> : bad.has(b.index) ? <span className="pill p-neg">Зөрчил</span> : <span className="pill p-pos">Баталгаатай</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="note">Блокчейн-д саналын бичвэр биш, зөвхөн агуулгын хэш, сэдэв, цаг, өмнөх блокийн хэш хадгалагдана (on-chain/off-chain эрлийз загвар).</p>
      </div>
      <div className="card">
        <h2>Нийтийн блокчейнд баталгаажуулалт (Merkle anchor)</h2>
        <p className="muted small">Олон блокийг нэг Merkle root болгон нэгтгэж, ухаалаг гэрээгээр нийтийн сүлжээнд нэг гүйлгээгээр бичнэ.</p>
        <table className="rtable">
          <thead><tr><th>#</th><th>Блокууд</th><th>Merkle root</th><th>Сүлжээ</th><th>Гүйлгээ</th><th>Огноо</th></tr></thead>
          <tbody>
            {anchors.map((a) => (
              <tr key={a.id}><td data-label="#">{a.id}</td><td data-label="Блокууд">{a.from_index}–{a.to_index}</td><td data-label="Merkle root"><Hash h={a.merkle_root} n={16} /></td><td data-label="Сүлжээ">{a.network}</td><td data-label="Гүйлгээ">{a.tx_hash ? <Hash h={a.tx_hash} /> : <span className="muted">—</span>}</td><td data-label="Огноо">{fmt(a.created_at)}</td></tr>
            ))}
            {anchors.length === 0 && <tr><td colSpan="6" className="muted">Anchor хараахан хийгдээгүй (Админ хэсгээс хийнэ).</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}
