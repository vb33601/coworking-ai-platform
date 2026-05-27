import axios from 'axios'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 120000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export async function searchWorkspaces(rawInput: string) {
  const { data } = await api.post('/api/v1/orchestrator/search', {
    tenant_id: 'demo',
    user_id: 'demo',
    raw_input: rawInput,
    context: { use_ai: true }
  })
  return data
}

export async function fetchWorkspaces(params: Record<string, any> = {}) {
  const { data } = await api.get('/api/v1/search/workspaces', { params })
  return data
}

export async function fetchProviders() {
  const { data } = await api.get('/api/v1/search/providers')
  return data
}

export async function calculatePricing(payload: any) {
  const { data } = await api.post('/api/v1/pricing/calculate', payload)
  return data
}

export async function scheduleVisit(payload: {
  workspace_id: string
  workspace_name: string
  visitor_name: string
  visitor_email: string
  visitor_mobile: string
  visitor_address: string
  visit_date: string
  visit_time: string
  team_size?: number
  notes?: string
}) {
  const { data } = await api.post('/api/v1/orchestrator/schedule-visit', payload)
  return data
}

export async function downloadProposal(payload: any) {
  const { data } = await api.post('/api/v1/orchestrator/proposal', payload)
  return data
}
