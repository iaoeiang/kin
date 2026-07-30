'use client'

import { useState, useEffect } from 'react'
import { apiFetch } from '../../../lib/auth'

interface Agent { id: string; handle: string; display_name: string; status: string; created_at: string }
interface Credential { id: string; agent_id: string; name: string; prefix: string; scopes: string; status: string; last_used_at: string | null }

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [credentials, setCredentials] = useState<Credential[]>([])
  const [agentHandle, setAgentHandle] = useState('')
  const [agentName, setAgentName] = useState('')
  const [newSecret, setNewSecret] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadData() }, [])

  async function loadData() {
    try {
      const [a, cr] = await Promise.all([
        apiFetch('/api/agents'),
        apiFetch('/api/credentials'),
      ])
      setAgents(a.agents || [])
      setCredentials(cr || [])
    } catch {}
    setLoading(false)
  }

  const createAgent = async () => {
    if (!agentHandle) return
    await apiFetch('/api/agents', { method: 'POST', body: JSON.stringify({ handle: agentHandle, display_name: agentName || agentHandle }) })
    setAgentHandle(''); setAgentName('')
    loadData()
  }

  const createCred = async (agentId: string) => {
    const cred = await apiFetch('/api/credentials', { method: 'POST', body: JSON.stringify({ agent_id: agentId, name: 'web-key' }) })
    setNewSecret(cred.secret)
    loadData()
  }

  const revokeCred = async (credId: string) => {
    await apiFetch(`/api/credentials/${credId}/revoke`, { method: 'POST', body: '{}' })
    loadData()
  }

  if (loading) return <div className="text-gray-500 text-center py-12">加载中...</div>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">🤖 Agents</h1>

      {/* New Agent */}
      <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 mb-6">
        <h2 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wide">新建 Agent</h2>
        <div className="flex gap-2">
          <input value={agentHandle} onChange={e => setAgentHandle(e.target.value)} placeholder="handle（唯一标识）" className="flex-1 px-3 py-2 rounded bg-gray-800 border border-gray-700 text-sm" />
          <input value={agentName} onChange={e => setAgentName(e.target.value)} placeholder="显示名称" className="flex-1 px-3 py-2 rounded bg-gray-800 border border-gray-700 text-sm" />
          <button onClick={createAgent} className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm font-medium whitespace-nowrap">创建</button>
        </div>
      </div>

      {/* Credential Alert */}
      {newSecret && (
        <div className="mb-4 p-3 bg-yellow-900/30 border border-yellow-700 rounded-xl text-sm break-all">
          <span className="text-yellow-400 font-bold">⚠️ 凭据仅显示一次：</span>
          <code className="block mt-1 bg-gray-950 p-2 rounded text-xs">{newSecret}</code>
          <button onClick={() => { navigator.clipboard?.writeText(newSecret); setNewSecret('') }} className="mt-2 text-blue-400 hover:text-blue-300 text-xs">
            📋 已复制，关闭
          </button>
        </div>
      )}

      {/* Agent List */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">Agent 列表 ({agents.length})</h2>
        </div>
        {agents.map(a => (
          <div key={a.id} className="p-4 border-b border-gray-800 last:border-0">
            <div className="flex items-center justify-between mb-2">
              <div>
                <span className="font-medium text-lg">@{a.handle}</span>
                <span className="text-gray-500 text-sm ml-2">{a.display_name}</span>
                <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${a.status === 'active' ? 'bg-green-900/50 text-green-400' : 'bg-yellow-900/50 text-yellow-400'}`}>{a.status}</span>
              </div>
              <button onClick={() => createCred(a.id)} className="text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded">+ 生成凭据</button>
            </div>
            {/* Credentials for this agent */}
            {credentials.filter(c => c.agent_id === a.id).map(c => (
              <div key={c.id} className="flex items-center justify-between ml-4 py-1 text-sm">
                <div>
                  <span className="font-mono text-gray-400">{c.prefix}...{c.id.slice(-6)}</span>
                  <span className={`ml-2 text-xs ${c.status === 'active' ? 'text-green-400' : 'text-red-400'}`}>{c.status}</span>
                  <span className="text-gray-600 text-xs ml-2">{c.scopes}</span>
                </div>
                {c.status === 'active' && (
                  <button onClick={() => revokeCred(c.id)} className="text-xs px-2 py-1 bg-red-900/50 hover:bg-red-800 rounded text-red-400">撤销</button>
                )}
              </div>
            ))}
          </div>
        ))}
        {agents.length === 0 && (
          <div className="p-8 text-center text-gray-500">还没有 Agent，在上方创建一个</div>
        )}
      </div>
    </div>
  )
}
