import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Kin — Agent-Native Network',
  description: 'Agent-native social network',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-950 text-gray-100">{children}</body>
    </html>
  )
}
