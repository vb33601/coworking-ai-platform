export interface Workspace {
  id: string
  name: string
  provider: string
  city: string
  area: string
  address: string
  workspace_type: string
  seating_capacity: number
  available_seats: number
  price_per_seat_inr: number
  amenities: string[]
  meeting_rooms: number
  cabins: number
  parking_capacity: number
  is_24_7: boolean
  latitude: number
  longitude: number
  trust_score: number
}

export interface Recommendation {
  workspace_id: string
  workspace_name?: string
  provider?: string
  rank: number
  overall_score: number
  scores: Record<string, number>
  reasoning: string
  pros: string[]
  cons: string[]
  cost_breakdown?: Record<string, any>
  location?: { city: string; area: string; address: string }
  workspace_type?: string
  seating_capacity?: number
  available_seats?: number
  price_per_seat_inr?: number
  amenities?: string[]
  meeting_rooms?: number
  cabins?: number
  parking_capacity?: number
  is_24_7?: boolean
  trust_score?: number
  latitude?: number
  longitude?: number
  negotiation_points?: string[]
  risk_analysis?: string[]
  nearby_facilities?: Record<string, string>
  commute_insights?: Record<string, any>
  expansion_possibilities?: Record<string, any>
}

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  agent?: string
  recommendations?: Recommendation[]
  isLoading?: boolean
}

export interface SearchResult {
  search_job_id: string
  status: string
  recommendations: Recommendation[]
  summary: string
  total_cost_estimate?: number
  ambiguity_flags?: any[]
}
