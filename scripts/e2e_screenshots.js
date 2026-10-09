// End-to-end walkthrough of the web app; saves screenshots to docs/screenshots.
// Usage: backend on :8000 (ADMIN_TOKEN=demo-admin, DEMO_MODE=true) + `npm run dev` in frontend,
// then: node scripts/e2e_screenshots.js
const path = require('path')
let chromium
try { ({ chromium } = require('playwright')) } catch { ({ chromium } = require('/opt/npm-tools/node_modules/playwright')) }

const BASE = process.env.WEB_URL || 'http://localhost:5173'
const OUT = path.join(__dirname, '..', 'docs', 'screenshots')

;(async () => {
  require('fs').mkdirSync(OUT, { recursive: true })
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } })
  const errors = []
  page.on('pageerror', (e) => errors.push(e.message))
  const shot = (n) => page.screenshot({ path: path.join(OUT, n + '.png'), fullPage: false })
  const expect = async (sel, what) => { await page.waitForSelector(sel, { timeout: 8000 }).catch(() => { throw new Error('missing: ' + what) }) }

  await page.goto(BASE + '/#/home'); await expect('.cons', 'consultations'); await shot('01_home')

  await page.goto(BASE + '/#/submit'); await page.waitForTimeout(500)
  await page.selectOption('select >> nth=0', { index: 1 })
  await page.fill('textarea', 'Оюутнуудын дотуур байр маш хүрэлцэхгүй, түрээсийн үнэ өндөр байна. Шинэ дотуур байр яаралтай барих хэрэгтэй. Утас 99112233')
  await page.click('button.btn:has-text("Илгээх")'); await expect('.receipt', 'receipt'); await shot('02_submit_receipt')
  const blockHash = (await page.locator('.receipt .mono.box').first().innerText()).trim()
  if (!/^[0-9a-f]{64}$/.test(blockHash)) throw new Error('bad receipt hash')

  await page.goto(BASE + '/#/receipt/' + blockHash); await expect('.timeline', 'receipt status'); await shot('03_receipt_check')
  const okText = await page.locator('.banner').first().innerText()
  if (!okText.includes('өөрчлөгдөөгүй')) throw new Error('receipt not intact')

  await page.goto(BASE + '/#/dashboard'); await expect('.kpi', 'kpis'); await page.waitForTimeout(600); await shot('04_dashboard')

  // admin: login, respond to the new proposal, anchor
  await page.goto(BASE + '/#/admin'); await page.fill('input[type=password]', 'demo-admin'); await page.click('button:has-text("Хадгалах")')
  await page.waitForTimeout(600)
  const firstRow = page.locator('tbody tr').first()
  await firstRow.locator('input').fill('Таны саналыг төслийн 4.2 заалтад тусгалаа.')
  await firstRow.locator('button:has-text("Тусгагдсан")').click(); await page.waitForTimeout(600)
  await page.click('button:has-text("Anchor үүсгэх")'); await page.waitForTimeout(600); await shot('05_admin')

  await page.goto(BASE + '/#/receipt/' + blockHash); await expect('.timeline', 'receipt status'); await page.waitForTimeout(600); await shot('06_receipt_reflected')
  const st = await page.locator('table.kv').innerText()
  if (!st.includes('Тусгагдсан') || !st.includes('4.2')) throw new Error('feedback loop failed')

  await page.goto(BASE + '/#/ledger'); await expect('tbody tr', 'ledger')
  await page.click('button:has-text("Бүрэн бүтэн")'); await expect('.banner.ok', 'verify ok')
  await page.click('button:has-text("Демо: саналыг")'); await expect('.banner.bad', 'tamper detected'); await shot('07_ledger_tamper_detected')
  await page.click('button:has-text("Сэргээх")'); await expect('.banner.ok', 'restored')

  await page.goto(BASE + '/#/brief'); await expect('blockquote', 'brief'); await shot('08_policy_brief')

  await page.setViewportSize({ width: 390, height: 844 }); await page.goto(BASE + '/#/submit'); await page.waitForTimeout(500); await shot('09_mobile_submit')

  await browser.close()
  if (errors.length) throw new Error('page errors: ' + errors.join(' | '))
  console.log('E2E OK — screenshots in docs/screenshots')
})().catch((e) => { console.error('E2E FAILED:', e.message); process.exit(1) })
