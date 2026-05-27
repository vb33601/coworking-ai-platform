'use client'

import { useState } from 'react'
import { useAppStore } from '@/stores/appStore'
import { scheduleVisit } from '@/lib/api'
import { X, Calendar, Clock, User, Mail, Phone, MapPin, Building2, Send, CheckCircle } from 'lucide-react'
import toast from 'react-hot-toast'

export default function ScheduleVisitModal() {
  const { selectedWorkspace, scheduleModalOpen, closeScheduleModal } = useAppStore()
  const [form, setForm] = useState({
    visitor_name: '',
    visitor_email: '',
    visitor_mobile: '',
    visitor_address: '',
    visit_date: '',
    visit_time: '10:00',
    notes: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [result, setResult] = useState<any>(null)

  if (!scheduleModalOpen || !selectedWorkspace) return null

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.visitor_name || !form.visitor_email || !form.visitor_mobile || !form.visit_date) {
      toast.error('Please fill in all required fields')
      return
    }
    setSubmitting(true)
    try {
      const payload = {
        workspace_id: selectedWorkspace.workspace_id || '',
        workspace_name: selectedWorkspace.workspace_name || 'Workspace',
        ...form,
        team_size: selectedWorkspace.seating_capacity || 10,
      }
      const data = await scheduleVisit(payload)
      setResult(data)
      setSubmitted(true)
      toast.success(data.message || 'Visit scheduled successfully!')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to schedule visit')
    } finally {
      setSubmitting(false)
    }
  }

  const handleClose = () => {
    setSubmitted(false)
    setResult(null)
    setForm({
      visitor_name: '',
      visitor_email: '',
      visitor_mobile: '',
      visitor_address: '',
      visit_date: '',
      visit_time: '10:00',
      notes: '',
    })
    closeScheduleModal()
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="bg-gray-900/95 border-b border-gray-700 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
              <Calendar className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="font-semibold text-sm text-white">Schedule Site Visit</h2>
              <p className="text-xs text-gray-400">{selectedWorkspace.workspace_name}</p>
            </div>
          </div>
          <button onClick={handleClose} className="w-8 h-8 rounded-lg bg-gray-800 hover:bg-gray-700 flex items-center justify-center transition-colors">
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>

        {submitted ? (
          <div className="p-8 text-center space-y-4">
            <CheckCircle className="w-16 h-16 text-green-400 mx-auto" />
            <h3 className="text-lg font-semibold text-white">Visit Scheduled!</h3>
            <p className="text-sm text-gray-400">
              Your visit to <span className="text-white font-medium">{result?.workspace_name}</span> is confirmed for{' '}
              <span className="text-white font-medium">{result?.visit_datetime}</span>.
            </p>
            <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700 text-left space-y-2 text-xs">
              <p className="flex items-center gap-2">
                <Mail className="w-4 h-4 text-primary-400" />
                Email: {result?.email_sent ? 'Sent successfully' : result?.email_error || 'Not sent'}
              </p>
              <p className="flex items-center gap-2">
                <Phone className="w-4 h-4 text-green-400" />
                WhatsApp: {result?.whatsapp_sent ? 'Message prepared' : result?.whatsapp_error || 'Not sent'}
              </p>
              <p className="flex items-center gap-2">
                <Building2 className="w-4 h-4 text-accent-400" />
                Visit ID: {result?.visit_id}
              </p>
            </div>
            <button
              onClick={handleClose}
              className="w-full py-3 bg-primary-600 hover:bg-primary-500 text-white text-sm font-medium rounded-xl transition-colors"
            >
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {/* Date & Time */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-400 flex items-center gap-1 mb-1.5">
                  <Calendar className="w-3 h-3" /> Visit Date *
                </label>
                <input
                  type="date"
                  name="visit_date"
                  value={form.visit_date}
                  onChange={handleChange}
                  min={new Date().toISOString().split('T')[0]}
                  required
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 flex items-center gap-1 mb-1.5">
                  <Clock className="w-3 h-3" /> Visit Time *
                </label>
                <select
                  name="visit_time"
                  value={form.visit_time}
                  onChange={handleChange}
                  required
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500"
                >
                  {['09:00', '10:00', '11:00', '12:00', '14:00', '15:00', '16:00', '17:00'].map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Name */}
            <div>
              <label className="text-xs text-gray-400 flex items-center gap-1 mb-1.5">
                <User className="w-3 h-3" /> Full Name *
              </label>
              <input
                type="text"
                name="visitor_name"
                value={form.visitor_name}
                onChange={handleChange}
                placeholder="John Doe"
                required
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500 placeholder-gray-600"
              />
            </div>

            {/* Email */}
            <div>
              <label className="text-xs text-gray-400 flex items-center gap-1 mb-1.5">
                <Mail className="w-3 h-3" /> Email Address *
              </label>
              <input
                type="email"
                name="visitor_email"
                value={form.visitor_email}
                onChange={handleChange}
                placeholder="john@company.com"
                required
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500 placeholder-gray-600"
              />
            </div>

            {/* Mobile */}
            <div>
              <label className="text-xs text-gray-400 flex items-center gap-1 mb-1.5">
                <Phone className="w-3 h-3" /> Mobile Number *
              </label>
              <input
                type="tel"
                name="visitor_mobile"
                value={form.visitor_mobile}
                onChange={handleChange}
                placeholder="+91 98765 43210"
                required
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500 placeholder-gray-600"
              />
            </div>

            {/* Address */}
            <div>
              <label className="text-xs text-gray-400 flex items-center gap-1 mb-1.5">
                <MapPin className="w-3 h-3" /> Current Address
              </label>
              <textarea
                name="visitor_address"
                value={form.visitor_address}
                onChange={handleChange}
                placeholder="123 Business Park, City, State - PIN"
                rows={2}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500 placeholder-gray-600 resize-none"
              />
            </div>

            {/* Notes */}
            <div>
              <label className="text-xs text-gray-400 mb-1.5 block">Additional Notes</label>
              <textarea
                name="notes"
                value={form.notes}
                onChange={handleChange}
                placeholder="Any special requirements or questions..."
                rows={2}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500 placeholder-gray-600 resize-none"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-3 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white text-sm font-medium rounded-xl transition-colors flex items-center justify-center gap-2"
            >
              {submitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Scheduling...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Confirm & Schedule Visit
                </>
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
