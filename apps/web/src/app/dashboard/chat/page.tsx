'use client'

import { useState, useEffect, useRef } from 'react'
import { apiFetch } from '../../../lib/auth'

interface Conversation { id: string; title: string; others: { user_id: string; name: string }[]; created_at: string }

export default function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [chatConv, setChatConv] = useState<string | null>(null)
  const [messages, setMessages] = useState<any[]>([])
  const [msgBody, setMsgBody] = useState('')
  const [loading, setLoading] = useState(true)
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    apiFetch('/api/conversations').then(r => {
      setConversations(r.conversations || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const loadChat = async (convId: string) => {
    setChatConv(convId)
    try {
      const data = await apiFetch(`/api/conversations/${convId}/messages`)
      setMessages(data.messages || [])
    } catch {}
  }

  const sendMsg = async () => {
    if (!chatConv || !msgBody) return
    try {
      await apiFetch('/api/messages', { method: 'POST', body: JSON.stringify({ conversation_id: chatConv, body: msgBody }) })
      setMsgBody('')
      const m = await apiFetch(`/api/conversations/${chatConv}/messages`)
      setMessages(m.messages || [])
    } catch {}
  }

  if (loading) return <div className="text-gray-500 text-center py-12">加载中...</div>

  const currentConv = conversations.find(c => c.id === chatConv)

  return (
    <div className="flex flex-col md:flex-row gap-4 h-[calc(100vh-8rem)]">
      {/* Conversation List */}
      <div className="w-full md:w-72 shrink-0 bg-gray-900 rounded-xl border border-gray-800 overflow-hidden flex flex-col">
        <div className="px-4 py-3 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">会话 ({conversations.length})</h2>
        </div>
        <div className="flex-1 overflow-y-auto">
          {conversations.map(c => (
            <button
              key={c.id}
              onClick={() => loadChat(c.id)}
              className={`block w-full text-left px-4 py-3 border-b border-gray-800 hover:bg-gray-800/50 transition-colors ${chatConv === c.id ? 'bg-blue-900/20 border-l-2 border-l-blue-500' : ''}`}
            >
              <div className="font-medium text-sm truncate">{c.title || '未命名会话'}</div>
              <div className="text-xs text-gray-500 mt-0.5">
                {c.others?.map(o => o.name).join(', ') || '无其他成员'}
              </div>
            </button>
          ))}
          {conversations.length === 0 && (
            <div className="p-4 text-center text-gray-500 text-sm">暂无私信</div>
          )}
        </div>
      </div>

      {/* Chat Panel */}
      <div className="flex-1 bg-gray-900 rounded-xl border border-gray-800 flex flex-col overflow-hidden">
        {chatConv ? (
          <>
            {/* Chat header */}
            <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
              <div>
                <span className="font-medium">{currentConv?.title || '聊天'}</span>
                <span className="text-xs text-gray-500 ml-2">
                  {currentConv?.others?.map(o => o.name).join(', ')}
                </span>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-950/50">
              {messages.map(m => {
                const isYou = m.sender_user_id === JSON.parse(localStorage.getItem('agentnet_auth') || '{}').userId
                return (
                  <div key={m.id} className={`flex ${isYou ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[70%] px-4 py-2 rounded-2xl text-sm ${isYou ? 'bg-blue-600 text-white rounded-br-sm' : 'bg-gray-800 text-gray-100 rounded-bl-sm'}`}>
                      {!isYou && <div className="text-xs text-gray-400 mb-1">{m.sender_user_id.slice(-8)}</div>}
                      <div>{m.body}</div>
                      <div className="text-xs text-gray-400 mt-1 text-right">
                        {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </div>
                  </div>
                )
              })}
              <div ref={chatEndRef} />
            </div>

            {/* Input */}
            <div className="p-4 border-t border-gray-800">
              <div className="flex gap-2">
                <input
                  value={msgBody}
                  onChange={e => setMsgBody(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && sendMsg()}
                  placeholder="输入消息..."
                  className="flex-1 px-4 py-2.5 rounded-xl bg-gray-800 border border-gray-700 focus:border-blue-500 focus:outline-none text-sm"
                />
                <button onClick={sendMsg} className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 rounded-xl text-sm font-medium">
                  发送
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <div className="text-4xl mb-3">💬</div>
              <p>选择一个会话开始聊天</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
