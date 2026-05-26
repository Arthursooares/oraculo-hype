import { Activity, AlertTriangle, BarChart3, Library } from 'lucide-react'
import type { DashboardAlert, DashboardTitle } from '../types/dashboard'

type SummaryCardsProps = {
  titles: DashboardTitle[]
  alerts: DashboardAlert[]
}

export function SummaryCards({ titles, alerts }: SummaryCardsProps) {
  const averageHype = titles.length
    ? Math.round(
        titles.reduce((sum, title) => sum + Number(title.hype_score), 0) /
          titles.length,
      )
    : 0

  const averageSentiment = titles.length
    ? Math.round(
        titles.reduce((sum, title) => sum + Number(title.sentiment_avg), 0) /
          titles.length,
      )
    : 0

  const activeAlerts = alerts.filter((alert) => !alert.resolved).length

  return (
    <section className="summary-grid">
      <article className="summary-card">
        <Library />
        <span>Títulos monitorados</span>
        <strong>{titles.length}</strong>
      </article>

      <article className="summary-card">
        <BarChart3 />
        <span>Hype médio</span>
        <strong>{averageHype}</strong>
      </article>

      <article className="summary-card">
        <Activity />
        <span>Sentimento médio</span>
        <strong>{averageSentiment}</strong>
      </article>

      <article className="summary-card">
        <AlertTriangle />
        <span>Alertas ativos</span>
        <strong>{activeAlerts}</strong>
      </article>
    </section>
  )
}