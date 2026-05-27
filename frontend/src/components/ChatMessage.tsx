import { Message } from '@/types'
import { User, Bot, Loader2 } from 'lucide-react'
import WorkspaceCard from './WorkspaceCard'

interface Props {
  message: Message
}

export default function ChatMessage({ message }: Props) {
  const isUser = message.role === 'user'

  if (message.isLoading) {
    return (
      <div className="flex gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shrink-0">
          <Loader2 className="w-4 h-4 text-white animate-spin" />
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3">
          <p className="text-sm text-gray-400">AI agents are searching, comparing, and analyzing...</p>
          <div className="flex gap-2 mt-2">
            {['Requirement Agent', 'Discovery Agent', 'Pricing Agent', 'Optimization Agent'].map((agent) => (
              <span key={agent} className="text-xs px-2 py-1 rounded-full bg-primary-500/10 text-primary-400 border border-primary-500/20">
                {agent}
              </span>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
        isUser ? 'bg-gray-700' : 'bg-gradient-to-br from-primary-500 to-accent-500'
      }`}>
        {isUser ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-white" />}
      </div>
      <div className={`max-w-3xl rounded-xl px-4 py-3 ${
        isUser 
          ? 'bg-primary-600 text-white' 
          : 'bg-gray-900 border border-gray-800 text-gray-200'
      }`}>
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        
        {message.recommendations && message.recommendations.length > 0 && (
          <div className="mt-4 space-y-3 xl:hidden">
            <p className="text-xs font-medium text-primary-400 uppercase tracking-wider">Recommendations</p>
            {message.recommendations.map((rec) => (
              <WorkspaceCard key={rec.workspace_id} recommendation={rec} compact />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
