'use client'

import { useState, useRef, useEffect } from 'react'
import { useAppStore } from '@/stores/appStore'
import { searchWorkspaces } from '@/lib/api'
import ChatMessage from '@/components/ChatMessage'
import WorkspaceCard from '@/components/WorkspaceCard'
import WorkspaceDetailModal from '@/components/WorkspaceDetailModal'
import ScheduleVisitModal from '@/components/ScheduleVisitModal'
import Sidebar from '@/components/Sidebar'
import { Send, Sparkles, Building2, MapPin, Users, DollarSign } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Home() {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { messages, recommendations, isLoading, addMessage, setLoading, setRecommendations } = useAppStore()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMsg = { id: Date.now().toString(), role: 'user' as const, content: input }
    addMessage(userMsg)
    setInput('')
    setLoading(true)

    // Add loading message
    const loadingId = (Date.now() + 1).toString()
    addMessage({ id: loadingId, role: 'assistant', content: '', isLoading: true })

    try {
      const result = await searchWorkspaces(input)

      // Remove loading message
      const { messages: currentMessages } = useAppStore.getState()
      const filtered = currentMessages.filter(m => m.id !== loadingId)
      useAppStore.setState({ messages: filtered })

      const assistantMsg = {
        id: (Date.now() + 2).toString(),
        role: 'assistant' as const,
        content: result.summary || `Found ${result.recommendations?.length || 0} recommendations.`,
        recommendations: result.recommendations || [],
      }
      addMessage(assistantMsg)
      setRecommendations(result.recommendations || [])

      toast.success('Search completed!')
    } catch (err: any) {
      const { messages: currentMessages } = useAppStore.getState()
      const filtered = currentMessages.filter(m => m.id !== loadingId)
      useAppStore.setState({ messages: filtered })

      addMessage({
        id: (Date.now() + 3).toString(),
        role: 'assistant',
        content: `Sorry, I encountered an error: ${err.message || 'Unknown error'}. Please try again.`,
      })
      toast.error('Search failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen bg-gray-950 text-white overflow-hidden">
      <Sidebar />

      <main className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-16 border-b border-gray-800 flex items-center px-6 justify-between bg-gray-900/50 backdrop-blur">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
              <Building2 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-semibold text-sm">Coworking AI</h1>
              <p className="text-xs text-gray-400">Intelligent Office Discovery</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-xs text-gray-400">
            <span className="flex items-center gap-1"><MapPin className="w-3 h-3" /> 10 Cities</span>
            <span className="flex items-center gap-1"><Users className="w-3 h-3" /> 10 Providers</span>
            <span className="flex items-center gap-1"><DollarSign className="w-3 h-3" /> Real-time Pricing</span>
          </div>
        </header>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center space-y-6">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-500/20 to-accent-500/20 flex items-center justify-center">
                <Sparkles className="w-10 h-10 text-primary-400" />
              </div>
              <div className="max-w-lg">
                <h2 className="text-2xl font-bold mb-2">Discover Your Perfect Office</h2>
                <p className="text-gray-400 mb-6">
                  Describe your team size, budget, location preferences, and requirements.
                  Our AI agents will search, compare, and recommend the best co-working spaces and managed offices.
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
                  {SUGGESTIONS.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => setInput(s)}
                      className="p-3 rounded-lg bg-gray-900 border border-gray-800 hover:border-primary-500/50 hover:bg-gray-800/50 transition-all text-sm text-gray-300 text-left"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-gray-800">
          <form onSubmit={handleSubmit} className="max-w-4xl mx-auto relative">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Describe your office requirements..."
              className="w-full bg-gray-900 border border-gray-700 rounded-xl px-5 py-4 pr-14 text-sm focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500/20 placeholder-gray-500"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-9 h-9 bg-primary-600 hover:bg-primary-500 disabled:opacity-30 disabled:hover:bg-primary-600 rounded-lg flex items-center justify-center transition-colors"
            >
              <Send className="w-4 h-4 text-white" />
            </button>
          </form>
          <p className="text-center text-xs text-gray-600 mt-2">
            AI agents use real-time data from WeWork, IndiQube, Awfis, Smartworks, Regus, and more.
          </p>
        </div>
      </main>

      {/* Recommendations Sidebar */}
      {recommendations.length > 0 && (
        <aside className="w-96 border-l border-gray-800 bg-gray-900/50 overflow-y-auto hidden xl:block">
          <div className="p-4 border-b border-gray-800">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-primary-400" />
              Top Recommendations
            </h3>
          </div>
          <div className="p-4 space-y-4">
            {recommendations.map((rec) => (
              <WorkspaceCard key={rec.workspace_id} recommendation={rec} />
            ))}
          </div>
        </aside>
      )}

      {/* Detail Modal */}
      <WorkspaceDetailModal />

      {/* Schedule Visit Modal */}
      <ScheduleVisitModal />
    </div>
  )
}

const SUGGESTIONS = [
  "We are a fintech startup with 80 employees looking for a managed office in Bangalore near ORR with 4 meeting rooms and cafeteria.",
  "Need a coworking space in Mumbai BKC for 25 people, budget 3 lakh/month, with parking and 24/7 access.",
  "Looking for a hot desk arrangement in Delhi Connaught Place for 10 remote workers, 3 months, meeting rooms on demand.",
  "Enterprise needs a 200-seat managed office in Hyderabad Hitech City with server room, branding rights, and 2-year lease.",
]
