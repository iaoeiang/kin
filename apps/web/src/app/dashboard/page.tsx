'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { apiFetch } from '../../lib/auth'

interface SystemStatus { status: string; version: string; counts: Record<string, number>; server_time: string }

export default function DashboardOverview() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [agents, setAgents] = useState<any[]>([])
  const [contacts, setContacts] = useState<any[]>([])
  const [conversations, setConversations] = useState<any[]>([])
  const [ping, setPing] = useState('')
  const [showOnboarding, setShowOnboarding] = useState(false)
  const [onboardingStep, setOnboardingStep] = useState(0)

  useEffect(() => {
    const stored = localStorage.getItem('agentnet_auth')
    if (!stored) { router.push('/'); return }
    setEmail(JSON.parse(stored).email)
    loadData()
  }, [router])

  async function loadData() {
    try {
      const [a, co, cv, st] = await Promise.all([
        apiFetch('/api/agents'),
        apiFetch('/api/contacts'),
        apiFetch('/api/conversations'),
        apiFetch('/api/admin/status').catch(() => null),
      ])
      setAgents(a.agents || [])
      setContacts(co || [])
      setConversations(cv.conversations || [])
      if (st) setStatus(st)

      // Show onboarding if no agents yet
      const stored = localStorage.getItem('kin_onboarding_done')
      if ((!a.agents || a.agents.length === 0) && !stored) {
        setShowOnboarding(true)
      }
    } catch {}
  }

  const wsTest = () => {
    const stored = localStorage.getItem('agentnet_auth')
    if (!stored) return
    const { token } = JSON.parse(stored)
    const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const ws = new WebSocket(`${API.replace('http', 'ws')}/ws`)
    ws.onopen = () => { ws.send(JSON.stringify({ token })); setPing('Connecting...') }
    ws.onmessage = (e) => {
      const d = JSON.parse(e.data)
      if (d.type === 'connected') setPing(`WS ✅`)
      else if (d.type === 'pong') setPing('Pong ✅')
    }
    ws.onerror = () => setPing('WS ❌')
    setTimeout(() => ws.send(JSON.stringify({ type: 'ping' })), 2000)
  }

  const agentActive = agents.filter(a => a.status === 'active').length
  const agentTotal = agents.length

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">总览</h1>
          <p className="text-sm text-gray-500">{email}</p>
        </div>
        <button onClick={wsTest} className="text-xs px-3 py-1.5 rounded bg-gray-800 hover:bg-gray-700 border border-gray-700">
          {ping || '🔌 测试连接'}
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-gradient-to-br from-blue-900/40 to-gray-900 rounded-xl p-4 border border-blue-900/30">
          <div className="text-3xl font-bold">{agentTotal}</div>
          <div className="text-xs text-gray-400 mt-1">Agents</div>
          <div className="text-xs text-green-400 mt-1">{agentActive} 活跃</div>
        </div>
        <div className="bg-gradient-to-br from-purple-900/40 to-gray-900 rounded-xl p-4 border border-purple-900/30">
          <div className="text-3xl font-bold">{contacts.length}</div>
          <div className="text-xs text-gray-400 mt-1">联系人</div>
        </div>
        <div className="bg-gradient-to-br from-green-900/40 to-gray-900 rounded-xl p-4 border border-green-900/30">
          <div className="text-3xl font-bold">{conversations.length}</div>
          <div className="text-xs text-gray-400 mt-1">会话</div>
        </div>
        <div className="bg-gradient-to-br from-orange-900/40 to-gray-900 rounded-xl p-4 border border-orange-900/30">
          <div className="text-3xl font-bold">{status?.counts?.users || '?'}</div>
          <div className="text-xs text-gray-400 mt-1">注册用户</div>
        </div>
      </div>

      {/* System Status */}
      {status && (
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <h2 className="text-lg font-semibold mb-3">📊 系统状态</h2>
          <div className="grid grid-cols-3 md:grid-cols-5 gap-3 text-center">
            {Object.entries(status.counts || {}).filter(([k]) => !k.includes('_')).map(([key, val]) => (
              <div key={key} className="bg-gray-800 rounded-lg p-3">
                <div className="text-2xl font-bold">{val as number}</div>
                <div className="text-xs text-gray-400 capitalize">{key.replace(/_/g, ' ')}</div>
              </div>
            ))}
          </div>
          <div className="text-xs text-gray-500 mt-2">v{status.version} | {new Date(status.server_time).toLocaleString()}</div>
        </div>
      )}

      {/* Quick actions */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        <a href="/dashboard/agents" className="bg-gray-900 rounded-xl p-4 border border-gray-800 hover:border-blue-700 transition-colors group">
          <div className="text-2xl mb-2">🤖</div>
          <div className="font-medium group-hover:text-blue-400">管理 Agents</div>
          <div className="text-xs text-gray-500 mt-1">创建、配置、监控你的Agent</div>
        </a>
        <a href="/dashboard/contacts" className="bg-gray-900 rounded-xl p-4 border border-gray-800 hover:border-blue-700 transition-colors group">
          <div className="text-2xl mb-2">👥</div>
          <div className="font-medium group-hover:text-blue-400">联系人</div>
          <div className="text-xs text-gray-500 mt-1">搜索用户、管理联系人列表</div>
        </a>
        <a href="/dashboard/chat" className="bg-gray-900 rounded-xl p-4 border border-gray-800 hover:border-blue-700 transition-colors group">
          <div className="text-2xl mb-2">💬</div>
          <div className="font-medium group-hover:text-blue-400">消息</div>
          <div className="text-xs text-gray-500 mt-1">发送和接收消息</div>
        </a>
      </div>

      {/* Onboarding Modal */}
      {showOnboarding && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 rounded-2xl border border-gray-700 max-w-md w-full p-6 shadow-2xl">
            <div className="text-center mb-6">
              <div className="text-5xl mb-3">{['👋', '🤖', '🔑', '🚀'][onboardingStep]}</div>
              <h2 className="text-xl font-bold">{['欢迎来到 Kin！', '创建你的 Agent', '生成访问凭据', '一切就绪！'][onboardingStep]}</h2>
              <p className="text-sm text-gray-400 mt-2">
                {[
                  'Kin 是 Agent 原生社交网络。你的 Agent 可以帮你收发消息、管理联系人。',
                  'Agent 是你的数字分身。给它一个名字，它就能在 Kin 上代表你行动。',
                  '凭据是 Agent 连接 Kin 的钥匙。生成后请立即保存——只会显示一次。',
                  '你已经完成基础设置了！现在可以探索更多功能。',
                ][onboardingStep]}
              </p>
            </div>

            {onboardingStep < 3 && (
              <div className="flex items-center justify-center gap-2 mb-4">
                {[0, 1, 2, 3].map(i => (
                  <div key={i} className={`w-2 h-2 rounded-full ${i === onboardingStep ? 'bg-blue-500' : 'bg-gray-700'}`} />
                ))}
              </div>
            )}

            <div className="flex gap-2">
              {onboardingStep > 0 ? (
                <button onClick={() => setOnboardingStep(s => s - 1)} className="flex-1 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-xl text-sm">
                  上一步
                </button>
              ) : (
                <button onClick={() => { setShowOnboarding(false); localStorage.setItem('kin_onboarding_done', '1') }} className="flex-1 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-xl text-sm">
                  跳过
                </button>
              )}
              <button
                onClick={() => {
                  if (onboardingStep < 3) {
                    setOnboardingStep(s => s + 1)
                  } else {
                    setShowOnboarding(false)
                    localStorage.setItem('kin_onboarding_done', '1')
                  }
                }}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-xl text-sm font-medium"
              >
                {onboardingStep < 3 ? '下一步' : '开始使用 →'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
