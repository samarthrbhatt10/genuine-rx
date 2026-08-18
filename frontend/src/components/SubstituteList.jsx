import { useState, useEffect } from 'react'
import { ArrowLeft, ShieldAlert, CheckCircle2, TrendingDown, Plus, Loader2, X, User } from 'lucide-react'

const API = 'http://localhost:8000/api/v1'

// ── Profile label picker modal ────────────────────────────────────────────────
const PROFILE_OPTIONS = ['self', 'Papa', 'Amma', 'Husband', 'Wife', 'Child', 'Other']

function ProfileModal({ medicineName, onConfirm, onCancel }) {
  const [label, setLabel] = useState('self')
  const [custom, setCustom] = useState('')

  const effective = label === 'Other' ? custom.trim() : label

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="glass-panel p-8 w-full max-w-md shadow-2xl">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-semibold text-white">Track Medicine</h3>
          <button onClick={onCancel} className="text-gray-400 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-gray-300 mb-6">
          Adding <span className="font-semibold text-teal-400">{medicineName}</span> to your watchlist. Who is this for?
        </p>

        <div className="grid grid-cols-3 gap-2 mb-4">
          {PROFILE_OPTIONS.map(opt => (
            <button
              key={opt}
              onClick={() => setLabel(opt)}
              className={`flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                label === opt
                  ? 'bg-teal-500/30 border border-teal-500/60 text-teal-300'
                  : 'bg-white/5 border border-white/10 text-gray-300 hover:bg-white/10'
              }`}
            >
              <User className="w-3.5 h-3.5" />
              {opt}
            </button>
          ))}
        </div>

        {label === 'Other' && (
          <input
            autoFocus
            type="text"
            value={custom}
            onChange={e => setCustom(e.target.value)}
            placeholder="Enter profile name…"
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 outline-none focus:border-teal-500/50 mb-4"
          />
        )}

        <div className="flex gap-3 mt-6">
          <button onClick={onCancel} className="flex-1 py-3 rounded-xl border border-white/10 text-gray-300 hover:bg-white/5 transition-colors">
            Cancel
          </button>
          <button
            disabled={!effective}
            onClick={() => onConfirm(effective)}
            className="flex-1 primary-button disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Track
          </button>
        </div>
      </div>
    </div>
  )
}

