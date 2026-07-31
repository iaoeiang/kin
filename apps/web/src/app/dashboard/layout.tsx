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
    <div style={{ minHeight: '100vh', background: '#030712', color: '#f3f4f6', display: 'flex' }}>
      {/* Sidebar */}
      <aside style={{ width: '240px', minWidth: '240px', background: '#111827', borderRight: '1px solid #1f2937', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '16px', borderBottom: '1px solid #1f2937' }}>
          <div style={{ fontSize: '18px', fontWeight: 'bold' }}>⚡ Kin</div>
          <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{email}</div>
        </div>
        <nav style={{ padding: '8px' }}>
          {NAV_ITEMS.map(item => {
            const active = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                style={{
                  display: 'block',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  fontSize: '14px',
                  textDecoration: 'none',
                  background: active ? '#2563eb' : 'transparent',
                  color: active ? '#fff' : '#d1d5db',
                }}
              >
                {lang === 'zh' && item.label !== '🤖 Agents' ? item.label : item.labelEn}
              </Link>
            )
          })}
        </nav>
        <div style={{ marginTop: 'auto', padding: '16px', borderTop: '1px solid #1f2937' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <button onClick={() => setLang(lang === 'zh' ? 'en' : 'zh')} style={{ fontSize: '12px', padding: '4px 8px', background: '#1f2937', borderRadius: '4px', border: 'none', color: '#d1d5db', cursor: 'pointer' }}>
              {lang === 'zh' ? 'EN' : '中文'}
            </button>
            <button onClick={logout} style={{ fontSize: '12px', color: '#f87171', padding: '4px 8px', border: 'none', background: 'transparent', cursor: 'pointer' }}>
              {lang === 'zh' ? '退出' : 'Logout'}
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main style={{ flex: 1, overflow: 'auto', padding: '24px', maxWidth: '1200px' }}>
        {children}
      </main>
    </div>
  )
}
