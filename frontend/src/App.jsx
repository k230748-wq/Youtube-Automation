import { useState, useEffect } from 'react'
import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export default function App() {
  const [channels, setChannels] = useState([])
  const [selectedChannel, setSelectedChannel] = useState(null)
  const [pipelines, setPipelines] = useState([])
  const [view, setView] = useState('channels')

  useEffect(() => {
    api.get('/channels/').then(r => setChannels(r.data.channels)).catch(() => {})
    api.get('/pipelines/').then(r => setPipelines(r.data.pipelines)).catch(() => {})
  }, [])

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-6 py-4">
        <h1 className="text-xl font-bold">YouTube Automation</h1>
        <nav className="flex gap-4 mt-2 text-sm">
          <button onClick={() => setView('channels')} className={view === 'channels' ? 'text-blue-400' : 'text-gray-400'}>Channels</button>
          <button onClick={() => setView('pipelines')} className={view === 'pipelines' ? 'text-blue-400' : 'text-gray-400'}>Pipelines</button>
          <button onClick={() => setView('videos')} className={view === 'videos' ? 'text-blue-400' : 'text-gray-400'}>Videos</button>
        </nav>
      </header>
      <main className="p-6">
        {view === 'channels' && (
          <div>
            <h2 className="text-lg font-semibold mb-4">Channels ({channels.length})</h2>
            {channels.length === 0 && <p className="text-gray-500">No channels yet. Create one to get started.</p>}
            {channels.map(ch => (
              <div key={ch.id} className="border border-gray-800 rounded p-4 mb-2">
                <p className="font-medium">{ch.name}</p>
                <p className="text-sm text-gray-400">{ch.niche}</p>
              </div>
            ))}
          </div>
        )}
        {view === 'pipelines' && (
          <div>
            <h2 className="text-lg font-semibold mb-4">Pipelines ({pipelines.length})</h2>
            {pipelines.map(p => (
              <div key={p.id} className="border border-gray-800 rounded p-4 mb-2">
                <p className="font-medium">{p.niche}</p>
                <p className="text-sm text-gray-400">Phase {p.current_phase} — {p.status}</p>
              </div>
            ))}
          </div>
        )}
        {view === 'videos' && (
          <div>
            <h2 className="text-lg font-semibold mb-4">Videos</h2>
            <p className="text-gray-500">Video list will appear here after pipeline runs.</p>
          </div>
        )}
      </main>
    </div>
  )
}
