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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>总览</h1>
          <p style={{ fontSize: '14px', color: '#6b7280' }}>{email}</p>
        </div>
        <button onClick={wsTest} style={{ fontSize: '12px', padding: '6px 12px', borderRadius: '8px', background: '#1f2937', border: '1px solid #374151', color: '#d1d5db', cursor: 'pointer' }}>
          {ping || '🔌 测试连接'}
        </button>
      </div>

      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
        <div style={{ background: 'linear-gradient(135deg, rgba(30,64,175,0.4), #030712)', borderRadius: '12px', padding: '16px', border: '1px solid rgba(30,64,175,0.3)' }}>
          <div style={{ fontSize: '30px', fontWeight: 'bold' }}>{agentTotal}</div>
          <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px' }}>Agents</div>
          <div style={{ fontSize: '12px', color: '#4ade80', marginTop: '4px' }}>{agentActive} 活跃</div>
        </div>
        <div style={{ background: 'linear-gradient(135deg, rgba(107,33,168,0.4), #030712)', borderRadius: '12px', padding: '16px', border: '1px solid rgba(107,33,168,0.3)' }}>
          <div style={{ fontSize: '30px', fontWeight: 'bold' }}>{contacts.length}</div>
          <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px' }}>联系人</div>
        </div>
        <div style={{ background: 'linear-gradient(135deg, rgba(20,83,45,0.4), #030712)', borderRadius: '12px', padding: '16px', border: '1px solid rgba(20,83,45,0.3)' }}>
          <div style={{ fontSize: '30px', fontWeight: 'bold' }}>{conversations.length}</div>
          <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px' }}>会话</div>
        </div>
        <div style={{ background: 'linear-gradient(135deg, rgba(154,52,18,0.4), #030712)', borderRadius: '12px', padding: '16px', border: '1px solid rgba(154,52,18,0.3)' }}>
          <div style={{ fontSize: '30px', fontWeight: 'bold' }}>{status?.counts?.users || '?'}</div>
          <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px' }}>注册用户</div>
        </div>
      </div>

      {/* Quick actions */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
        <a href="/dashboard/agents" style={{ background: '#111827', borderRadius: '12px', padding: '16px', border: '1px solid #1f2937', textDecoration: 'none', color: '#f3f4f6', display: 'block' }}>
          <div style={{ fontSize: '24px', marginBottom: '8px' }}>🤖</div>
          <div style={{ fontWeight: 500 }}>管理 Agents</div>
          <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>创建、配置、监控你的Agent</div>
        </a>
        <a href="/dashboard/contacts" style={{ background: '#111827', borderRadius: '12px', padding: '16px', border: '1px solid #1f2937', textDecoration: 'none', color: '#f3f4f6', display: 'block' }}>
          <div style={{ fontSize: '24px', marginBottom: '8px' }}>👥</div>
          <div style={{ fontWeight: 500 }}>联系人</div>
          <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>搜索用户、管理联系人列表</div>
        </a>
        <a href="/dashboard/chat" style={{ background: '#111827', borderRadius: '12px', padding: '16px', border: '1px solid #1f2937', textDecoration: 'none', color: '#f3f4f6', display: 'block' }}>
          <div style={{ fontSize: '24px', marginBottom: '8px' }}>💬</div>
          <div style={{ fontWeight: 500 }}>消息</div>
          <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>发送和接收消息</div>
        </a>
      </div>
    </div>
  )
}
