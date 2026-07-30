'use client'

import { useState, useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'

const NAV_ITEMS = [
  { href: '/dashboard', label: '📊 总览', labelEn: 'Overview' },
  { href: '/dashboard/agents', label: '🤖 Agents', labelEn: 'Agents' },
  { href: '/dashboard/contacts', label: '👥 联系人', labelEn: 'Contacts' },
  { href: '/dashboard/chat', label: '💬 消息', labelEn: 'Chat' },
  { href: '/dashboard/settings', label: '⚙️ 设置', labelEn: 'Settings' },
]

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [email, setEmail] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [lang, setLang] = useState<'zh' | 'en'>('zh')

  useEffect(() => {
    const saved = localStorage.getItem('agentnet_auth')
    const savedLang = localStorage.getItem('kin-language') as 'zh' | 'en' | null
    if (savedLang) setLang(savedLang)
    if (!saved) { router.push('/'); return }
    setEmail(JSON.parse(saved).email)
  }, [router])

  const logout = () => {
    localStorage.removeItem('agentnet_auth')
    router.push('/')
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex">
      {/* Sidebar */}
      <aside className={`fixed md:static inset-y-0 left-0 z-50 w-60 bg-gray-900 border-r border-gray-800 transform transition-transform duration-200 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0`}>
        <div className="p-4 border-b border-gray-800">
          <h1 className="text-lg font-bold">⚡ Kin</h1>
          <p className="text-xs text-gray-500 truncate mt-1">{email}</p>
        </div>
        <nav className="p-2 space-y-1">
          {NAV_ITEMS.map(item => {
            const active = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={`block px-3 py-2 rounded-lg text-sm transition-colors ${active ? 'bg-blue-600 text-white' : 'hover:bg-gray-800 text-gray-300'}`}
              >
                {lang === 'zh' && item.label !== '🤖 Agents' ? item.label : item.labelEn}
              </Link>
            )
          })}
        </nav>
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-800">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setLang(lang === 'zh' ? 'en' : 'zh')}
              className="text-xs px-2 py-1 bg-gray-800 rounded hover:bg-gray-700"
            >
              {lang === 'zh' ? 'EN' : '中文'}
            </button>
            <button onClick={logout} className="text-xs text-red-400 hover:text-red-300 px-2 py-1">
              {lang === 'zh' ? '退出' : 'Logout'}
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 md:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="md:hidden flex items-center justify-between p-3 border-b border-gray-800">
          <button onClick={() => setSidebarOpen(true)} className="text-xl">☰</button>
          <span className="text-sm font-medium">Kin</span>
          <button onClick={() => setLang(lang === 'zh' ? 'en' : 'zh')} className="text-xs px-2 py-1 bg-gray-800 rounded">
            {lang === 'zh' ? 'EN' : '中文'}
          </button>
        </div>
        <div className="p-4 md:p-6 max-w-6xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  )
}
