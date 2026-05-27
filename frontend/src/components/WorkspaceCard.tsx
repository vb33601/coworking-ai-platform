import { Recommendation } from '@/types'
import { useAppStore } from '@/stores/appStore'
import { MapPin, Star, Users, DollarSign, Check, X, Building2, Car, Wifi, Clock } from 'lucide-react'

interface Props {
  recommendation: Recommendation
  compact?: boolean
}

export default function WorkspaceCard({ recommendation, compact }: Props) {
  const { openDetailModal } = useAppStore()
  const scores = recommendation.scores || {}

  if (compact) {
    return (
      <div
        onClick={() => openDetailModal(recommendation)}
        className="bg-gray-800/50 border border-gray-700 rounded-lg p-3 hover:border-primary-500/30 transition-colors cursor-pointer"
      >
        <div className="flex items-start justify-between">
          <div>
            <h4 className="font-medium text-sm text-white">{recommendation.workspace_name || `Workspace #${recommendation.rank}`}</h4>
            <div className="flex items-center gap-1 mt-1 text-xs text-gray-400">
              <MapPin className="w-3 h-3" />
              <span>Rank #{recommendation.rank}</span>
            </div>
          </div>
          <div className="text-right">
            <span className="text-lg font-bold text-primary-400">{recommendation.overall_score}</span>
            <p className="text-xs text-gray-500">/100</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div
      onClick={() => openDetailModal(recommendation)}
      className="bg-gray-800/50 border border-gray-700 rounded-xl overflow-hidden hover:border-primary-500/30 transition-all group cursor-pointer"
    >
      <div className="h-32 bg-gradient-to-br from-gray-700 to-gray-800 flex items-center justify-center relative">
        <Building2 className="w-12 h-12 text-gray-600" />
        <div className="absolute top-3 right-3 bg-gray-900/80 backdrop-blur px-2 py-1 rounded-lg text-xs font-medium text-white border border-gray-700">
          #{recommendation.rank}
        </div>
      </div>

      <div className="p-4 space-y-3">
        <div className="flex items-start justify-between">
          <div>
            <h4 className="font-semibold text-sm text-white">{recommendation.workspace_name || 'Recommended Workspace'}</h4>
            <div className="flex items-center gap-1 mt-1 text-xs text-gray-400">
              <MapPin className="w-3 h-3" />
              <span>{recommendation.location?.area || 'Location matched'}, {recommendation.location?.city || ''}</span>
            </div>
          </div>
          <div className="text-center">
            <span className="text-2xl font-bold text-primary-400">{Math.round(recommendation.overall_score)}</span>
            <p className="text-xs text-gray-500">score</p>
          </div>
        </div>

        {/* Score bars */}
        <div className="space-y-1.5">
          {Object.entries(scores).slice(0, 5).map(([key, value]) => (
            <div key={key} className="flex items-center gap-2">
              <span className="text-xs text-gray-400 w-24 capitalize">{key.replace(/_/g, ' ')}</span>
              <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full"
                  style={{ width: `${Math.round(value as number)}%` }}
                />
              </div>
              <span className="text-xs text-gray-300 w-8 text-right">{Math.round(value as number)}</span>
            </div>
          ))}
        </div>

        {/* Pros/Cons */}
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <p className="text-gray-500 mb-1 flex items-center gap-1"><Check className="w-3 h-3 text-green-400" /> Pros</p>
            {(recommendation.pros || []).slice(0, 3).map((pro, i) => (
              <p key={i} className="text-gray-300">{pro}</p>
            ))}
          </div>
          <div>
            <p className="text-gray-500 mb-1 flex items-center gap-1"><X className="w-3 h-3 text-red-400" /> Cons</p>
            {(recommendation.cons || []).slice(0, 3).map((con, i) => (
              <p key={i} className="text-gray-300">{con}</p>
            ))}
          </div>
        </div>

        {/* Cost */}
        {recommendation.cost_breakdown && (
          <div className="pt-2 border-t border-gray-700">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-400 flex items-center gap-1"><DollarSign className="w-3 h-3" /> Monthly</span>
              <span className="font-semibold text-white">
                {recommendation.cost_breakdown.total_monthly_inr ? `₹${(recommendation.cost_breakdown.total_monthly_inr / 100000).toFixed(2)}L` : 'N/A'}
              </span>
            </div>
          </div>
        )}

        <button className="w-full py-2 bg-primary-600 hover:bg-primary-500 text-white text-sm font-medium rounded-lg transition-colors">
          View Details
        </button>
      </div>
    </div>
  )
}
