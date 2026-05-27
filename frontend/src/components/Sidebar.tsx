import { useAppStore } from '@/stores/appStore'
import { 
  MessageSquare, 
  Search, 
  BarChart3, 
  Settings, 
  FileText,
  ChevronLeft,
  ChevronRight,
  Plus
} from 'lucide-react'

export default function Sidebar() {
  const { sidebarOpen, toggleSidebar, messages } = useAppStore()
  
  const recentSearches = messages
    .filter(m => m.role === 'user')
    .slice(-5)
    .map(m => m.content.slice(0, 40) + (m.content.length > 40 ? '...' : ''))

  if (!sidebarOpen) {
    return (
      <button 
        onClick={toggleSidebar}
        className="w-12 h-12 border-r border-gray-800 flex items-center justify-center hover:bg-gray-800 transition-colors"
      >
        <ChevronRight className="w-4 h-4 text-gray-400" />
      </button>
    )
  }

  return (
    <aside className="w-64 border-r border-gray-800 bg-gray-900 flex flex-col">
      <div className="h-16 border-b border-gray-800 flex items-center justify-between px-4">
        <span className="font-semibold text-sm">Workspace</span>
        <button onClick={toggleSidebar} className="p-1 hover:bg-gray-800 rounded">
          <ChevronLeft className="w-4 h-4 text-gray-400" />
        </button>
      </div>
      
      <div className="p-3">
        <button className="w-full flex items-center gap-2 px-3 py-2 bg-primary-600 hover:bg-primary-500 text-white text-sm rounded-lg transition-colors">
          <Plus className="w-4 h-4" />
          New Search
        </button>
      </div>

      <nav className="flex-1 px-3 space-y-1">
        <SidebarItem icon={<MessageSquare className="w-4 h-4" />} label="Conversations" active />
        <SidebarItem icon={<Search className="w-4 h-4" />} label="Saved Searches" />
        <SidebarItem icon={<BarChart3 className="w-4 h-4" />} label="Analytics" />
        <SidebarItem icon={<FileText className="w-4 h-4" />} label="Reports" />
        <SidebarItem icon={<Settings className="w-4 h-4" />} label="Settings" />
      </nav>

      <div className="p-3 border-t border-gray-800">
        <p className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wider">Recent</p>
        <div className="space-y-1">
          {recentSearches.length === 0 && (
            <p className="text-xs text-gray-600">No recent searches</p>
          )}
          {recentSearches.map((search, i) => (
            <button key={i} className="w-full text-left text-xs text-gray-400 hover:text-white px-2 py-1.5 rounded hover:bg-gray-800 truncate transition-colors">
              {search}
            </button>
          ))}
        </div>
      </div>
    </aside>
  )
}

function SidebarItem({ icon, label, active }: { icon: React.ReactNode; label: string; active?: boolean }) {
  return (
    <button className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
      active 
        ? 'bg-primary-500/10 text-primary-400 border border-primary-500/20' 
        : 'text-gray-400 hover:text-white hover:bg-gray-800'
    }`}>
      {icon}
      {label}
    </button>
  )
}
