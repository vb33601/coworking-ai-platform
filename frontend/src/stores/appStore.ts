import { create } from 'zustand'
import { Message, Recommendation, Workspace } from '@/types'

interface AppState {
  messages: Message[]
  workspaces: Workspace[]
  recommendations: Recommendation[]
  isLoading: boolean
  sidebarOpen: boolean
  darkMode: boolean
  selectedWorkspace: Recommendation | null
  detailModalOpen: boolean
  scheduleModalOpen: boolean
  addMessage: (msg: Message) => void
  setLoading: (loading: boolean) => void
  setWorkspaces: (workspaces: Workspace[]) => void
  setRecommendations: (recs: Recommendation[]) => void
  setSelectedWorkspace: (rec: Recommendation | null) => void
  openDetailModal: (rec: Recommendation) => void
  closeDetailModal: () => void
  openScheduleModal: () => void
  closeScheduleModal: () => void
  toggleSidebar: () => void
  toggleDarkMode: () => void
}

export const useAppStore = create<AppState>((set) => ({
  messages: [],
  workspaces: [],
  recommendations: [],
  isLoading: false,
  sidebarOpen: true,
  darkMode: true,
  selectedWorkspace: null,
  detailModalOpen: false,
  scheduleModalOpen: false,
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  setLoading: (loading) => set({ isLoading: loading }),
  setWorkspaces: (workspaces) => set({ workspaces }),
  setRecommendations: (recs) => set({ recommendations: recs }),
  setSelectedWorkspace: (rec) => set({ selectedWorkspace: rec }),
  openDetailModal: (rec) => set({ selectedWorkspace: rec, detailModalOpen: true }),
  closeDetailModal: () => set({ selectedWorkspace: null, detailModalOpen: false }),
  openScheduleModal: () => set({ scheduleModalOpen: true }),
  closeScheduleModal: () => set({ scheduleModalOpen: false }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  toggleDarkMode: () => set((state) => ({ darkMode: !state.darkMode })),
}))