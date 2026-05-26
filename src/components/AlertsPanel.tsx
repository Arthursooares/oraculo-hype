import type { DashboardAlert } from '../types/dashboard'
import {
  formatAlertType,
  formatSeverity,
  translateAlertMessage,
} from '../lib/formatters'

type AlertsPanelProps = {
  alerts: DashboardAlert[]
}

export function AlertsPanel({ alerts }: AlertsPanelProps) {
  return (
    <section className="panel">
      <div className="section-heading compact">
        <div>
          <span className="eyebrow">Radar</span>
          <h2>Anomalias detectadas</h2>
        </div>
      </div>

      <div className="alert-list">
        {alerts.length > 0 ? (
          alerts.map((alert) => (
            <article key={alert.id} className={`alert-card ${alert.severity}`}>
              <div className="alert-card-header">
                <strong>{alert.title_name}</strong>
                <span>{formatSeverity(alert.severity)}</span>
              </div>

              <small>{formatAlertType(alert.alert_type)}</small>

              <p>{translateAlertMessage(alert.message)}</p>
            </article>
          ))
        ) : (
          <p className="empty-state">Nenhum alerta detectado.</p>
        )}
      </div>
    </section>
  )
}