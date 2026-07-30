'use client'

import { useState, useEffect } from 'react'
import { apiFetch } from '../../../lib/auth'

interface Agent { id: string; handle: string; display_name: string; status: string }

export default function SettingsPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [autoLevels, setAutoLevels] = useState<Record<string, string>>({})
  const [stopping, setStopping] = useState<string | null>(null)
  const [status, setStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [profile, setProfile] = useState<any>(null)
  const [editName, setEditName] = useState('')
  const [editHandle, setEditHandle] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => { loadData() }, [])

  async function loadData() {
    try {
      const [a, st, me] = await Promise.all([
        apiFetch('/api/agents'),
        apiFetch('/api/admin/status').catch(() => null),
        apiFetch('/api/users/me').catch(() => null),
      ])
      setAgents(a.agents || [])
      if (st) setStatus(st)
      if (me) {
        setProfile(me)
        setEditName(me.display_name || '')
        setEditHandle(me.handle || '')
      }
      // Load automation levels
      const levels: Record<string, string> = {}
      for (const agent of (a.agents || [])) {
        try {
          const r = await apiFetch(`/api/security/agents/${agent.id}/automation`)
          levels[agent.id] = r.automation_level
        } catch {}
      }
      setAutoLevels(levels)
    } catch {}
    setLoading(false)
  }

  const changeAutomation = async (agentId: string, level: string) => {
    await apiFetch(`/api/security/agents/${agentId}/automation`, {
      method: 'PATCH', body: JSON.stringify({ automation_level: level })
    })
    loadData()
  }

  const emergencyStop = async (agentId: string) => {
    setStopping(agentId)
    await apiFetch(`/api/security/agents/${agentId}/emergency-stop`, { method: 'POST', body: '{}' })
    loadData()
  }

  const saveProfile = async () => {
    setSaving(true)
    try {
      await apiFetch('/api/users/me', {
        method: 'PATCH',
        body: JSON.stringify({ display_name: editName, handle: editHandle }),
      })
      loadData()
    } catch {}
    setSaving(false)
  }

  if (loading) return <div className="text-gray-500 text-center py-12">加载中...</div>

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">⚙️ 设置</h1>

      {/* Profile */}
      <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 mb-6">
        <h2 className="text-lg font-semibold mb-4">👤 个人资料</h2>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-gray-400 block mb-1">邮箱</label>
            <input value={profile?.email || ''} disabled className="w-full px-3 py-2 rounded bg-gray-800/50 border border-gray-700 text-sm text-gray-500" />
          </div>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-xs text-gray-400 block mb-1">显示名称</label>
              <input value={editName} onChange={e => setEditName(e.target.value)} className="w-full px-3 py-2 rounded bg-gray-800 border border-gray-700 text-sm" />
            </div>
            <div className="flex-1">
              <label className="text-xs text-gray-400 block mb-1">Handle (@username)</label>
              <input value={editHandle} onChange={e => setEditHandle(e.target.value)} className="w-full px-3 py-2 rounded bg-gray-800 border border-gray-700 text-sm font-mono" />
            </div>
          </div>
          <button onClick={saveProfile} disabled={saving} className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm font-medium disabled:opacity-50">
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>

      {/* Agent Security */}
      <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 mb-6">
        <h2 className="text-lg font-semibold mb-4">🛡️ Agent 安全控制</h2>
        <div className="space-y-3">
          {agents.map(a => (
            <div key={a.id} className="flex items-center justify-between py-2 px-3 bg-gray-800/50 rounded-lg">
              <div>
                <span className="font-medium text-sm">@{a.handle}</span>
                <span className={`ml-2 text-xs ${a.status === 'active' ? 'text-green-400' : 'text-yellow-400'}`}>{a.status}</span>
              </div>
              <div className="flex items-center gap-2">
                <select
                  value={autoLevels[a.id] || 'human_review'}
                  onChange={e => changeAutomation(a.id, e.target.value)}
                  className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs"
                >
                  <option value="auto">🤖 自动</option>
                  <option value="human_review">👤 人工审核</option>
                  <option value="disabled">🚫 禁用</option>
                </select>
                <button
                  onClick={() => emergencyStop(a.id)}
                  disabled={stopping === a.id}
                  className="text-xs px-3 py-1 bg-red-900/50 hover:bg-red-800 rounded text-red-400 disabled:opacity-50"
                >
                  {stopping === a.id ? '...' : '🔴 急停'}
                </button>
              </div>
            </div>
          ))}
          {agents.length === 0 && <p className="text-gray-500 text-sm">还没有 Agent</p>}
        </div>
      </div>

      {/* System Info */}
      {status && (
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <h2 className="text-lg font-semibold mb-4">📊 系统信息</h2>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {Object.entries(status.counts || {}).map(([key, val]) => (
              <div key={key} className="flex justify-between py-1 px-3 bg-gray-800/50 rounded">
                <span className="text-gray-400 capitalize">{key.replace(/_/g, ' ')}</span>
                <span className="font-medium">{val as number}</span>
              </div>
            ))}
          </div>
          <div className="text-xs text-gray-500 mt-3">
            版本: v{status.version} | 服务状态: {status.status}
          </div>
        </div>
      )}
    </div>
  )
}
