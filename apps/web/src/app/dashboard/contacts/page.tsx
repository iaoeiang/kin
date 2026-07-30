'use client'

import { useState, useEffect } from 'react'
import { apiFetch } from '../../../lib/auth'

interface Contact { contact_id: string; user_id: string; handle: string; display_name: string; status: string }
interface UserSearchResult { id: string; email: string; display_name: string; handle: string | null }

export default function ContactsPage() {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [searchQ, setSearchQ] = useState('')
  const [searchResults, setSearchResults] = useState<UserSearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadData() }, [])

  async function loadData() {
    try {
      const co = await apiFetch('/api/contacts')
      setContacts(co || [])
    } catch {}
    setLoading(false)
  }

  async function searchUser() {
    if (!searchQ.trim()) return
    setSearching(true)
    try {
      const r = await apiFetch(`/api/users/search?q=${encodeURIComponent(searchQ)}`)
      setSearchResults(r.users || [])
    } catch {}
    setSearching(false)
  }

  async function addContact(userId: string) {
    try {
      await apiFetch('/api/contacts', { method: 'POST', body: JSON.stringify({ addressee_user_id: userId }) })
      setSearchResults([])
      setSearchQ('')
      loadData()
    } catch {}
  }

  if (loading) return <div className="text-gray-500 text-center py-12">加载中...</div>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">👥 联系人</h1>

      {/* Search Users */}
      <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 mb-6">
        <h2 className="text-sm font-semibold text-gray-400 mb-3 uppercase tracking-wide">搜索用户</h2>
        <div className="flex gap-2">
          <input
            value={searchQ}
            onChange={e => setSearchQ(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && searchUser()}
            placeholder="输入 handle 或名称搜索..."
            className="flex-1 px-3 py-2 rounded bg-gray-800 border border-gray-700 text-sm"
          />
          <button onClick={searchUser} disabled={searching} className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm font-medium disabled:opacity-50">
            {searching ? '...' : '搜索'}
          </button>
        </div>

        {searchResults.length > 0 && (
          <div className="mt-3 space-y-1">
            {searchResults.map(u => (
              <div key={u.id} className="flex items-center justify-between py-2 px-3 bg-gray-800/50 rounded-lg">
                <div>
                  <span className="font-medium">{u.display_name}</span>
                  {u.handle && <span className="text-gray-500 text-sm ml-2">@{u.handle}</span>}
                </div>
                <button onClick={() => addContact(u.id)} className="text-xs px-3 py-1 bg-green-700 hover:bg-green-600 rounded">
                  + 添加联系人
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Contact List */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">联系人列表 ({contacts.length})</h2>
        </div>
        {contacts.map(c => (
          <div key={c.contact_id} className="flex items-center justify-between px-4 py-3 border-b border-gray-800 last:border-0 hover:bg-gray-800/50">
            <div>
              <span className="font-medium">{c.display_name}</span>
              {c.handle && <span className="text-gray-500 text-sm ml-2">@{c.handle}</span>}
            </div>
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              c.status === 'accepted' ? 'bg-green-900/50 text-green-400' :
              c.status === 'pending' ? 'bg-yellow-900/50 text-yellow-400' :
              'bg-gray-800 text-gray-500'
            }`}>{c.status}</span>
          </div>
        ))}
        {contacts.length === 0 && (
          <div className="p-8 text-center text-gray-500">还没有联系人，搜索添加好友吧</div>
        )}
      </div>
    </div>
  )
}
