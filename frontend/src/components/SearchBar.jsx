import { useState } from 'react'
import { Search, Camera, ArrowRight, Loader2, AlertCircle } from 'lucide-react'

export default function SearchBar({ onResolve }) {
  const [query, setQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [candidates, setCandidates] = useState(null) // for low-confidence fallback

  const handleSearch = async (text, source = 'typed') => {
    if (!text.trim()) return
    
    setIsLoading(true)
    setError(null)
    setCandidates(null)
    
    try {
      const res = await fetch('http://localhost:8000/api/v1/resolve-medicine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_text: text, source })
      })
      
      const data = await res.json()
      
      if (!res.ok) {
        throw new Error(data.message || 'Failed to resolve medicine')
      }
      
      if (!data.matched) {
        setError('No medicine found matching your search. Please try another brand or salt name.')
        return
      }

      if (data.needs_confirmation) {
        // OCR or typed text was too ambiguous (<75% confidence)
        setCandidates(data.candidates)
      } else {
        // High confidence match, proceed immediately
        onResolve(data)
      }
      
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const simulateOCR = () => {
    // In a real app, this would open the camera or file picker and pass the image to an OCR endpoint
    // For demo purposes, we'll simulate an OCR read that is slightly misspelled to trigger the confidence check or direct match
    const demoOcrText = "Croc"
    setQuery(demoOcrText)
    handleSearch(demoOcrText, 'ocr')
  }

  return (
    <div className="w-full">
      <div className="glass-panel p-2 flex items-center gap-2 focus-within:ring-2 focus-within:ring-teal-500/50 transition-all">
        <div className="pl-4 text-gray-400">
          <Search className="w-6 h-6" />
        </div>
        <input 
          type="text" 
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch(query)}
          placeholder="Enter medicine brand or generic name..."
          className="flex-1 bg-transparent border-none outline-none text-lg text-white px-2 py-4 placeholder-gray-500"
        />
        
        <button 
          onClick={simulateOCR}
          title="Upload Prescription (Demo OCR)"
          className="p-3 text-gray-400 hover:text-white hover:bg-white/10 rounded-xl transition-colors flex items-center justify-center group relative"
        >
          <Camera className="w-6 h-6" />
          <span className="absolute -top-10 scale-0 group-hover:scale-100 transition-all bg-gray-800 text-xs px-2 py-1 rounded whitespace-nowrap">
            Scan Rx
          </span>
        </button>
        
        <button 
          onClick={() => handleSearch(query)}
          disabled={!query.trim() || isLoading}
          className="primary-button flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <ArrowRight className="w-5 h-5" />}
        </button>
      </div>

      {error && (
        <div className="mt-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-start gap-3 text-red-400 animate-in fade-in">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <p>{error}</p>
        </div>
      )}

      {candidates && (
        <div className="mt-8 glass-panel p-6 animate-in slide-in-from-bottom-4">
          <h3 className="text-xl font-medium text-white mb-4">Did you mean...</h3>
          <p className="text-gray-400 mb-6">We couldn't find an exact match. Please select the correct medicine:</p>
          <div className="grid gap-3">
            {candidates.map((c, i) => (
              <button 
                key={i}
                onClick={() => onResolve(c)}
                className="flex items-center justify-between p-4 rounded-xl border border-white/5 bg-white/5 hover:bg-white/10 transition-colors text-left"
              >
                <div>
                  <span className="text-white font-medium text-lg block">{c.brand_name}</span>
                  <span className="text-sm text-gray-400">Match confidence: {Math.round(c.confidence * 100)}%</span>
                </div>
                <ArrowRight className="w-5 h-5 text-teal-400" />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
