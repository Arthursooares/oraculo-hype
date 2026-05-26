import { Link } from 'react-router-dom'
import type { DashboardSourceCoverage } from '../types/dashboard'

type SourceCoveragePanelProps = {
  coverage: DashboardSourceCoverage[]
}

function formatCompactNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return '—'

  return new Intl.NumberFormat('pt-BR', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value)
}

function formatLastUpdate(date: string | null) {
  if (!date || date.startsWith('1900-01-01')) {
    return 'Sem atualização registrada'
  }

  return new Date(date).toLocaleDateString('pt-BR')
}

function getCoverageClass(status: DashboardSourceCoverage['coverage_status']) {
  if (status === 'Cobertura completa') return 'complete'
  if (status === 'Cobertura parcial') return 'partial'
  if (status === 'Precisa de base textual') return 'text-needed'
  if (status === 'Precisa de sinais públicos') return 'signal-needed'

  return 'insufficient'
}

function SourceCheck({
  active,
  label,
  value,
}: {
  active: boolean
  label: string
  value?: string | number
}) {
  return (
    <span className={active ? 'source-check active' : 'source-check'}>
      <strong>{active ? 'Sim' : 'Não'}</strong>
      <small>{label}</small>
      {value !== undefined && <em>{value}</em>}
    </span>
  )
}

export function SourceCoveragePanel({ coverage }: SourceCoveragePanelProps) {
  const topCoverage = coverage.slice(0, 8)

  const completeCount = coverage.filter(
    (item) => item.coverage_status === 'Cobertura completa',
  ).length

  const partialCount = coverage.filter(
    (item) => item.coverage_status === 'Cobertura parcial',
  ).length

  const needsDataCount = coverage.filter(
    (item) =>
      item.coverage_status !== 'Cobertura completa' &&
      item.coverage_status !== 'Cobertura parcial',
  ).length

  return (
    <section className="panel source-coverage-panel">
      <div className="section-heading compact">
        <div>
          <span className="eyebrow">Integridade</span>
          <h2>Cobertura das fontes</h2>
          <p>
            Mostra quais dados já existem por título e quais integrações ainda
            faltam para reduzir campos vazios no Oráculo.
          </p>
        </div>
      </div>

      <div className="source-coverage-summary">
        <article>
          <strong>{coverage.length}</strong>
          <span>Títulos auditados</span>
        </article>

        <article>
          <strong>{completeCount}</strong>
          <span>Cobertura completa</span>
        </article>

        <article>
          <strong>{partialCount}</strong>
          <span>Cobertura parcial</span>
        </article>

        <article>
          <strong>{needsDataCount}</strong>
          <span>Precisam de dados</span>
        </article>
      </div>

      <div className="source-coverage-list">
        {topCoverage.length > 0 ? (
          topCoverage.map((item) => (
            <Link
              to={`/titles/${item.slug}`}
              key={item.title_id}
              className="source-coverage-card"
            >
              <div className="source-coverage-card-header">
                <div>
                  <h3>{item.title_name}</h3>
                  <p>
                    Última atualização: {formatLastUpdate(item.last_data_at)}
                  </p>
                </div>

                <span
                  className={`coverage-pill ${getCoverageClass(
                    item.coverage_status,
                  )}`}
                >
                  {item.coverage_status}
                </span>
              </div>

              <div className="source-check-grid">
                <SourceCheck active={item.has_rawg} label="RAWG" />

                <SourceCheck
                  active={item.has_steam_appid}
                  label="Steam App ID"
                />

                <SourceCheck
                  active={item.steam_review_count > 0}
                  label="Steam Reviews"
                  value={item.steam_review_count}
                />

                <SourceCheck
                  active={item.youtube_video_count > 0}
                  label="YouTube Vídeos"
                  value={item.youtube_video_count}
                />

                <SourceCheck
                  active={item.youtube_comment_count > 0}
                  label="YouTube Comments"
                  value={item.youtube_comment_count}
                />

                <SourceCheck
                  active={item.total_text_mentions > 0}
                  label="Menções textuais"
                  value={item.total_text_mentions}
                />
              </div>

              <div className="source-signal-row">
                <span>{formatCompactNumber(item.youtube_view_count)} views</span>
                <span>{formatCompactNumber(item.youtube_like_count)} likes</span>
                <span>
                  {formatCompactNumber(item.youtube_comment_signal_count)} comentários
                  em vídeo
                </span>
              </div>

              {item.missing_sources && item.missing_sources.length > 0 && (
                <div className="missing-sources">
                  <strong>Faltando:</strong>
                  {item.missing_sources.slice(0, 5).map((source) => (
                    <span key={source}>{source}</span>
                  ))}
                </div>
              )}
            </Link>
          ))
        ) : (
          <p className="empty-state">
            Ainda não há dados de cobertura das fontes.
          </p>
        )}
      </div>
    </section>
  )
}