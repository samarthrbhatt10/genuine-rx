import { useState, useEffect, useCallback } from 'react'
import { Pill, LayoutDashboard, Search, X, CheckCircle, AlertCircle } from 'lucide-react'
import SearchBar from './components/SearchBar'
import SubstituteList from './components/SubstituteList'
import TrackedMedicines from './components/TrackedMedicines'

// Demo users from seed — in production this would come from auth
const DEMO_USERS = [
  { id: 1, name: 'Rahul', phone: '+919999000001' },
  { id: 3, name: 'Priya', phone: '+919999000002' },
]

// ── Toast system ──────────────────────────────────────────────────────────────
function ToastContainer({ toasts, onDismiss }) {
  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`flex items-center gap-3 px-4 py-3 rounded-xl shadow-2xl text-sm font-medium pointer-events-auto transition-all duration-300
            ${t.type === 'success'
              ? 'bg-teal-900/90 border border-teal-500/40 text-teal-100 backdrop-blur-md'
              : 'bg-red-900/90 border border-red-500/40 text-red-100 backdrop-blur-md'
            }`}
        >
          {t.type === 'success'
            ? <CheckCircle className="w-4 h-4 text-teal-400 shrink-0" />
            : <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />}
          <span>{t.message}</span>
          <button onClick={() => onDismiss(t.id)} className="ml-2 opacity-60 hover:opacity-100 transition-opacity">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
    </div>
  )
}

function App() {
  const [currentView, setCurrentView] = useState('search')
  const [resolvedMedicine, setResolvedMedicine] = useState(null)
  const [currentUser, setCurrentUser] = useState(DEMO_USERS[0])
  const [toasts, setToasts] = useState([])

  const addToast = useCallback((message, type = 'success') => {
    const id = Date.now()
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000)
  }, [])

  const dismissToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const handleResolve = (medicineData) => {
    setResolvedMedicine(medicineData)
    setCurrentView('results')
  }

  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden font-sans">
      {/* Background gradients */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-teal-600/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-blue-600/20 rounded-full blur-[120px] pointer-events-none" />

      {/* Navigation */}
      <nav className="relative z-10 border-b border-white/10 bg-black/20 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div
              className="flex items-center gap-2 cursor-pointer group"
              onClick={() => setCurrentView('search')}
            >
              <div className="p-2 bg-teal-500/20 rounded-lg group-hover:bg-teal-500/30 transition-colors">
                <Pill className="w-5 h-5 text-teal-400" />
              </div>
              <span className="text-xl font-bold bg-gradient-to-r from-teal-400 to-blue-400 bg-clip-text text-transparent">
                Genuine RX
              </span>
            </div>

            {/* Right side */}
            <div className="flex items-center gap-3">
              {/* User switcher (demo) */}
              <select
                value={currentUser.id}
                onChange={e => setCurrentUser(DEMO_USERS.find(u => u.id === Number(e.target.value)))}
                className="bg-white/5 border border-white/10 rounded-lg text-sm text-gray-300 px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-teal-500 cursor-pointer"
              >
                {DEMO_USERS.map(u => (
                  <option key={u.id} value={u.id} className="bg-gray-900">{u.name}</option>
                ))}
              </select>

              <button
                onClick={() => setCurrentView('search')}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm transition-all ${
                  currentView === 'search' || currentView === 'results'
                    ? 'bg-white/10 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <Search className="w-4 h-4" />
                <span>Find Medicine</span>
              </button>

              <button
                onClick={() => setCurrentView('dashboard')}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm transition-all ${
                  currentView === 'dashboard'
                    ? 'bg-white/10 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <LayoutDashboard className="w-4 h-4" />
                <span>Dashboard</span>
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main */}
      <main className="relative z-10 flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-12 flex flex-col items-center">
        {currentView === 'search' && (
          <div className="w-full max-w-3xl flex flex-col items-center justify-center flex-1">
            <div className="text-center mb-10">
              <h1 className="text-5xl font-bold mb-4 tracking-tight">Stop overpaying for medicines.</h1>
              <p className="text-xl text-gray-400 max-w-2xl mx-auto">
                Search for your prescribed brand to instantly find cheaper, exact generic substitutes.
              </p>
            </div>
            <SearchBar onResolve={handleResolve} />
          </div>
        )}

        {currentView === 'results' && resolvedMedicine && (
          <div className="w-full">
            <SubstituteList
              medicineId={resolvedMedicine.medicine_id}
              onBack={() => setCurrentView('search')}
              userId={currentUser.id}
              onToast={addToast}
            />
          </div>
        )}

        {currentView === 'dashboard' && (
          <div className="w-full">
            <TrackedMedicines userId={currentUser.id} userName={currentUser.name} onToast={addToast} />
          </div>
        )}
      </main>

      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  )
}

export default App
