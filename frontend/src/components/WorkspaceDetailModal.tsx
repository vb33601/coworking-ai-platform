'use client'

import { useState } from 'react'
import { Recommendation } from '@/types'
import { useAppStore } from '@/stores/appStore'
import { downloadProposal } from '@/lib/api'
import {
  X, MapPin, Star, Users, DollarSign, Check, AlertTriangle,
  TrendingUp, Car, Wifi, Clock, Building2, Phone, Mail,
  Train, Shield, ChevronRight, BarChart3,
  FileText, MessageSquare, Loader2
} from 'lucide-react'
import toast from 'react-hot-toast'

export default function WorkspaceDetailModal() {
  const { selectedWorkspace, detailModalOpen, closeDetailModal, openScheduleModal } = useAppStore()
  const [downloading, setDownloading] = useState(false)

  if (!detailModalOpen || !selectedWorkspace) return null

  const rec = selectedWorkspace
  const scores = rec.scores || {}
  const cost = rec.cost_breakdown || {}
  const location = rec.location || { city: '', area: '', address: '' }
  const negotiation = rec.negotiation_points || []
  const risks = rec.risk_analysis || []
  const nearby = rec.nearby_facilities || {}
  const commute = rec.commute_insights || {}
  const expansion = rec.expansion_possibilities || {}

  const handleDownload = async () => {
    setDownloading(true)
    try {
      const data = await downloadProposal({
        workspace_id: rec.workspace_id,
        workspace_name: rec.workspace_name,
        provider: rec.provider,
        city: location.city,
        area: location.area,
        address: location.address,
        workspace_type: rec.workspace_type,
        seating_capacity: rec.seating_capacity,
        available_seats: rec.available_seats,
        price_per_seat_inr: rec.price_per_seat_inr,
        amenities: rec.amenities,
        meeting_rooms: rec.meeting_rooms,
        cabins: rec.cabins,
        parking_capacity: rec.parking_capacity,
        is_24_7: rec.is_24_7,
        trust_score: rec.trust_score,
        overall_score: rec.overall_score,
        scores: rec.scores,
        reasoning: rec.reasoning,
        pros: rec.pros,
        cons: rec.cons,
        cost_breakdown: rec.cost_breakdown,
        negotiation_points: rec.negotiation_points,
        risk_analysis: rec.risk_analysis,
        nearby_facilities: rec.nearby_facilities,
        commute_insights: rec.commute_insights,
        expansion_possibilities: rec.expansion_possibilities,
        team_size: rec.seating_capacity || 10,
      })
      
      // Decode base64 and download
      const byteCharacters = atob(data.pdf_base64)
      const byteNumbers = new Array(byteCharacters.length)
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i)
      }
      const byteArray = new Uint8Array(byteNumbers)
      const blob = new Blob([byteArray], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = data.filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      
      toast.success('Proposal downloaded!')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to generate proposal')
    } finally {
      setDownloading(false)
    }
  }

  const amenityIcons: Record<string, React.ReactNode> = {
    internet: <Wifi className="w-3.5 h-3.5" />,
    meeting_rooms: <Users className="w-3.5 h-3.5" />,
    cafeteria: <CoffeeIcon />,
    parking: <Car className="w-3.5 h-3.5" />,
    recreation: <Star className="w-3.5 h-3.5" />,
    '24_7': <Clock className="w-3.5 h-3.5" />,
    server_room: <Shield className="w-3.5 h-3.5" />,
    branding: <Building2 className="w-3.5 h-3.5" />,
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="sticky top-0 bg-gray-900/95 backdrop-blur border-b border-gray-700 px-6 py-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
              <Building2 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="font-semibold text-lg text-white">{rec.workspace_name || 'Workspace Detail'}</h2>
              <p className="text-xs text-gray-400 flex items-center gap-1">
                <MapPin className="w-3 h-3" /> {location.area}, {location.city}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-center">
              <span className="text-2xl font-bold text-primary-400">{Math.round(rec.overall_score)}</span>
              <p className="text-[10px] text-gray-500 uppercase">Score</p>
            </div>
            <button
              onClick={closeDetailModal}
              className="w-8 h-8 rounded-lg bg-gray-800 hover:bg-gray-700 flex items-center justify-center transition-colors"
            >
              <X className="w-4 h-4 text-gray-400" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Overview Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <InfoCard icon={<Users className="w-4 h-4 text-primary-400" />} label="Capacity" value={`${rec.seating_capacity || '-'} seats`} />
            <InfoCard icon={<DollarSign className="w-4 h-4 text-green-400" />} label="Per Seat" value={`₹${(rec.price_per_seat_inr || 0).toLocaleString()}`} />
            <InfoCard icon={<MapPin className="w-4 h-4 text-blue-400" />} label="Type" value={rec.workspace_type || '-'} />
            <InfoCard icon={<Star className="w-4 h-4 text-yellow-400" />} label="Trust Score" value={`${rec.trust_score || '-'}/5`} />
          </div>

          {/* Score Breakdown */}
          <Section title="Score Breakdown" icon={<BarChart3 className="w-4 h-4 text-primary-400" />}>
            <div className="space-y-2">
              {Object.entries(scores).map(([key, value]) => (
                <div key={key} className="flex items-center gap-3">
                  <span className="text-xs text-gray-400 w-32 capitalize">{key.replace(/_/g, ' ')}</span>
                  <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full" style={{ width: `${Math.round(value as number)}%` }} />
                  </div>
                  <span className="text-xs text-white w-8 text-right">{Math.round(value as number)}</span>
                </div>
              ))}
            </div>
          </Section>

          {/* Cost Breakdown */}
          {Object.keys(cost).length > 0 && (
            <Section title="Cost Breakdown" icon={<DollarSign className="w-4 h-4 text-green-400" />}>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {Object.entries(cost).map(([key, value]) => (
                  <div key={key} className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
                    <p className="text-[10px] text-gray-500 uppercase">{key.replace(/_/g, ' ')}</p>
                    <p className="text-sm font-semibold text-white">{typeof value === 'number' ? `₹${(value as number).toLocaleString()}` : String(value)}</p>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Amenities */}
          <Section title="Amenities" icon={<Check className="w-4 h-4 text-green-400" />}>
            <div className="flex flex-wrap gap-2">
              {(rec.amenities || []).map((amenity) => (
                <span key={amenity} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800 border border-gray-700 text-xs text-gray-300">
                  {amenityIcons[amenity] || <Check className="w-3.5 h-3.5" />}
                  {amenity.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          </Section>

          {/* Pros & Cons */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Section title="Pros" icon={<Check className="w-4 h-4 text-green-400" />}>
              <ul className="space-y-2">
                {(rec.pros || []).map((pro, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                    <Check className="w-4 h-4 text-green-400 shrink-0 mt-0.5" />
                    {pro}
                  </li>
                ))}
              </ul>
            </Section>
            <Section title="Cons" icon={<AlertTriangle className="w-4 h-4 text-red-400" />}>
              <ul className="space-y-2">
                {(rec.cons || []).map((con, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                    <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                    {con}
                  </li>
                ))}
              </ul>
            </Section>
          </div>

          {/* Reasoning */}
          <Section title="AI Reasoning" icon={<MessageSquare className="w-4 h-4 text-primary-400" />}>
            <p className="text-sm text-gray-300 leading-relaxed bg-gray-800/50 rounded-lg p-4 border border-gray-700">
              {rec.reasoning}
            </p>
          </Section>

          {/* Negotiation Points */}
          {negotiation.length > 0 && (
            <Section title="Negotiation Points" icon={<TrendingUp className="w-4 h-4 text-blue-400" />}>
              <div className="space-y-2">
                {negotiation.map((point, i) => (
                  <div key={i} className="flex items-start gap-3 bg-blue-500/5 border border-blue-500/20 rounded-lg p-3">
                    <TrendingUp className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                    <p className="text-sm text-gray-300">{point}</p>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Risk Analysis */}
          {risks.length > 0 && (
            <Section title="Risk Analysis" icon={<Shield className="w-4 h-4 text-red-400" />}>
              <div className="space-y-2">
                {risks.map((risk, i) => (
                  <div key={i} className="flex items-start gap-3 bg-red-500/5 border border-red-500/20 rounded-lg p-3">
                    <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                    <p className="text-sm text-gray-300">{risk}</p>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Nearby Facilities */}
          {Object.keys(nearby).length > 0 && (
            <Section title="Nearby Facilities" icon={<MapPin className="w-4 h-4 text-green-400" />}>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {Object.entries(nearby).map(([key, value]) => (
                  <div key={key} className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
                    <p className="text-[10px] text-gray-500 uppercase">{key.replace(/_/g, ' ')}</p>
                    <p className="text-xs text-gray-300 mt-1">{String(value)}</p>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Commute Insights */}
          {Object.keys(commute).length > 0 && (
            <Section title="Commute & Accessibility" icon={<Train className="w-4 h-4 text-purple-400" />}>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {Object.entries(commute).map(([key, value]) => (
                  <div key={key} className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
                    <p className="text-[10px] text-gray-500 uppercase">{key.replace(/_/g, ' ')}</p>
                    <p className="text-xs text-gray-300 mt-1">{typeof value === 'number' ? `${value} km` : String(value)}</p>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Expansion */}
          {Object.keys(expansion).length > 0 && (
            <Section title="Expansion Possibilities" icon={<TrendingUp className="w-4 h-4 text-accent-400" />}>
              <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700 space-y-3">
                {expansion.adjacent_space && (
                  <p className="text-sm text-gray-300 flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-accent-400" />
                    {String(expansion.adjacent_space)}
                  </p>
                )}
                {expansion.scalability_score && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400">Scalability Score:</span>
                    <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden max-w-[200px]">
                      <div className="h-full bg-accent-500 rounded-full" style={{ width: `${Math.min(100, Number(expansion.scalability_score))}%` }} />
                    </div>
                    <span className="text-xs text-accent-400">{Math.round(Number(expansion.scalability_score))}/100</span>
                  </div>
                )}
                {Array.isArray(expansion.nearby_locations) && (
                  <div className="space-y-1">
                    <p className="text-xs text-gray-500">Nearby Locations:</p>
                    {expansion.nearby_locations.map((loc: string, i: number) => (
                      <p key={i} className="text-xs text-gray-300 flex items-center gap-1">
                        <ChevronRight className="w-3 h-3 text-gray-500" /> {loc}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            </Section>
          )}

          {/* Contact / Action */}
          <div className="flex gap-3 pt-2">
            <button
              onClick={openScheduleModal}
              className="flex-1 py-3 bg-primary-600 hover:bg-primary-500 text-white text-sm font-medium rounded-xl transition-colors flex items-center justify-center gap-2"
            >
              <Phone className="w-4 h-4" />
              Schedule Visit
            </button>
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="flex-1 py-3 bg-gray-800 hover:bg-gray-700 disabled:opacity-50 text-white text-sm font-medium rounded-xl transition-colors flex items-center justify-center gap-2 border border-gray-700"
            >
              {downloading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <FileText className="w-4 h-4" />
              )}
              {downloading ? 'Generating PDF...' : 'Download Proposal'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function Section({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-sm font-medium text-white flex items-center gap-2 mb-3">
        {icon}
        {title}
      </h3>
      {children}
    </div>
  )
}

function InfoCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-[10px] text-gray-500 uppercase">{label}</span>
      </div>
      <p className="text-sm font-semibold text-white">{value}</p>
    </div>
  )
}

function CoffeeIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 8h1a4 4 0 1 1 0 8h-1" />
      <path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z" />
      <line x1="6" x2="6" y1="2" y2="4" />
      <line x1="10" x2="10" y1="2" y2="4" />
      <line x1="14" x2="14" y1="2" y2="4" />
    </svg>
  )
}
