import { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import {
  LayoutDashboard, Tv, Video, Lightbulb, ClipboardCheck, Settings,
  Plus, X, Check, ChevronRight, ChevronDown, Moon, Sun,
  Play, Square, RotateCcw, Download, Upload, Eye, Edit3, Trash2,
  Search, Film, Mic, Image, FileText, Wand2, Package,
  CheckCircle2, XCircle, AlertCircle, Clock, Loader2,
  ArrowLeft, Save, ExternalLink, Filter, MoreVertical, Copy
} from 'lucide-react';

// ─── Constants ───────────────────────────────────────────────────────────────

const PHASES = [
  'Ideas Discovery', 'Script Generation', 'Media Collection',
  'Voice Generation', 'Video Assembly', 'QA & Package'
];

const PHASE_ICONS = [Lightbulb, FileText, Image, Mic, Film, Package];

const STATUS_COLORS = {
  pending:           { bg: 'bg-slate-500/10', text: 'text-slate-400', border: 'border-slate-500/30' },
  running:           { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30' },
  completed:         { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/30' },
  failed:            { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30' },
  waiting_approval:  { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/30' },
  approved:          { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/30' },
  rejected:          { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30' },
  edited:            { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/30' },
  draft:             { bg: 'bg-slate-500/10', text: 'text-slate-400', border: 'border-slate-500/30' },
  processing:        { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/30' },
  ready:             { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/30' },
  uploaded:          { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/30' },
  used:              { bg: 'bg-slate-500/10', text: 'text-slate-400', border: 'border-slate-500/30' },
  discarded:         { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/30' },
};

const PHASE_CIRCLE_COLORS = {
  pending:          'bg-slate-700 text-slate-400',
  running:          'bg-blue-600 text-white animate-pulse',
  completed:        'bg-emerald-600 text-white',
  failed:           'bg-red-600 text-white',
  waiting_approval: 'bg-amber-500 text-white',
  approved:         'bg-emerald-600 text-white',
  rejected:         'bg-red-600 text-white',
  edited:           'bg-purple-600 text-white',
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

const formatDuration = (seconds) => {
  if (!seconds) return '—';
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
};

const formatDate = (iso) => {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
};

const shortId = (id) => id ? id.slice(0, 8) : '';

// ─── API Service Layer ───────────────────────────────────────────────────────

const http = axios.create({ baseURL: '/api' });

const api = {
  // Channels
  listChannels:    ()           => http.get('/channels/').then(r => r.data),
  getChannel:      (id)         => http.get(`/channels/${id}`).then(r => r.data),
  createChannel:   (data)       => http.post('/channels/', data).then(r => r.data),
  updateChannel:   (id, data)   => http.patch(`/channels/${id}`, data).then(r => r.data),
  deleteChannel:   (id)         => http.delete(`/channels/${id}`).then(r => r.data),

  // Pipelines
  listPipelines:   (params)     => http.get('/pipelines/', { params }).then(r => r.data),
  getPipeline:     (id)         => http.get(`/pipelines/${id}`).then(r => r.data),
  createPipeline:  (data)       => http.post('/pipelines/', data).then(r => r.data),
  startPipeline:   (id)         => http.post(`/pipelines/${id}/start`).then(r => r.data),
  stopPipeline:    (id)         => http.post(`/pipelines/${id}/stop`).then(r => r.data),
  restartFrom:     (id, phase)  => http.post(`/pipelines/${id}/restart_from/${phase}`).then(r => r.data),
  deletePipeline:  (id)         => http.delete(`/pipelines/${id}`).then(r => r.data),

  // Videos
  listVideos:      (params)     => http.get('/videos/', { params }).then(r => r.data),
  getVideo:        (id)         => http.get(`/videos/${id}`).then(r => r.data),
  updateVideo:     (id, data)   => http.patch(`/videos/${id}`, data).then(r => r.data),
  uploadVoice:     (id, file)   => { const fd = new FormData(); fd.append('file', file); return http.post(`/videos/${id}/upload-voice`, fd, { headers: { 'Content-Type': 'multipart/form-data' }}).then(r => r.data); },
  deleteVideo:     (id)         => http.delete(`/videos/${id}/delete`).then(r => r.data),

  // Ideas
  listIdeas:       (params)     => http.get('/ideas/', { params }).then(r => r.data),
  createIdea:      (data)       => http.post('/ideas/', data).then(r => r.data),
  updateIdea:      (id, data)   => http.patch(`/ideas/${id}`, data).then(r => r.data),
  deleteIdea:      (id)         => http.delete(`/ideas/${id}`).then(r => r.data),

  // Approvals
  listPending:     ()           => http.get('/approvals/pending').then(r => r.data),
  resolveApproval: (id, data)   => http.post(`/approvals/${id}/resolve`, data).then(r => r.data),

  // Phase Toggles
  listToggles:     ()           => http.get('/phase-toggles/').then(r => r.data),
  updateToggle:    (num, data)  => http.patch(`/phase-toggles/${num}`, data).then(r => r.data),
  seedToggles:     ()           => http.post('/phase-toggles/seed').then(r => r.data),

};

// ─── UI Components ───────────────────────────────────────────────────────────

const Card = ({ children, className = '', onClick }) => (
  <div onClick={onClick} className={`bg-slate-800 rounded-lg border border-slate-700 ${onClick ? 'cursor-pointer hover:border-slate-500 transition-colors' : ''} ${className}`}>
    {children}
  </div>
);

const Badge = ({ children, status = 'pending' }) => {
  const colors = STATUS_COLORS[status] || STATUS_COLORS.pending;
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors.bg} ${colors.text} border ${colors.border}`}>
      {children}
    </span>
  );
};

const Button = ({ children, onClick, variant = 'default', size = 'default', className = '', disabled = false, icon: Icon }) => {
  const variants = {
    default:     'bg-blue-600 text-white hover:bg-blue-700',
    destructive: 'bg-red-600 text-white hover:bg-red-700',
    success:     'bg-emerald-600 text-white hover:bg-emerald-700',
    warning:     'bg-amber-600 text-white hover:bg-amber-700',
    outline:     'border border-slate-600 text-slate-300 hover:bg-slate-700',
    ghost:       'text-slate-400 hover:text-white hover:bg-slate-700',
  };
  const sizes = {
    default: 'h-9 px-4 py-2 text-sm',
    sm:      'h-8 px-3 text-xs',
    lg:      'h-11 px-6 text-base',
    icon:    'h-9 w-9',
  };
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {Icon && <Icon className="h-4 w-4" />}
      {children}
    </button>
  );
};

const Modal = ({ isOpen, onClose, title, children, footer, wide }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className={`${wide ? 'max-w-4xl' : 'max-w-lg'} w-full bg-slate-900 rounded-lg border border-slate-700 shadow-2xl max-h-[90vh] flex flex-col`} onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white"><X className="h-5 w-5" /></button>
        </div>
        <div className="p-6 overflow-y-auto flex-1">{children}</div>
        {footer && (
          <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-slate-700">{footer}</div>
        )}
      </div>
    </div>
  );
};

const Toggle = ({ checked, onChange, label }) => (
  <label className="flex items-center gap-3 cursor-pointer">
    <button
      onClick={() => onChange(!checked)}
      className={`relative w-11 h-6 rounded-full transition-colors ${checked ? 'bg-blue-600' : 'bg-slate-600'}`}
    >
      <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${checked ? 'translate-x-5' : ''}`} />
    </button>
    {label && <span className="text-sm text-slate-300">{label}</span>}
  </label>
);

const StatusBadge = ({ status }) => (
  <Badge status={status}>{(status || 'pending').replace(/_/g, ' ')}</Badge>
);

const StatCard = ({ label, value, icon: Icon }) => (
  <Card className="p-5">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm text-slate-400">{label}</p>
        <p className="text-2xl font-bold text-white mt-1">{value}</p>
      </div>
      <div className="h-12 w-12 rounded-lg bg-blue-600/10 flex items-center justify-center">
        <Icon className="h-6 w-6 text-blue-400" />
      </div>
    </div>
  </Card>
);

const EmptyState = ({ icon: Icon, title, description, action }) => (
  <div className="text-center py-16">
    <Icon className="h-12 w-12 text-slate-600 mx-auto mb-4" />
    <h3 className="text-lg font-medium text-slate-300 mb-2">{title}</h3>
    <p className="text-sm text-slate-500 mb-6">{description}</p>
    {action}
  </div>
);

const Input = ({ label, ...props }) => (
  <div>
    {label && <label className="block text-sm font-medium text-slate-300 mb-1.5">{label}</label>}
    <input className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-slate-500" {...props} />
  </div>
);

const Select = ({ label, children, ...props }) => (
  <div>
    {label && <label className="block text-sm font-medium text-slate-300 mb-1.5">{label}</label>}
    <select className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none" {...props}>
      {children}
    </select>
  </div>
);

const Textarea = ({ label, ...props }) => (
  <div>
    {label && <label className="block text-sm font-medium text-slate-300 mb-1.5">{label}</label>}
    <textarea className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder-slate-500 resize-none" {...props} />
  </div>
);

// ─── Dashboard Page ──────────────────────────────────────────────────────────

const DashboardPage = ({ navigate, channels }) => {
  const [stats, setStats] = useState({ channels: 0, active: 0, approvals: 0, ready: 0 });
  const [pipelines, setPipelines] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ channel_id: '', topic: '', mode: 'hybrid', style: 'cinematic' });
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const [pRes, aRes, vRes] = await Promise.all([
          api.listPipelines(),
          api.listPending().catch(() => ({ approvals: [] })),
          api.listVideos({ per_page: 100 }).catch(() => ({ videos: [] })),
        ]);
        setPipelines(pRes.pipelines || []);
        setStats({
          channels: channels.length,
          active: (pRes.pipelines || []).filter(p => p.status === 'running').length,
          approvals: (aRes.approvals || []).length,
          ready: (vRes.videos || []).filter(v => v.status === 'ready').length,
        });
      } catch (e) { console.error('Dashboard load error:', e); }
    };
    load();
  }, [channels]);

  const handleCreate = async () => {
    if (!form.channel_id) return;
    setCreating(true);
    try {
      const p = await api.createPipeline({
        channel_id: form.channel_id,
        topic: form.topic || undefined,
        config: { mode: form.mode, ...(form.mode === 'story' ? { style: form.style } : {}) },
        auto_start: true,
      });
      setShowModal(false);
      setForm({ channel_id: '', topic: '', mode: 'hybrid', style: 'cinematic' });
      navigate('pipeline', p.id);
    } catch (e) { console.error('Create pipeline error:', e); }
    setCreating(false);
  };

  const handleDelete = async (e, pipelineId, topic) => {
    e.stopPropagation();
    if (!confirm(`Delete pipeline "${topic || 'Untitled'}" and all associated files?`)) return;
    try {
      await api.deletePipeline(pipelineId);
      setPipelines(prev => prev.filter(p => p.id !== pipelineId));
    } catch (err) { console.error('Delete pipeline error:', err); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <Button icon={Plus} onClick={() => setShowModal(true)}>New Pipeline</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Channels" value={stats.channels} icon={Tv} />
        <StatCard label="Active Pipelines" value={stats.active} icon={Play} />
        <StatCard label="Pending Approvals" value={stats.approvals} icon={ClipboardCheck} />
        <StatCard label="Videos Ready" value={stats.ready} icon={Video} />
      </div>

      <Card>
        <div className="px-6 py-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-white">Recent Pipelines</h2>
        </div>
        {pipelines.length === 0 ? (
          <div className="p-6 text-center text-slate-500">No pipelines yet. Create one to get started.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-700 text-left text-xs text-slate-400 uppercase">
                  <th className="px-6 py-3">Pipeline</th>
                  <th className="px-6 py-3">Channel</th>
                  <th className="px-6 py-3">Phase</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Created</th>
                  <th className="px-6 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {pipelines.slice(0, 10).map(p => (
                  <tr key={p.id} onClick={() => navigate('pipeline', p.id)} className="border-b border-slate-700/50 hover:bg-slate-800/50 cursor-pointer transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-medium text-white">{p.topic || 'Untitled'}</div>
                      <div className="text-xs text-slate-500 font-mono">{shortId(p.id)}</div>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-300">{p.niche || '—'}</td>
                    <td className="px-6 py-4 text-sm text-slate-300">{p.current_phase ? PHASES[p.current_phase - 1] || `Phase ${p.current_phase}` : '—'}</td>
                    <td className="px-6 py-4"><StatusBadge status={p.status} /></td>
                    <td className="px-6 py-4 text-sm text-slate-400">{formatDate(p.created_at)}</td>
                    <td className="px-6 py-4">
                      <Button size="sm" variant="ghost" icon={Trash2} onClick={(e) => handleDelete(e, p.id, p.topic)} className="text-red-400 hover:text-red-300" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title="New Pipeline"
        footer={
          <>
            <Button variant="outline" onClick={() => setShowModal(false)}>Cancel</Button>
            <Button onClick={handleCreate} disabled={!form.channel_id || creating}>{creating ? 'Creating...' : 'Create & Start'}</Button>
          </>
        }
      >
        <div className="space-y-4">
          <Select label="Channel" value={form.channel_id} onChange={e => setForm({ ...form, channel_id: e.target.value })}>
            <option value="">Select a channel...</option>
            {channels.filter(c => c.active).map(c => (
              <option key={c.id} value={c.id}>{c.name} — {c.niche}</option>
            ))}
          </Select>
          <Input label="Topic (optional)" placeholder="e.g. Top 10 AI tools in 2026" value={form.topic} onChange={e => setForm({ ...form, topic: e.target.value })} />
          <Select label="Mode" value={form.mode} onChange={e => setForm({ ...form, mode: e.target.value })}>
            <option value="hybrid">Hybrid (Stock + AI)</option>
            <option value="story">Story Mode (All AI Images)</option>
          </Select>
          {form.mode === 'story' && (
            <Select label="Art Style" value={form.style} onChange={e => setForm({ ...form, style: e.target.value })}>
              <option value="cinematic">Cinematic Realism</option>
              <option value="anime">Anime / Manga</option>
              <option value="watercolor">Watercolor Painting</option>
              <option value="comic">Comic Book</option>
              <option value="gothic">Dark / Gothic</option>
              <option value="minimalist">Minimalist / Flat</option>
              <option value="retro">Retro / Vintage</option>
              <option value="fantasy">Fantasy / Dreamlike</option>
            </Select>
          )}
        </div>
      </Modal>
    </div>
  );
};

// ─── Channels Page ───────────────────────────────────────────────────────────

const ChannelsPage = ({ channels, refreshChannels }) => {
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: '', niche: '', youtube_channel_id: '', voice_id: '', language: 'en' });
  const [saving, setSaving] = useState(false);

  const openCreate = () => {
    setEditing(null);
    setForm({ name: '', niche: '', youtube_channel_id: '', voice_id: '', language: 'en' });
    setShowModal(true);
  };

  const openEdit = (ch) => {
    setEditing(ch);
    setForm({ name: ch.name, niche: ch.niche, youtube_channel_id: ch.youtube_channel_id || '', voice_id: ch.voice_id || '', language: ch.language || 'en' });
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.name || !form.niche) return;
    setSaving(true);
    try {
      if (editing) {
        await api.updateChannel(editing.id, form);
      } else {
        await api.createChannel(form);
      }
      setShowModal(false);
      refreshChannels();
    } catch (e) { console.error('Save channel error:', e); }
    setSaving(false);
  };

  const handleDelete = async (ch) => {
    if (!confirm(`Deactivate channel "${ch.name}"?`)) return;
    try {
      await api.updateChannel(ch.id, { active: false });
      refreshChannels();
    } catch (e) { console.error('Delete channel error:', e); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Channels</h1>
        <Button icon={Plus} onClick={openCreate}>New Channel</Button>
      </div>

      {channels.length === 0 ? (
        <EmptyState icon={Tv} title="No channels yet" description="Create a channel to start building your video pipeline." action={<Button icon={Plus} onClick={openCreate}>Create Channel</Button>} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {channels.map(ch => (
            <Card key={ch.id} className="p-5">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-lg bg-blue-600/10 flex items-center justify-center">
                    <Tv className="h-5 w-5 text-blue-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">{ch.name}</h3>
                    <p className="text-sm text-slate-400">{ch.niche}</p>
                  </div>
                </div>
                <Badge status={ch.active ? 'completed' : 'failed'}>{ch.active ? 'Active' : 'Inactive'}</Badge>
              </div>
              <div className="space-y-1.5 text-sm text-slate-400 mb-4">
                <div className="flex justify-between"><span>Language</span><span className="text-slate-300">{ch.language || 'en'}</span></div>
                {ch.voice_id && <div className="flex justify-between"><span>Voice ID</span><span className="text-slate-300 font-mono text-xs">{ch.voice_id}</span></div>}
                {ch.youtube_channel_id && <div className="flex justify-between"><span>YouTube ID</span><span className="text-slate-300 font-mono text-xs">{ch.youtube_channel_id}</span></div>}
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" icon={Edit3} onClick={() => openEdit(ch)}>Edit</Button>
                {ch.active && <Button size="sm" variant="ghost" icon={Trash2} onClick={() => handleDelete(ch)} className="text-red-400 hover:text-red-300">Deactivate</Button>}
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title={editing ? 'Edit Channel' : 'New Channel'}
        footer={
          <>
            <Button variant="outline" onClick={() => setShowModal(false)}>Cancel</Button>
            <Button onClick={handleSave} disabled={!form.name || !form.niche || saving}>{saving ? 'Saving...' : (editing ? 'Save Changes' : 'Create Channel')}</Button>
          </>
        }
      >
        <div className="space-y-4">
          <Input label="Channel Name" placeholder="e.g. AI Insights" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
          <Input label="Niche" placeholder="e.g. artificial intelligence" value={form.niche} onChange={e => setForm({ ...form, niche: e.target.value })} />
          <Input label="YouTube Channel ID (optional)" placeholder="UCxxxxxx" value={form.youtube_channel_id} onChange={e => setForm({ ...form, youtube_channel_id: e.target.value })} />
          <Input label="ElevenLabs Voice ID (optional)" placeholder="voice_id_here" value={form.voice_id} onChange={e => setForm({ ...form, voice_id: e.target.value })} />
          <Select label="Language" value={form.language} onChange={e => setForm({ ...form, language: e.target.value })}>
            <option value="en">English</option>
            <option value="es">Spanish</option>
          </Select>
        </div>
      </Modal>
    </div>
  );
};

// ─── Pipeline Detail Page ────────────────────────────────────────────────────

const PipelineDetailPage = ({ pipelineId, navigate }) => {
  const [pipeline, setPipeline] = useState(null);
  const [expandedPhase, setExpandedPhase] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [approvalNotes, setApprovalNotes] = useState('');
  const [editedOutput, setEditedOutput] = useState('');
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingApproval, setEditingApproval] = useState(null);
  const [restartPhase, setRestartPhase] = useState(null);
  const pollRef = useRef(null);

  const loadPipeline = useCallback(async () => {
    try {
      const data = await api.getPipeline(pipelineId);
      setPipeline(data);
    } catch (e) { console.error('Load pipeline error:', e); }
    setLoading(false);
  }, [pipelineId]);

  useEffect(() => {
    loadPipeline();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [loadPipeline]);

  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (pipeline?.status === 'running') {
      pollRef.current = setInterval(loadPipeline, 5000);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [pipeline?.status, loadPipeline]);

  const handleStart = async () => {
    setActionLoading(true);
    try { await api.startPipeline(pipelineId); await loadPipeline(); } catch (e) { console.error(e); }
    setActionLoading(false);
  };

  const handleStop = async () => {
    setActionLoading(true);
    try { await api.stopPipeline(pipelineId); await loadPipeline(); } catch (e) { console.error(e); }
    setActionLoading(false);
  };

  const handleRestart = async (phaseNum) => {
    setActionLoading(true);
    try { await api.restartFrom(pipelineId, phaseNum); setRestartPhase(null); await loadPipeline(); } catch (e) { console.error(e); }
    setActionLoading(false);
  };

  const handleApproval = async (approvalId, decision) => {
    setActionLoading(true);
    try {
      const body = { decision, notes: approvalNotes || undefined };
      if (decision === 'edited') {
        try { body.edited_output = JSON.parse(editedOutput); } catch { alert('Invalid JSON'); setActionLoading(false); return; }
      }
      await api.resolveApproval(approvalId, body);
      setApprovalNotes('');
      setShowEditModal(false);
      await loadPipeline();
    } catch (e) { console.error(e); }
    setActionLoading(false);
  };

  const openEditApproval = (phase) => {
    setEditingApproval(phase);
    setEditedOutput(JSON.stringify(phase.output_data || {}, null, 2));
    setShowEditModal(true);
  };

  if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="h-8 w-8 text-blue-400 animate-spin" /></div>;
  if (!pipeline) return <div className="text-center py-16 text-slate-400">Pipeline not found.</div>;

  const phases = pipeline.phases || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('dashboard')} className="text-slate-400 hover:text-white"><ArrowLeft className="h-5 w-5" /></button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-white">{pipeline.topic || 'Untitled Pipeline'}</h1>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-sm text-slate-400 font-mono">{shortId(pipeline.id)}</span>
            <StatusBadge status={pipeline.status} />
            {pipeline.niche && <span className="text-sm text-slate-400">{pipeline.niche}</span>}
          </div>
        </div>
        <div className="flex gap-2">
          {(pipeline.status === 'pending' || pipeline.status === 'failed') && (
            <Button icon={Play} onClick={handleStart} disabled={actionLoading}>Start</Button>
          )}
          {pipeline.status === 'running' && (
            <Button icon={Square} variant="destructive" onClick={handleStop} disabled={actionLoading}>Stop</Button>
          )}
          <Button icon={RotateCcw} variant="outline" onClick={() => setRestartPhase(1)} disabled={actionLoading}>Restart</Button>
        </div>
      </div>

      {pipeline.error_message && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-sm text-red-400">
          <strong>Error:</strong> {pipeline.error_message}
        </div>
      )}

      {pipeline.status === 'running' && (
        <div className="flex items-center gap-2 text-sm text-blue-400">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Pipeline is running — auto-refreshing every 5s</span>
        </div>
      )}

      <div className="space-y-3">
        {PHASES.map((phaseName, idx) => {
          const phaseNum = idx + 1;
          const phaseResult = phases.find(pr => pr.phase_number === phaseNum);
          const status = phaseResult?.status || 'pending';
          const isExpanded = expandedPhase === phaseNum;
          const PhaseIcon = PHASE_ICONS[idx];
          const approval = phaseResult?.approval;

          return (
            <Card key={phaseNum} className="overflow-hidden">
              <div
                className="flex items-center gap-4 px-5 py-4 cursor-pointer hover:bg-slate-750"
                onClick={() => setExpandedPhase(isExpanded ? null : phaseNum)}
              >
                <div className={`h-10 w-10 rounded-full flex items-center justify-center text-sm font-bold ${PHASE_CIRCLE_COLORS[status] || PHASE_CIRCLE_COLORS.pending}`}>
                  {phaseNum}
                </div>
                <div className="flex items-center gap-2 flex-1">
                  <PhaseIcon className="h-4 w-4 text-slate-400" />
                  <span className="font-medium text-white">{phaseName}</span>
                </div>
                <div className="flex items-center gap-3">
                  {phaseResult?.duration_seconds && (
                    <span className="text-xs text-slate-500">{formatDuration(phaseResult.duration_seconds)}</span>
                  )}
                  <StatusBadge status={status} />
                  {isExpanded ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
                </div>
              </div>

              {isExpanded && (
                <div className="border-t border-slate-700 px-5 py-4 space-y-4">
                  {status === 'waiting_approval' && approval && (
                    <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 space-y-3">
                      <p className="text-sm font-medium text-amber-400">Waiting for approval</p>
                      <Textarea
                        placeholder="Reviewer notes (optional)..."
                        value={approvalNotes}
                        onChange={e => setApprovalNotes(e.target.value)}
                        rows={2}
                      />
                      <div className="flex gap-2">
                        <Button size="sm" icon={Check} variant="success" onClick={() => handleApproval(approval.id, 'approved')} disabled={actionLoading}>Approve</Button>
                        <Button size="sm" icon={X} variant="destructive" onClick={() => handleApproval(approval.id, 'rejected')} disabled={actionLoading}>Reject</Button>
                        <Button size="sm" icon={Edit3} variant="outline" onClick={() => openEditApproval(phaseResult)} disabled={actionLoading}>Edit & Approve</Button>
                      </div>
                    </div>
                  )}

                  {phaseResult?.output_data && (
                    <div>
                      <p className="text-xs font-medium text-slate-400 uppercase mb-2">Output</p>
                      <pre className="bg-slate-950 border border-slate-700 rounded-lg p-4 text-xs text-slate-300 overflow-auto max-h-96 whitespace-pre-wrap">
                        {JSON.stringify(phaseResult.output_data, null, 2)}
                      </pre>
                    </div>
                  )}

                  {phaseResult?.error_log && (
                    <div>
                      <p className="text-xs font-medium text-red-400 uppercase mb-2">Error Log</p>
                      <pre className="bg-red-950/30 border border-red-500/20 rounded-lg p-4 text-xs text-red-300 overflow-auto max-h-48 whitespace-pre-wrap">
                        {phaseResult.error_log}
                      </pre>
                    </div>
                  )}

                  {(status === 'completed' || status === 'failed') && (
                    <Button size="sm" variant="outline" icon={RotateCcw} onClick={() => handleRestart(phaseNum)} disabled={actionLoading}>
                      Restart from Phase {phaseNum}
                    </Button>
                  )}
                </div>
              )}
            </Card>
          );
        })}
      </div>

      {/* Restart from phase picker */}
      <Modal
        isOpen={restartPhase !== null && restartPhase === 1}
        onClose={() => setRestartPhase(null)}
        title="Restart Pipeline"
        footer={
          <>
            <Button variant="outline" onClick={() => setRestartPhase(null)}>Cancel</Button>
            <Button icon={RotateCcw} onClick={() => handleRestart(restartPhase)} disabled={actionLoading}>Restart from Phase {restartPhase}</Button>
          </>
        }
      >
        <div className="space-y-2">
          <p className="text-sm text-slate-400 mb-4">Select which phase to restart from:</p>
          {PHASES.map((name, idx) => (
            <button
              key={idx}
              onClick={() => setRestartPhase(idx + 1)}
              className={`w-full text-left px-4 py-3 rounded-lg border transition-colors ${restartPhase === idx + 1 ? 'border-blue-500 bg-blue-500/10 text-blue-400' : 'border-slate-700 hover:border-slate-500 text-slate-300'}`}
            >
              <span className="font-medium">Phase {idx + 1}:</span> {name}
            </button>
          ))}
        </div>
      </Modal>

      {/* Edit approval modal */}
      <Modal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        title="Edit & Approve"
        wide
        footer={
          <>
            <Button variant="outline" onClick={() => setShowEditModal(false)}>Cancel</Button>
            <Button icon={Check} variant="success" onClick={() => handleApproval(editingApproval?.approval?.id, 'edited')} disabled={actionLoading}>Save & Approve</Button>
          </>
        }
      >
        <div className="space-y-4">
          <Textarea
            label="Reviewer Notes"
            placeholder="Notes about your edits..."
            value={approvalNotes}
            onChange={e => setApprovalNotes(e.target.value)}
            rows={2}
          />
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">Edited Output (JSON)</label>
            <textarea
              className="w-full px-3 py-2 bg-slate-950 border border-slate-600 rounded-md text-emerald-400 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              value={editedOutput}
              onChange={e => setEditedOutput(e.target.value)}
              rows={20}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

// ─── Videos Page ─────────────────────────────────────────────────────────────

const VideosPage = ({ navigate, channels }) => {
  const [videos, setVideos] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [channelFilter, setChannelFilter] = useState('');
  const [loading, setLoading] = useState(true);

  const loadVideos = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, per_page: 12 };
      if (channelFilter) params.channel_id = channelFilter;
      const data = await api.listVideos(params);
      setVideos(data.videos || []);
      setTotal(data.total || 0);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [page, channelFilter]);

  useEffect(() => { loadVideos(); }, [loadVideos]);

  const totalPages = Math.ceil(total / 12) || 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Videos <span className="text-sm font-normal text-slate-400">({total})</span></h1>
        <div className="flex items-center gap-3">
          <Select value={channelFilter} onChange={e => { setChannelFilter(e.target.value); setPage(1); }}>
            <option value="">All channels</option>
            {channels.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </Select>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64"><Loader2 className="h-8 w-8 text-blue-400 animate-spin" /></div>
      ) : videos.length === 0 ? (
        <EmptyState icon={Video} title="No videos yet" description="Videos will appear here after pipeline runs complete." />
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {videos.map(v => (
              <Card key={v.id} onClick={() => navigate('video', v.id)} className="overflow-hidden">
                <div className="aspect-video bg-slate-700 flex items-center justify-center relative">
                  {v.thumbnail_path ? (
                    <img src={`/api/videos/${v.id}/download/thumbnail`} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <Film className="h-12 w-12 text-slate-500" />
                  )}
                  {v.duration_seconds && (
                    <span className="absolute bottom-2 right-2 bg-black/80 text-white text-xs px-2 py-0.5 rounded">{formatDuration(v.duration_seconds)}</span>
                  )}
                </div>
                <div className="p-4">
                  <h3 className="font-medium text-white text-sm line-clamp-2 mb-2">{v.title || 'Untitled Video'}</h3>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400">{formatDate(v.created_at)}</span>
                    <StatusBadge status={v.status} />
                  </div>
                </div>
              </Card>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</Button>
              <span className="text-sm text-slate-400">Page {page} of {totalPages}</span>
              <Button size="sm" variant="outline" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</Button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

// ─── Video Detail Page ───────────────────────────────────────────────────────

const VideoDetailPage = ({ videoId, navigate }) => {
  const [video, setVideo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ title: '', description: '', tags_list: '' });
  const [voiceFile, setVoiceFile] = useState(null);
  const [uploadingVoice, setUploadingVoice] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.getVideo(videoId);
        setVideo(data);
        setForm({
          title: data.title || '',
          description: data.description || '',
          tags_list: (data.tags_list || []).join(', '),
        });
      } catch (e) { console.error(e); }
      setLoading(false);
    };
    load();
  }, [videoId]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const tags = form.tags_list.split(',').map(t => t.trim()).filter(Boolean);
      await api.updateVideo(videoId, { title: form.title, description: form.description, tags_list: tags });
      const data = await api.getVideo(videoId);
      setVideo(data);
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const handleDownload = (type) => {
    window.open(`/api/videos/${videoId}/download/${type}`, '_blank');
  };

  const handleVoiceUpload = async () => {
    if (!voiceFile) return;
    setUploadingVoice(true);
    try {
      await api.uploadVoice(videoId, voiceFile);
      setVoiceFile(null);
      const data = await api.getVideo(videoId);
      setVideo(data);
    } catch (e) { console.error(e); }
    setUploadingVoice(false);
  };


  if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="h-8 w-8 text-blue-400 animate-spin" /></div>;
  if (!video) return <div className="text-center py-16 text-slate-400">Video not found.</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('videos')} className="text-slate-400 hover:text-white"><ArrowLeft className="h-5 w-5" /></button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-white">{video.title || 'Untitled Video'}</h1>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-sm text-slate-400 font-mono">{shortId(video.id)}</span>
            <StatusBadge status={video.status} />
            {video.duration_seconds && <span className="text-sm text-slate-400">{formatDuration(video.duration_seconds)}</span>}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: Edit form */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="p-6 space-y-4">
            <h2 className="text-lg font-semibold text-white">Details</h2>
            <Input label="Title" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
            <Textarea label="Description" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} rows={6} />
            <Input label="Tags (comma-separated)" value={form.tags_list} onChange={e => setForm({ ...form, tags_list: e.target.value })} placeholder="tag1, tag2, tag3" />
            <Button icon={Save} onClick={handleSave} disabled={saving}>{saving ? 'Saving...' : 'Save Changes'}</Button>
          </Card>

          {/* Script preview */}
          {video.script_text && (
            <Card className="p-6">
              <h2 className="text-lg font-semibold text-white mb-3">Script</h2>
              <pre className="bg-slate-950 border border-slate-700 rounded-lg p-4 text-sm text-slate-300 overflow-auto max-h-64 whitespace-pre-wrap">{video.script_text}</pre>
            </Card>
          )}
        </div>

        {/* Right column: Actions */}
        <div className="space-y-6">
          {/* Downloads */}
          <Card className="p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Downloads</h2>
            <div className="space-y-2">
              {video.final_video_path && <Button variant="outline" icon={Film} className="w-full justify-start" onClick={() => handleDownload('video')}>Download Video</Button>}
              {video.audio_path && <Button variant="outline" icon={Mic} className="w-full justify-start" onClick={() => handleDownload('audio')}>Download Audio</Button>}
              {video.thumbnail_path && <Button variant="outline" icon={Image} className="w-full justify-start" onClick={() => handleDownload('thumbnail')}>Download Thumbnail</Button>}
              {video.subtitle_path && <Button variant="outline" icon={FileText} className="w-full justify-start" onClick={() => handleDownload('subtitle')}>Download Subtitles</Button>}
              {!video.final_video_path && !video.audio_path && !video.thumbnail_path && (
                <p className="text-sm text-slate-500">No files available yet.</p>
              )}
            </div>
          </Card>

          {/* Voice Upload */}
          <Card className="p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Voice Override</h2>
            <p className="text-sm text-slate-400 mb-3">Upload a custom voice recording to replace the generated audio.</p>
            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*"
              className="hidden"
              onChange={e => setVoiceFile(e.target.files[0])}
            />
            <div className="space-y-2">
              <Button variant="outline" icon={Upload} className="w-full" onClick={() => fileInputRef.current?.click()}>
                {voiceFile ? voiceFile.name : 'Choose Audio File'}
              </Button>
              {voiceFile && (
                <Button icon={Upload} className="w-full" onClick={handleVoiceUpload} disabled={uploadingVoice}>
                  {uploadingVoice ? 'Uploading...' : 'Upload Voice'}
                </Button>
              )}
            </div>
          </Card>

        </div>
      </div>
    </div>
  );
};

// ─── Ideas Page ──────────────────────────────────────────────────────────────

const IdeasPage = ({ channels }) => {
  const [ideas, setIdeas] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [channelFilter, setChannelFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ channel_id: '', topic: '', score: '', source: 'manual' });
  const [saving, setSaving] = useState(false);

  const loadIdeas = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, per_page: 20 };
      if (channelFilter) params.channel_id = channelFilter;
      if (statusFilter) params.status = statusFilter;
      const data = await api.listIdeas(params);
      setIdeas(data.ideas || []);
      setTotal(data.total || 0);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [page, channelFilter, statusFilter]);

  useEffect(() => { loadIdeas(); }, [loadIdeas]);

  const handleCreate = async () => {
    if (!form.channel_id || !form.topic) return;
    setSaving(true);
    try {
      await api.createIdea({
        channel_id: form.channel_id,
        topic: form.topic,
        score: form.score ? Number(form.score) : undefined,
        source: form.source,
      });
      setShowModal(false);
      setForm({ channel_id: '', topic: '', score: '', source: 'manual' });
      loadIdeas();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const handleAction = async (idea, action) => {
    try {
      if (action === 'delete') {
        await api.deleteIdea(idea.id);
      } else {
        await api.updateIdea(idea.id, { status: action });
      }
      loadIdeas();
    } catch (e) { console.error(e); }
  };

  const totalPages = Math.ceil(total / 20) || 1;
  const channelMap = Object.fromEntries(channels.map(c => [c.id, c.name]));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Ideas <span className="text-sm font-normal text-slate-400">({total})</span></h1>
        <Button icon={Plus} onClick={() => setShowModal(true)}>New Idea</Button>
      </div>

      <div className="flex items-center gap-3">
        <Select value={channelFilter} onChange={e => { setChannelFilter(e.target.value); setPage(1); }}>
          <option value="">All channels</option>
          {channels.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </Select>
        <Select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}>
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="discarded">Discarded</option>
          <option value="used">Used</option>
        </Select>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64"><Loader2 className="h-8 w-8 text-blue-400 animate-spin" /></div>
      ) : ideas.length === 0 ? (
        <EmptyState icon={Lightbulb} title="No ideas yet" description="Ideas are discovered by the pipeline or can be added manually." action={<Button icon={Plus} onClick={() => setShowModal(true)}>Add Idea</Button>} />
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-700 text-left text-xs text-slate-400 uppercase">
                  <th className="px-6 py-3">Topic</th>
                  <th className="px-6 py-3">Channel</th>
                  <th className="px-6 py-3">Score</th>
                  <th className="px-6 py-3">Source</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Created</th>
                  <th className="px-6 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {ideas.map(idea => (
                  <tr key={idea.id} className="border-b border-slate-700/50 hover:bg-slate-800/50">
                    <td className="px-6 py-4">
                      <span className="font-medium text-white">{idea.topic}</span>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-300">{channelMap[idea.channel_id] || shortId(idea.channel_id)}</td>
                    <td className="px-6 py-4 text-sm text-slate-300">{idea.score != null ? idea.score : '—'}</td>
                    <td className="px-6 py-4">
                      <span className="text-xs text-slate-400 bg-slate-700/50 px-2 py-0.5 rounded">{idea.source || 'manual'}</span>
                    </td>
                    <td className="px-6 py-4"><StatusBadge status={idea.status} /></td>
                    <td className="px-6 py-4 text-sm text-slate-400">{formatDate(idea.created_at)}</td>
                    <td className="px-6 py-4">
                      <div className="flex gap-1">
                        {idea.status === 'pending' && (
                          <>
                            <Button size="sm" variant="ghost" icon={Check} onClick={() => handleAction(idea, 'approved')} className="text-emerald-400" />
                            <Button size="sm" variant="ghost" icon={X} onClick={() => handleAction(idea, 'discarded')} className="text-amber-400" />
                          </>
                        )}
                        <Button size="sm" variant="ghost" icon={Trash2} onClick={() => handleAction(idea, 'delete')} className="text-red-400" />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Previous</Button>
          <span className="text-sm text-slate-400">Page {page} of {totalPages}</span>
          <Button size="sm" variant="outline" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</Button>
        </div>
      )}

      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title="New Idea"
        footer={
          <>
            <Button variant="outline" onClick={() => setShowModal(false)}>Cancel</Button>
            <Button onClick={handleCreate} disabled={!form.channel_id || !form.topic || saving}>{saving ? 'Creating...' : 'Create Idea'}</Button>
          </>
        }
      >
        <div className="space-y-4">
          <Select label="Channel" value={form.channel_id} onChange={e => setForm({ ...form, channel_id: e.target.value })}>
            <option value="">Select a channel...</option>
            {channels.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </Select>
          <Input label="Topic" placeholder="e.g. How AI is changing healthcare" value={form.topic} onChange={e => setForm({ ...form, topic: e.target.value })} />
          <Input label="Score (optional)" type="number" placeholder="0-100" value={form.score} onChange={e => setForm({ ...form, score: e.target.value })} />
          <Select label="Source" value={form.source} onChange={e => setForm({ ...form, source: e.target.value })}>
            <option value="manual">Manual</option>
            <option value="google_trends">Google Trends</option>
            <option value="serpapi">SerpAPI</option>
            <option value="youtube">YouTube</option>
          </Select>
        </div>
      </Modal>
    </div>
  );
};

// ─── Approvals Page ──────────────────────────────────────────────────────────

const ApprovalsPage = ({ navigate }) => {
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [notes, setNotes] = useState({});
  const [editModal, setEditModal] = useState(null);
  const [editedOutput, setEditedOutput] = useState('');

  const load = async () => {
    try {
      const data = await api.listPending();
      setApprovals(data.approvals || []);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleResolve = async (approval, decision) => {
    setActionLoading(approval.id);
    try {
      const body = { decision, notes: notes[approval.id] || undefined };
      if (decision === 'edited') {
        try { body.edited_output = JSON.parse(editedOutput); } catch { alert('Invalid JSON'); setActionLoading(null); return; }
      }
      await api.resolveApproval(approval.id, body);
      setEditModal(null);
      load();
    } catch (e) { console.error(e); }
    setActionLoading(null);
  };

  if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="h-8 w-8 text-blue-400 animate-spin" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Approvals <span className="text-sm font-normal text-slate-400">({approvals.length} pending)</span></h1>
        <Button variant="outline" icon={RotateCcw} onClick={() => { setLoading(true); load(); }}>Refresh</Button>
      </div>

      {approvals.length === 0 ? (
        <EmptyState icon={ClipboardCheck} title="No pending approvals" description="All caught up! Approvals will appear here when pipeline phases need review." />
      ) : (
        <div className="space-y-4">
          {approvals.map(approval => (
            <Card key={approval.id} className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="font-semibold text-white">{approval.phase_name || PHASES[approval.phase_number - 1] || `Phase ${approval.phase_number}`}</h3>
                    <Badge status="waiting_approval">Phase {approval.phase_number}</Badge>
                  </div>
                  <p className="text-sm text-slate-400">
                    Pipeline <button onClick={() => navigate('pipeline', approval.pipeline_run_id)} className="text-blue-400 hover:underline font-mono">{shortId(approval.pipeline_run_id)}</button>
                  </p>
                </div>
                <span className="text-xs text-slate-500">{formatDate(approval.created_at)}</span>
              </div>

              {(approval.original_output || approval.phase_output) && (
                <div className="mb-4">
                  <p className="text-xs font-medium text-slate-400 uppercase mb-2">Output Preview</p>
                  <pre className="bg-slate-950 border border-slate-700 rounded-lg p-3 text-xs text-slate-300 overflow-auto max-h-48 whitespace-pre-wrap">
                    {JSON.stringify(approval.phase_output || approval.original_output, null, 2).slice(0, 1000)}
                    {JSON.stringify(approval.phase_output || approval.original_output, null, 2).length > 1000 ? '\n...' : ''}
                  </pre>
                </div>
              )}

              <div className="space-y-3">
                <Input
                  placeholder="Reviewer notes (optional)..."
                  value={notes[approval.id] || ''}
                  onChange={e => setNotes({ ...notes, [approval.id]: e.target.value })}
                />
                <div className="flex gap-2">
                  <Button size="sm" icon={Check} variant="success" onClick={() => handleResolve(approval, 'approved')} disabled={actionLoading === approval.id}>Approve</Button>
                  <Button size="sm" icon={X} variant="destructive" onClick={() => handleResolve(approval, 'rejected')} disabled={actionLoading === approval.id}>Reject</Button>
                  <Button size="sm" icon={Edit3} variant="outline" onClick={() => { setEditModal(approval); setEditedOutput(JSON.stringify(approval.phase_output || approval.original_output || {}, null, 2)); }} disabled={actionLoading === approval.id}>Edit & Approve</Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal
        isOpen={!!editModal}
        onClose={() => setEditModal(null)}
        title={`Edit & Approve — ${editModal?.phase_name || ''}`}
        wide
        footer={
          <>
            <Button variant="outline" onClick={() => setEditModal(null)}>Cancel</Button>
            <Button icon={Check} variant="success" onClick={() => handleResolve(editModal, 'edited')} disabled={actionLoading === editModal?.id}>Save & Approve</Button>
          </>
        }
      >
        <div className="space-y-4">
          <Input
            label="Reviewer Notes"
            placeholder="Notes about your edits..."
            value={notes[editModal?.id] || ''}
            onChange={e => setNotes({ ...notes, [editModal?.id]: e.target.value })}
          />
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5">Edited Output (JSON)</label>
            <textarea
              className="w-full px-3 py-2 bg-slate-950 border border-slate-600 rounded-md text-emerald-400 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              value={editedOutput}
              onChange={e => setEditedOutput(e.target.value)}
              rows={20}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

// ─── Settings Page ───────────────────────────────────────────────────────────

const SettingsPage = () => {
  const [toggles, setToggles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [changes, setChanges] = useState({});

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.listToggles();
        let list = data.toggles || [];
        if (list.length === 0) {
          await api.seedToggles();
          const seeded = await api.listToggles();
          list = seeded.toggles || [];
        }
        setToggles(list);
      } catch (e) { console.error(e); }
      setLoading(false);
    };
    load();
  }, []);

  const handleToggle = (phaseNum, field, value) => {
    setChanges(prev => ({
      ...prev,
      [phaseNum]: { ...(prev[phaseNum] || {}), [field]: value },
    }));
  };

  const getVal = (toggle, field) => {
    if (changes[toggle.phase_number]?.[field] !== undefined) return changes[toggle.phase_number][field];
    return toggle[field];
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const promises = Object.entries(changes).map(([phaseNum, data]) =>
        api.updateToggle(Number(phaseNum), data)
      );
      await Promise.all(promises);
      const fresh = await api.listToggles();
      setToggles(fresh.toggles || []);
      setChanges({});
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const hasChanges = Object.keys(changes).length > 0;

  if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="h-8 w-8 text-blue-400 animate-spin" /></div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        {hasChanges && (
          <Button icon={Save} onClick={handleSave} disabled={saving}>{saving ? 'Saving...' : 'Save Changes'}</Button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {toggles.map(toggle => {
          const idx = toggle.phase_number - 1;
          const PhaseIcon = PHASE_ICONS[idx] || Package;
          return (
            <Card key={toggle.id || toggle.phase_number} className="p-5">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-10 w-10 rounded-lg bg-blue-600/10 flex items-center justify-center">
                  <PhaseIcon className="h-5 w-5 text-blue-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">Phase {toggle.phase_number}</h3>
                  <p className="text-sm text-slate-400">{toggle.phase_name || PHASES[idx]}</p>
                </div>
              </div>
              <div className="space-y-3">
                <Toggle
                  label="Enabled"
                  checked={getVal(toggle, 'is_enabled')}
                  onChange={v => handleToggle(toggle.phase_number, 'is_enabled', v)}
                />
                <Toggle
                  label="Require Approval"
                  checked={getVal(toggle, 'requires_approval')}
                  onChange={v => handleToggle(toggle.phase_number, 'requires_approval', v)}
                />
              </div>
            </Card>
          );
        })}
      </div>

      {toggles.length === 0 && (
        <EmptyState icon={Settings} title="No phase toggles" description="Phase toggles will be seeded automatically." />
      )}
    </div>
  );
};

// ─── Main App ────────────────────────────────────────────────────────────────

const NAV_ITEMS = [
  { key: 'dashboard',  label: 'Dashboard',  icon: LayoutDashboard },
  { key: 'channels',   label: 'Channels',   icon: Tv },
  { key: 'videos',     label: 'Videos',     icon: Video },
  { key: 'ideas',      label: 'Ideas',      icon: Lightbulb },
  { key: 'approvals',  label: 'Approvals',  icon: ClipboardCheck },
  { key: 'settings',   label: 'Settings',   icon: Settings },
];

export default function App() {
  const [view, setView] = useState('dashboard');
  const [detailId, setDetailId] = useState(null);
  const [channels, setChannels] = useState([]);
  const [darkMode, setDarkMode] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const navigate = (page, id = null) => {
    setView(page);
    setDetailId(id);
    window.scrollTo(0, 0);
  };

  const refreshChannels = async () => {
    try {
      const data = await api.listChannels();
      setChannels(data.channels || []);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { refreshChannels(); }, []);

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  const renderContent = () => {
    switch (view) {
      case 'dashboard':  return <DashboardPage navigate={navigate} channels={channels} />;
      case 'channels':   return <ChannelsPage channels={channels} refreshChannels={refreshChannels} />;
      case 'pipeline':   return <PipelineDetailPage pipelineId={detailId} navigate={navigate} />;
      case 'videos':     return <VideosPage navigate={navigate} channels={channels} />;
      case 'video':      return <VideoDetailPage videoId={detailId} navigate={navigate} />;
      case 'ideas':      return <IdeasPage channels={channels} />;
      case 'approvals':  return <ApprovalsPage navigate={navigate} />;
      case 'settings':   return <SettingsPage />;
      default:           return <DashboardPage navigate={navigate} channels={channels} />;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white flex">
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? 'w-64' : 'w-16'} bg-slate-900 border-r border-slate-800 flex flex-col transition-all duration-200`}>
        <div className="px-4 py-5 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
              <Film className="h-5 w-5 text-white" />
            </div>
            {sidebarOpen && <span className="font-bold text-lg">YT Auto</span>}
          </div>
        </div>

        <nav className="flex-1 py-4 px-2 space-y-1">
          {NAV_ITEMS.map(item => {
            const isActive = view === item.key || (item.key === 'dashboard' && view === 'pipeline');
            return (
              <button
                key={item.key}
                onClick={() => navigate(item.key)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-600/10 text-blue-400'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
              >
                <item.icon className="h-5 w-5 flex-shrink-0" />
                {sidebarOpen && <span>{item.label}</span>}
              </button>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-800 space-y-2">
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            {sidebarOpen && <span>{darkMode ? 'Light Mode' : 'Dark Mode'}</span>}
          </button>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <ChevronRight className={`h-5 w-5 transition-transform ${sidebarOpen ? 'rotate-180' : ''}`} />
            {sidebarOpen && <span>Collapse</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto px-6 py-8">
          {renderContent()}
        </div>
      </main>
    </div>
  );
}
