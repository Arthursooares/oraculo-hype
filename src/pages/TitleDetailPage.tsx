import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, ExternalLink, Play } from 'lucide-react'
import { supabase } from '../lib/supabase'
import {
  formatDate,
  formatMediaType,
  formatStatus,
} from '../lib/formatters'
import type {
  DashboardRecentMention,
  DashboardTitle,
  DashboardYoutubeMetric,
} from '../types/dashboard'

function formatNullableScore(value: number | null | undefined) {
  if (value === null || value === undefined || Number(value) === 0) {
    return '—'
  }

  return Number(value).toFixed(1)
}

function formatCompactNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return '—'

  return new Intl.NumberFormat('pt-BR', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value)
}

function formatSentimentLabel(label: string | null) {
  if (label === 'positive') return 'Positiva'
  if (label === 'negative') return 'Negativa'
  if (label === 'neutral') return 'Neutra'

  return 'Sem classificação'
}

function getSentimentClass(label: string | null) {
  if (label === 'positive') return 'positive'
  if (label === 'negative') return 'negative'
  if (label === 'neutral') return 'neutral'

  return 'unknown'
}

function cleanReviewContent(content: string) {
  return content
    .replace('[STEAM_POSITIVE]', '')
    .replace('[STEAM_NEGATIVE]', '')
    .replace(/Steam App ID:.*$/s, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function formatReviewDate(date: string | null) {
  if (!date) return 'Data não informada'

  return new Date(date).toLocaleDateString('pt-BR')
}

function getYoutubeHypeLabel(video: DashboardYoutubeMetric) {
  const views = Number(video.view_count ?? 0)
  const likes = Number(video.like_count ?? 0)
  const comments = Number(video.comment_count ?? 0)

  if (views >= 10_000_000 || likes >= 300_000 || comments >= 50_000) {
    return 'Hype muito alto'
  }

  if (views >= 1_000_000 || likes >= 80_000 || comments >= 10_000) {
    return 'Hype alto'
  }

  if (views >= 250_000 || likes >= 10_000 || comments >= 2_000) {
    return 'Hype moderado'
  }

  return 'Sinal inicial'
}

export function TitleDetailPage() {
  const { slug } = useParams()

  const [title, setTitle] = useState<DashboardTitle | null>(null)
  const [reviews, setReviews] = useState<DashboardRecentMention[]>([])
  const [youtubeVideos, setYoutubeVideos] = useState<DashboardYoutubeMetric[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchTitleDetails() {
      if (!slug) {
        setLoading(false)
        return
      }

      const [titleResponse, reviewsResponse, youtubeResponse] = await Promise.all([
        supabase
          .from('dashboard_titles')
          .select('*')
          .eq('slug', slug)
          .single(),

        supabase
          .from('dashboard_recent_mentions')
          .select('*')
          .eq('slug', slug)
          .order('published_at', { ascending: false })
          .limit(30),

        supabase
          .from('dashboard_youtube_metrics')
          .select('*')
          .eq('slug', slug)
          .order('view_count', { ascending: false })
          .limit(6),
      ])

      if (titleResponse.error) {
        console.error('Erro ao buscar detalhes do título:', titleResponse.error)
      } else {
        setTitle(titleResponse.data)
      }

      if (reviewsResponse.error) {
        console.error('Erro ao buscar reviews:', reviewsResponse.error)
      } else {
        setReviews(reviewsResponse.data ?? [])
      }

      if (youtubeResponse.error) {
        console.error('Erro ao buscar vídeos do YouTube:', youtubeResponse.error)
      } else {
        setYoutubeVideos(youtubeResponse.data ?? [])
      }

      setLoading(false)
    }

    fetchTitleDetails()
  }, [slug])

  const positiveReviews = useMemo(
    () => reviews.filter((review) => review.sentiment_label === 'positive'),
    [reviews],
  )

  const negativeReviews = useMemo(
    () => reviews.filter((review) => review.sentiment_label === 'negative'),
    [reviews],
  )

  const topKeywords = useMemo(() => {
    const keywordMap = new Map<string, number>()

    reviews.forEach((review) => {
      review.keywords?.forEach((keyword) => {
        keywordMap.set(keyword, (keywordMap.get(keyword) ?? 0) + 1)
      })
    })

    return Array.from(keywordMap.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12)
  }, [reviews])

  const youtubeTotals = useMemo(() => {
    return youtubeVideos.reduce(
      (acc, video) => {
        acc.views += Number(video.view_count ?? 0)
        acc.likes += Number(video.like_count ?? 0)
        acc.comments += Number(video.comment_count ?? 0)
        return acc
      },
      {
        views: 0,
        likes: 0,
        comments: 0,
      },
    )
  }, [youtubeVideos])

  if (loading) {
    return (
      <main className="app-shell">
        <p className="loading">Carregando detalhes do jogo...</p>
      </main>
    )
  }

  if (!title) {
    return (
      <main className="app-shell">
        <Link to="/" className="back-link">
          <ArrowLeft size={18} />
          Voltar para o dashboard
        </Link>

        <section className="panel">
          <h1>Título não encontrado</h1>
          <p className="empty-state">
            Não encontramos dados para este jogo no dashboard.
          </p>
        </section>
      </main>
    )
  }

  return (
    <main className="app-shell">
      <Link to="/" className="back-link">
        <ArrowLeft size={18} />
        Voltar para o dashboard
      </Link>

      <section className="title-detail-hero">
        <div className="title-detail-cover">
          {title.cover_url ? (
            <img src={title.cover_url} alt={`Capa de ${title.name}`} />
          ) : (
            <div className="cover-placeholder">Sem capa</div>
          )}
        </div>

        <div className="title-detail-info">
          <span className="eyebrow">Detalhes do título</span>

          <h1>{title.name}</h1>

          <p>
            {title.franchise ?? 'Franquia não informada'} ·{' '}
            {formatMediaType(title.media_type)} · {formatStatus(title.status)}
          </p>

          <div className="detail-metrics-grid">
            <article>
              <strong>{Number(title.hype_score).toFixed(0)}</strong>
              <span>{title.mention_volume > 0 ? 'Hype Score' : 'Score de Mercado'}</span>
            </article>

            <article>
              <strong>{formatNullableScore(title.sentiment_avg)}</strong>
              <span>Sentimento</span>
            </article>

            <article>
              <strong>{title.mention_volume}</strong>
              <span>Reviews analisadas</span>
            </article>

            <article>
              <strong>{formatNullableScore(title.user_score_avg)}</strong>
              <span>Usuários</span>
            </article>

            <article>
              <strong>{formatNullableScore(title.rawg_rating)}</strong>
              <span>RAWG</span>
            </article>

            <article>
              <strong>{formatNullableScore(title.rawg_metacritic)}</strong>
              <span>Metacritic</span>
            </article>
          </div>

          <div className="detail-meta">
            <span>Lançamento: {formatDate(title.release_date)}</span>
            <span>
              Steam App ID: {title.steam_appid ? title.steam_appid : 'Não encontrado'}
            </span>
            <span>
              Última sincronização:{' '}
              {title.last_synced_at
                ? new Date(title.last_synced_at).toLocaleDateString('pt-BR')
                : 'Não informada'}
            </span>
          </div>
        </div>
      </section>

      <section className="detail-grid">
        <div className="panel">
          <div className="section-heading compact">
            <div>
              <span className="eyebrow">Comunidade</span>
              <h2>Resumo das reviews</h2>
            </div>
          </div>

          <div className="review-summary-grid">
            <article>
              <strong>{reviews.length}</strong>
              <span>Total analisado</span>
            </article>

            <article>
              <strong>{positiveReviews.length}</strong>
              <span>Positivas</span>
            </article>

            <article>
              <strong>{negativeReviews.length}</strong>
              <span>Negativas</span>
            </article>
          </div>
        </div>

        <div className="panel">
          <div className="section-heading compact">
            <div>
              <span className="eyebrow">Temas</span>
              <h2>Palavras-chave</h2>
            </div>
          </div>

          <div className="keyword-cloud">
            {topKeywords.length > 0 ? (
              topKeywords.map(([keyword, frequency]) => (
                <span key={keyword}>
                  {keyword} · {frequency}
                </span>
              ))
            ) : (
              <p className="empty-state">
                Ainda não há palavras-chave para este título.
              </p>
            )}
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="section-heading compact">
          <div>
            <span className="eyebrow">Trailer Hype</span>
            <h2>Trailers e sinais de hype no YouTube</h2>
            <p>
              Métricas coletadas a partir de vídeos públicos relacionados ao jogo.
            </p>
          </div>
        </div>

        {youtubeVideos.length > 0 ? (
          <>
            <div className="youtube-summary-grid">
              <article>
                <strong>{youtubeVideos.length}</strong>
                <span>Vídeos monitorados</span>
              </article>

              <article>
                <strong>{formatCompactNumber(youtubeTotals.views)}</strong>
                <span>Views somadas</span>
              </article>

              <article>
                <strong>{formatCompactNumber(youtubeTotals.likes)}</strong>
                <span>Likes somados</span>
              </article>

              <article>
                <strong>{formatCompactNumber(youtubeTotals.comments)}</strong>
                <span>Comentários</span>
              </article>
            </div>

            <div className="youtube-video-grid">
              {youtubeVideos.map((video) => (
                <article key={video.id} className="youtube-video-card">
                  <div className="youtube-thumbnail">
                    {video.thumbnail_url ? (
                      <img src={video.thumbnail_url} alt={video.video_title} />
                    ) : (
                      <div className="cover-placeholder">Sem thumbnail</div>
                    )}

                    <span>
                      <Play size={15} />
                      {getYoutubeHypeLabel(video)}
                    </span>
                  </div>

                  <div className="youtube-video-content">
                    <h3>{video.video_title}</h3>

                    <p>{video.channel_title ?? 'Canal não informado'}</p>

                    <div className="youtube-video-stats">
                      <span>{formatCompactNumber(video.view_count)} views</span>
                      <span>{formatCompactNumber(video.like_count)} likes</span>
                      <span>{formatCompactNumber(video.comment_count)} comentários</span>
                    </div>

                    <small>
                      Publicado em: {formatReviewDate(video.published_at)}
                    </small>

                    {video.url && (
                      <a href={video.url} target="_blank" rel="noreferrer">
                        Abrir no YouTube
                        <ExternalLink size={14} />
                      </a>
                    )}
                  </div>
                </article>
              ))}
            </div>
          </>
        ) : (
          <p className="empty-state">
            Ainda não há vídeos do YouTube salvos para este título.
          </p>
        )}
      </section>

      <section className="panel">
        <div className="section-heading compact">
          <div>
            <span className="eyebrow">Evidências</span>
            <h2>Reviews recentes da Steam</h2>
          </div>
        </div>

        <div className="reviews-list">
          {reviews.length > 0 ? (
            reviews.map((review) => (
              <article key={review.id} className="review-card">
                <div className="review-card-header">
                  <span className={`sentiment-pill ${getSentimentClass(review.sentiment_label)}`}>
                    {formatSentimentLabel(review.sentiment_label)}
                  </span>

                  <span>{formatReviewDate(review.published_at)}</span>
                </div>

                <p>{cleanReviewContent(review.content)}</p>

                {review.summary && <small>{review.summary}</small>}

                <div className="review-card-footer">
                  <span>Votos úteis: {review.upvotes}</span>

                  {review.url && (
                    <a href={review.url} target="_blank" rel="noreferrer">
                      Abrir na Steam
                      <ExternalLink size={14} />
                    </a>
                  )}
                </div>
              </article>
            ))
          ) : (
            <p className="empty-state">
              Ainda não há reviews da Steam salvas para este título.
            </p>
          )}
        </div>
      </section>
    </main>
  )
}