import { useState, useEffect } from 'react'
import { BellRing, Pill, Loader2, TrendingDown, TrendingUp, Minus, X } from 'lucide-react'
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip,
} from 'recharts'

const API = 'http://localhost:8000/api/v1'

function PriceTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const { price, scraped_at } = payload[0].payload
  return (
    <div className="bg-gray-800/95 border border-white/10 rounded-lg px-3 py-2 shadow-lg text-sm backdrop-blur-sm">
      <p className="text-teal-400 font-semibold">Rs. {Number(price).toFixed(2)}</p>
      <p className="text-gray-400 text-xs mt-0.5">
        {new Date(scraped_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
      </p>
    </div>
  )
}

function PriceChart({ history, medicineId }) {
  if (!history || history.length < 2) {
    return <p className="text-xs text-gray-600 italic mt-3">Not enough price data yet.</p>
  }

  const data = history.map(p => ({ price: Number(p.price), scraped_at: p.scraped_at }))
  const prices = data.map(d => d.price)
  const minP = Math.min(...prices)
  const maxP = Math.max(...prices)
  const delta = prices[prices.length - 1] - prices[0]
  const TrendIcon = delta < 0 ? TrendingDown : delta > 0 ? TrendingUp : Minus
  const trendColor = delta < 0 ? 'text-green-400' : delta > 0 ? 'text-red-400' : 'text-gray-400'
  const gradId = `grad-${medicineId}`

  return (
    <div className="mt-4">
      <div className="flex items-center gap-1.5 mb-2">
        <TrendIcon className={`w-3.5 h-3.5 ${trendColor}`} />
        <span className={`text-xs font-medium ${trendColor}`}>
          {delta < 0
            ? `Down Rs. ${Math.abs(delta).toFixed(2)} over 4 weeks`
            : delta > 0
            ? `Up Rs. ${delta.toFixed(2)} over 4 weeks`
            : 'Stable price'}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={80}>
        <AreaChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#14b8a6" stopOpacity={0.35} />
              <stop offset="95%" stopColor="#14b8a6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="scraped_at" hide />
          <YAxis domain={[minP * 0.95, maxP * 1.05]} hide />
          <Tooltip content={<PriceTooltip />} />
          <Area type="monotone" dataKey="price" stroke="#14b8a6" strokeWidth={2}
            fill={`url(#${gradId})`} dot={false} activeDot={{ r: 4, fill: '#14b8a6', strokeWidth: 0 }} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Untrack confirm dialog ────────────────────────────────────────────────────
function UntrackModal({ medicine, onConfirm, onCancel }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="glass-panel p-7 w-full max-w-sm shadow-2xl">
        <h3 className="text-lg font-semibold text-white mb-2">Remove from watchlist?</h3>
        <p className="text-gray-400 text-sm mb-6">
          Stop tracking <span className="text-white font-medium">{medicine.brand_name}</span> ({medicine.profile_label})?
        </p>
        <div className="flex gap-3">
          <button onClick={onCancel} className="flex-1 py-2.5 rounded-xl border border-white/10 text-gray-300 hover:bg-white/5 transition-colors text-sm">
            Keep it
          </button>
          <button onClick={onConfirm} className="flex-1 py-2.5 rounded-xl bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-300 transition-colors text-sm">
            Remove
          </button>
        </div>
      </div>
    </div>
  )
}

export default function TrackedMedicines({ userId, userName, onToast }) {
  const [medicines, setMedicines] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [untrackModal, setUntrackModal] = useState(null)

  const load = async () => {
    setIsLoading(true)
    try {
      const res = await fetch(`${API}/users/${userId}/tracked-medicines`)
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail?.message || 'Failed to load tracked medicines')
      }
      setMedicines(await res.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => { load() }, [userId])

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-8 h-8 text-teal-400 animate-spin" />
      </div>
    )
  }

  if (error) return <div className="text-red-400 text-center py-10">{error}</div>

  const totalSavings = medicines.reduce((acc, m) => {
    if (m.history?.length >= 2) {
      const first = m.history[0].price
      const last = m.history[m.history.length - 1].price
      return acc + Math.max(0, first - last)
    }
    return acc
  }, 0)

  return (
    <>
      {untrackModal && (
        <UntrackModal
          medicine={untrackModal}
          onCancel={() => setUntrackModal(null)}
          onConfirm={async () => {
            // Optimistic removal — no untrack API yet, just remove from local state
            setMedicines(prev => prev.filter(m => m.tracked_id !== untrackModal.tracked_id))
            setUntrackModal(null)
            onToast?.(`${untrackModal.brand_name} removed from watchlist`, 'success')
          }}
        />
      )}

      <div className="w-full max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-10 gap-4">
          <div>
            <h2 className="text-3xl font-bold text-white mb-1">{userName}'s Watchlist</h2>
            <p className="text-gray-400">
              Tracking <span className="text-teal-400 font-semibold">{medicines.length}</span> medicines
              {totalSavings > 0 && (
                <> · Potential saving <span className="text-green-400 font-semibold">Rs. {totalSavings.toFixed(2)}</span> vs. original prices</>
              )}
            </p>
          </div>
          <button className="primary-button flex items-center gap-2 self-start">
            <BellRing className="w-4 h-4" />
            <span>Alert Settings</span>
          </button>
        </div>

        {/* Empty state */}
        {medicines.length === 0 ? (
          <div className="glass-panel py-20 flex flex-col items-center justify-center text-center">
            <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mb-4">
              <Pill className="w-8 h-8 text-gray-500" />
            </div>
            <h3 className="text-xl font-medium text-white mb-2">No tracked medicines yet</h3>
            <p className="text-gray-400 max-w-md">
              Search for your prescription and track substitutes to monitor price trends here.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {medicines.map(med => (
              <div
                key={med.tracked_id}
                className="glass-panel p-6 flex flex-col relative overflow-hidden hover:bg-white/10 transition-colors"
              >
                {/* Remove button */}
                <button
                  onClick={() => setUntrackModal(med)}
                  className="absolute top-4 right-4 w-7 h-7 flex items-center justify-center rounded-lg text-gray-600 hover:text-red-400 hover:bg-red-400/10 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>

                {/* Background pill */}
                <div className="absolute top-0 right-0 p-4 opacity-[0.05] pointer-events-none">
                  <Pill className="w-24 h-24" />
                </div>

                {/* Profile badge */}
                <div className="mb-3">
                  <span className="px-2.5 py-1 rounded-md bg-white/10 text-xs font-medium text-gray-300">
                    {med.profile_label}
                  </span>
                </div>

                {/* Brand name */}
                <h3 className="text-xl font-bold text-white pr-8">{med.brand_name}</h3>

                {/* Latest price */}
                <p className="text-2xl font-semibold text-white mt-2">
                  {med.latest_price != null
                    ? `Rs. ${Number(med.latest_price).toFixed(2)}`
                    : <span className="text-gray-500 text-lg">Price N/A</span>}
                </p>

                {/* Chart */}
                <PriceChart history={med.history} medicineId={med.tracked_id} />
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  )
}
