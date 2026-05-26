import { Link } from 'react-router-dom'
import type { DashboardTitle } from '../types/dashboard'
import {
  formatDate,
  formatMediaType,
  formatStatus,
} from '../lib/formatters'

type TitleCardProps = {
  title: DashboardTitle
}

function formatNullableScore(value: number | null | undefined) {
  if (value === null || value === undefined || Number(value) === 0) {
    return '—'
  }

  return Number(value).toFixed(1)
}

function formatDataOrigin(title: DashboardTitle) {
  if (title.data_origin === 'rawg' && title.mention_volume > 0) {
    return 'RAWG API + Steam Reviews'
  }

  if (title.data_origin === 'rawg') {
    return 'RAWG API'
  }

  if (title.data_origin === 'mock') {
    return 'Mock/Teste'
  }

  return title.data_origin
}

function getScoreLabel(title: DashboardTitle) {
  if (title.mention_volume > 0) {
    return 'Hype Score'
  }

  return 'Score de Mercado'
}

export function TitleCard({ title }: TitleCardProps) {
  return (
    <Link to={`/titles/${title.slug}`} className="title-card-link">
      <article className="title-card">
        <div className="cover-wrap">
          {title.cover_url ? (
            <img src={title.cover_url} alt={`Capa de ${title.name}`} />
          ) : (
            <div className="cover-placeholder">Sem capa</div>
          )}
        </div>

        <div className="title-card-content">
          <div className="title-card-top">
            <span>{formatMediaType(title.media_type)}</span>
            <span>{formatStatus(title.status)}</span>
          </div>

          <h3>{title.name}</h3>
          <p>{title.franchise ?? 'Franquia não informada'}</p>

          <div className="score-line">
            <strong>{Number(title.hype_score).toFixed(0)}</strong>
            <span>{getScoreLabel(title)}</span>
          </div>

          <div className="metrics-grid">
            <div>
              <strong>{formatNullableScore(title.sentiment_avg)}</strong>
              <span>Sentimento</span>
            </div>

            <div>
              <strong>{title.mention_volume}</strong>
              <span>Menções</span>
            </div>

            <div>
              <strong>{formatNullableScore(title.user_score_avg)}</strong>
              <span>Usuários</span>
            </div>

            <div>
              <strong>{formatNullableScore(title.rawg_rating)}</strong>
              <span>RAWG</span>
            </div>
          </div>

          <small>Lançamento: {formatDate(title.release_date)}</small>

          <small className="data-origin">
            Origem dos dados: {formatDataOrigin(title)}
          </small>
        </div>
      </article>
    </Link>
  )
}