import { useEffect, useState } from 'react'
import { AlertsPanel } from '../components/AlertsPanel'
import { Header } from '../components/Header'
import { HypeChart } from '../components/HypeChart'
import { KeywordsPanel } from '../components/KeywordsPanel'
import { SummaryCards } from '../components/SummaryCards'
import { TitleCard } from '../components/TitleCard'
import { supabase } from '../lib/supabase'
import type {
  DashboardAlert,
  DashboardKeyword,
  DashboardTitle,
} from '../types/dashboard'

export function DashboardPage() {
  const [titles, setTitles] = useState<DashboardTitle[]>([])
  const [alerts, setAlerts] = useState<DashboardAlert[]>([])
  const [keywords, setKeywords] = useState<DashboardKeyword[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchDashboardData() {
      const [titlesResponse, alertsResponse, keywordsResponse] =
        await Promise.all([
          supabase
            .from('dashboard_titles')
            .select('*')
            .order('hype_score', { ascending: false }),

          supabase.from('dashboard_alerts').select('*'),

          supabase.from('dashboard_keywords').select('*'),
        ])

      if (titlesResponse.error) {
        console.error('Erro ao buscar títulos:', titlesResponse.error)
      } else {
        setTitles(titlesResponse.data ?? [])
      }

      if (alertsResponse.error) {
        console.error('Erro ao buscar alertas:', alertsResponse.error)
      } else {
        setAlerts(alertsResponse.data ?? [])
      }

      if (keywordsResponse.error) {
        console.error('Erro ao buscar palavras-chave:', keywordsResponse.error)
      } else {
        setKeywords(keywordsResponse.data ?? [])
      }

      setLoading(false)
    }

    fetchDashboardData()
  }, [])

  const topTitle = titles[0]

  if (loading) {
    return (
      <main className="app-shell">
        <p className="loading">Carregando Oráculo de Hype...</p>
      </main>
    )
  }

  return (
    <main className="app-shell">
      <Header topTitle={topTitle} />

      <SummaryCards titles={titles} alerts={alerts} />

      <HypeChart titles={titles} />

      <section className="insights-grid">
        <AlertsPanel alerts={alerts} />
        <KeywordsPanel keywords={keywords} />
      </section>

      <section className="section-heading">
        <div>
          <span className="eyebrow">Monitoramento</span>
          <h2>Cards de títulos</h2>
        </div>
      </section>

      <section className="titles-grid">
        {titles.map((title) => (
          <TitleCard key={title.id} title={title} />
        ))}
      </section>
    </main>
  )
}