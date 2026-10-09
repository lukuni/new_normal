import React, { useEffect, useState } from 'react'
import { api } from './api.js'
import Home from './pages/Home.jsx'
import Submit from './pages/Submit.jsx'
import Receipt from './pages/Receipt.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Ledger from './pages/Ledger.jsx'
import Brief from './pages/Brief.jsx'
import Admin from './pages/Admin.jsx'

const ROUTES = [
  ['home', 'Нүүр', Home],
  ['submit', 'Санал илгээх', Submit],
  ['receipt', 'Баримт шалгах', Receipt],
  ['dashboard', 'Хяналтын самбар', Dashboard],
  ['ledger', 'Блокчейн бүртгэл', Ledger],
  ['brief', 'Бодлогын зөвлөмж', Brief],
  ['admin', 'Админ', Admin],
]

function currentRoute() {
  const [name, ...rest] = window.location.hash.replace(/^#\/?/, '').split('/')
  return { name: ROUTES.some((r) => r[0] === name) ? name : 'home', arg: rest.join('/') }
}

export default function App() {
  const [route, setRoute] = useState(currentRoute())
  const [health, setHealth] = useState(null)

  useEffect(() => {
    const on = () => setRoute(currentRoute())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  useEffect(() => { api.health().then(setHealth).catch(() => setHealth(false)) }, [route.name])

  const Page = ROUTES.find((r) => r[0] === route.name)[2]
  return (
    <>
      <header>
        <a className="brand" href="#/home">
          <div className="logo">ЗД</div>
          <div>
            <h1>Залуу Дуу Хоолой</h1>
            <small>Залуучуудын бодлогын санал · хиймэл оюун · блокчейн бүртгэл</small>
          </div>
        </a>
        <div className="chainstat">
          {health === false ? 'Сервертэй холбогдсонгүй' : health ? `Блок: ${health.blocks} · ангилагч: ${health.classifier === 'llm' ? 'LLM' : 'дүрэм'}` : '…'}
        </div>
      </header>
      <nav>
        {ROUTES.map(([key, label]) => (
          <a key={key} href={`#/${key}`} className={route.name === key ? 'active' : ''}>{label}</a>
        ))}
      </nav>
      <main><Page arg={route.arg} /></main>
      <footer>Залуу Дуу Хоолой · Нээлттэй эхийн судалгааны прототип · Саналын бичвэр блокчейнд бичигдэхгүй, зөвхөн хэш бүртгэгдэнэ.</footer>
    </>
  )
}