export default function SubstituteList({ medicineId, onBack, userId, onToast }) {
  const [data, setData] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [trackedIds, setTrackedIds] = useState(new Set())
  const [trackingId, setTrackingId] = useState(null)
  const [modal, setModal] = useState(null) // { medicineId, medicineName }

  useEffect(() => {
    const load = async () => {
      try {
        const [subRes, trackedRes] = await Promise.all([
          fetch(`${API}/medicines/${medicineId}/substitutes`),
          fetch(`${API}/users/${userId}/tracked-medicines`),
        ])
        const subData = await subRes.json()
        if (!subRes.ok) throw new Error(subData.detail?.message || 'Failed to load substitutes')
        setData(subData)

        if (trackedRes.ok) {
          const trackedList = await trackedRes.json()
          setTrackedIds(new Set(trackedList.map(t => t.medicine_id)))
        }
      } catch (err) {
        setError(err.message)
      } finally {
        setIsLoading(false)
      }
    }
    load()
  }, [medicineId, userId])

  const openModal = (medId, medName) => {
    if (trackedIds.has(medId)) return
    setModal({ medicineId: medId, medicineName: medName })
  }

  const confirmTrack = async (profileLabel) => {
    const { medicineId: medIdToTrack, medicineName } = modal
    setModal(null)
    setTrackingId(medIdToTrack)
    try {
      const res = await fetch(`${API}/tracked-medicines`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          medicine_id: medIdToTrack,
          profile_label: profileLabel,
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail?.message || 'Failed to track')
      }
      setTrackedIds(prev => new Set([...prev, medIdToTrack]))
      onToast?.(`${medicineName} added to watchlist (${profileLabel})`, 'success')
    } catch (err) {
      onToast?.(err.message, 'error')
    } finally {
      setTrackingId(null)
    }
  }

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Loader2 className="w-10 h-10 text-teal-400 animate-spin mb-4" />
        <p className="text-gray-400">Finding the best substitutes…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <p className="text-red-400 mb-4">{error}</p>
        <button onClick={onBack} className="text-teal-400 hover:underline">Go back</button>
      </div>
    )
  }

  if (!data) return null

  return (
    <>
      {modal && (
        <ProfileModal
          medicineName={modal.medicineName}
          onConfirm={confirmTrack}
          onCancel={() => setModal(null)}
        />
      )}

      <div className="w-full max-w-4xl mx-auto pb-20">
        <button
          onClick={onBack}
          className="flex items-center gap-2 text-gray-400 hover:text-white mb-8 transition-colors group"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
          Back to Search
        </button>

        {/* Source medicine hero */}
        <div className="glass-panel p-8 mb-8 bg-gradient-to-br from-white/10 to-transparent relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-teal-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
          <div className="relative z-10">
            <h2 className="text-sm font-semibold text-teal-400 uppercase tracking-wider mb-2">Original Prescription</h2>
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
              <div>
                <h1 className="text-4xl font-bold text-white mb-2">{data.source_medicine.brand_name}</h1>
                {data.source_medicine.current_price != null
                  ? <p className="text-xl text-gray-300">Rs. {data.source_medicine.current_price.toFixed(2)}</p>
                  : <p className="text-lg text-gray-500">Price unavailable</p>}
              </div>
              <TrackButton
                isTracked={trackedIds.has(data.source_medicine.medicine_id)}
                isTracking={trackingId === data.source_medicine.medicine_id}
                onClick={() => openModal(data.source_medicine.medicine_id, data.source_medicine.brand_name)}
                size="sm"
              />
            </div>
          </div>
        </div>

        {/* Caution flag */}
        {data.caution_flag && (
          <div className="mb-8 p-6 bg-amber-500/10 border border-amber-500/20 rounded-2xl flex gap-4 items-start shadow-[0_0_30px_rgba(245,158,11,0.1)]">
            <ShieldAlert className="w-6 h-6 shrink-0 text-amber-500 mt-0.5" />
            <div>
              <h3 className="font-semibold text-amber-400 mb-1">Clinical Caution</h3>
              <p className="text-sm text-amber-200/80 leading-relaxed">{data.caution_flag}</p>
            </div>
          </div>
        )}

        {/* Disclaimer */}
        <p className="text-xs text-gray-600 mb-6 italic">
          ⚕️ Always confirm substitutions with your pharmacist or prescribing doctor.
        </p>

        {/* Substitutes */}
        <h3 className="text-xl font-semibold text-white mb-4">Available Substitutes</h3>

        {data.substitutes.length === 0 ? (
          <div className="text-center py-12 glass-panel">
            <p className="text-gray-400 text-lg">No generic substitutes found for this medicine.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {data.substitutes.map(sub => (
              <div
                key={sub.medicine_id}
                className={`glass-panel p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 transition-all hover:bg-white/10 ${
                  sub.is_jan_aushadhi ? 'border-teal-500/30 bg-teal-500/5' : ''
                }`}
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2 flex-wrap">
                    <h4 className="text-2xl font-bold text-white">{sub.brand_name}</h4>
                    {sub.is_jan_aushadhi && (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-500/20 text-teal-300 text-xs font-semibold border border-teal-500/30">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Jan Aushadhi
                      </span>
                    )}
                  </div>
                  <div className="flex items-baseline gap-4 mt-3 flex-wrap">
                    <span className="text-3xl font-bold text-white tracking-tight">Rs. {sub.price.toFixed(2)}</span>
                    {sub.savings_percent > 0 && (
                      <div className="flex items-center gap-1.5 text-green-400 font-medium bg-green-400/10 px-2.5 py-1 rounded-lg text-sm">
                        <TrendingDown className="w-4 h-4" />
                        {sub.savings_percent}% cheaper · Save Rs. {sub.savings_rupees.toFixed(2)}
                      </div>
                    )}
                  </div>
                </div>

                <TrackButton
                  isTracked={trackedIds.has(sub.medicine_id)}
                  isTracking={trackingId === sub.medicine_id}
                  onClick={() => openModal(sub.medicine_id, sub.brand_name)}
                  size="md"
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  )
}

function TrackButton({ isTracked, isTracking, onClick, size = 'md' }) {
  const base = size === 'sm'
    ? 'px-4 py-2 rounded-lg text-sm gap-2'
    : 'px-6 py-3 rounded-xl text-base gap-2'

  if (isTracked) {
    return (
      <button disabled className={`flex items-center ${base} bg-teal-500/15 border border-teal-500/30 text-teal-300 cursor-default`}>
        <CheckCircle2 className="w-4 h-4" />
        <span>Tracked</span>
      </button>
    )
  }

  if (isTracking) {
    return (
      <button disabled className={`flex items-center ${base} bg-white/5 text-gray-300`}>
        <Loader2 className="w-4 h-4 animate-spin text-teal-400" />
        <span>Tracking…</span>
      </button>
    )
  }

  return (
    <button
      onClick={onClick}
      className={`flex items-center ${base} bg-white/10 hover:bg-white/20 text-white font-medium transition-colors`}
    >
      <Plus className="w-4 h-4" />
      <span>Track Price</span>
    </button>
  )
}
