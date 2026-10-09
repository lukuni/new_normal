// Thin wrapper around the FastAPI backend.
const BASE = import.meta.env.VITE_API_BASE || ''

export function getAdminToken() {
  try { return localStorage.getItem('adminToken') || '' } catch { return '' }
}
export function setAdminToken(t) {
  try { localStorage.setItem('adminToken', t) } catch { /* storage unavailable */ }
}

async function req(path, { method = 'GET', body, admin = false } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (admin) headers['X-Admin-Token'] = getAdminToken()
  const r = await fetch(BASE + path, { method, headers, body: body ? JSON.stringify(body) : undefined })
  const data = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `Алдаа (${r.status})`)
  return data
}

export const api = {
  health: () => req('/api/health'),
  meta: () => req('/api/meta'),
  consultations: () => req('/api/consultations'),
  createConsultation: (body) => req('/api/consultations', { method: 'POST', body, admin: true }),
  closeConsultation: (id) => req(`/api/consultations/${id}/close`, { method: 'POST', admin: true }),
  submit: (body) => req('/api/proposals', { method: 'POST', body }),
  proposals: (q = '') => req('/api/proposals' + q),
  receipt: (h) => req(`/api/receipts/${encodeURIComponent(h)}`),
  erase: (h, owner_secret) => req(`/api/receipts/${encodeURIComponent(h)}/erase`, { method: 'POST', body: { owner_secret } }),
  stats: (cid) => req('/api/stats' + (cid ? `?consultation_id=${cid}` : '')),
  brief: (cid) => req('/api/brief' + (cid ? `?consultation_id=${cid}` : '')),
  ledger: (limit = 100) => req(`/api/ledger?limit=${limit}`),
  verify: () => req('/api/ledger/verify'),
  anchors: () => req('/api/anchors'),
  createAnchor: () => req('/api/anchors', { method: 'POST', admin: true }),
  proof: (h) => req(`/api/proofs/${h}`),
  updateProposal: (id, body) => req(`/api/admin/proposals/${id}`, { method: 'PATCH', body, admin: true }),
  tamper: (id) => req(`/api/demo/tamper/${id}`, { method: 'POST', admin: true }),
  restore: () => req('/api/demo/restore', { method: 'POST', admin: true }),
}
