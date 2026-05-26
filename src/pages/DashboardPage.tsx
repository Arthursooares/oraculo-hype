import { useEffect, useMemo, useState } from 'react'
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

type DashboardFilter =
  | 'all'
  | 'withSteam'
  | 'withoutSteam'
  | 'highestHype'
  | 'highestMentions'
  | 'lowestSentiment'
  | 'upcoming'
  | 'released'

const FILTERS: { label: string; value: DashboardFilter }[] = [
  {
    label: 'Todos',
    value: 'all',
  },
  {
    label: 'Com reviews Steam',
    value: 'withSteam',
  },
  {
    label: 'Sem reviews Steam',
    value: 'withoutSteam',
  },
  {
    label: 'Maior hype',
    value: 'highestHype',
  },
  {
    label: 'Mais menções',
    value: 'highestMentions',
  },
  {
    label: 'Pior sentimento',
    value: 'lowestSentiment',
  },
  {
    label: 'Próximos lançamentos',
    value: 'upcoming',
  },
  {
    label: 'Já lançados',
    value: 'released',
  },
]

function isUpcomingTitle(title: DashboardTitle) {
  if (!title.release_date) return false

  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const releaseDate = new Date(title.release_date)
  releaseDate.setHours(0, 0, 0, 0)

  return releaseDate > today
}

function isReleasedTitle(title: DashboardTitle) {
  if (!title.release_date) return false

  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const releaseDate = new Date(title.release_date)
  releaseDate.setHours(0, 0, 0, 0)

  return releaseDate <= today
}

function getFilteredAndSortedTitles(
  titles: DashboardTitle[],
  selectedFilter: DashboardFilter,
) {
  const titlesCopy = [...titles]

  if (selectedFilter === 'withSteam') {
    return titlesCopy
      .filter((title) => title.mention_volume > 0)
      .sort((a, b) => b.hype_score - a.hype_score)
  }

  if (selectedFilter === 'withoutSteam') {
    return titlesCopy
      .filter((title) => title.mention_volume === 0)
      .sort((a, b) => b.hype_score - a.hype_score)
  }

  if (selectedFilter === 'highestHype') {
    return titlesCopy.sort((a, b) => b.hype_score - a.hype_score)
  }

  if (selectedFilter === 'highestMentions') {
    return titlesCopy.sort((a, b) => b.mention_volume - a.mention_volume)
  }

  if (selectedFilter === 'lowestSentiment') {
    return titlesCopy
      .filter((title) => title.mention_volume > 0)
      .sort((a, b) => a.sentiment_avg - b.sentiment_avg)
  }

  if (selectedFilter === 'upcoming') {
    return titlesCopy
      .filter(isUpcomingTitle)
      .sort((a, b) => {
        const dateA = a.release_date ? new Date(a.release_date).getTime() : 0
        const dateB = b.release_date ? new Date(b.release_date).getTime() : 0

        return dateA - dateB
      })
  }

  if (selectedFilter === 'released') {
    return titlesCopy
      .filter(isReleasedTitle)
      .sort((a, b) => b.hype_score - a.hype_score)
  }

  return titlesCopy.sort((a, b) => b.hype_score - a.hype_score)
}

function getFilterDescription(selectedFilter: DashboardFilter) {
  const descriptions: Record<DashboardFilter, string> = {
    all: 'Mostrando todos os títulos monitorados pelo Oráculo.',
    withSteam: 'Mostrando apenas títulos com reviews reais da Steam analisadas.',
    withoutSteam:
      'Mostrando títulos que ainda dependem de dados de mercado, sem reviews Steam salvas.',
    highestHype: 'Ordenando os títulos pelo maior Hype Score.',
    highestMentions: 'Ordenando os títulos pelo maior volume de menções analisadas.',
    lowestSentiment:
      'Mostrando títulos com reviews Steam e sentimento médio mais baixo.',
    upcoming: 'Mostrando jogos com lançamento futuro.',
    released: 'Mostrando jogos já lançados.',
  }

  return descriptions[selectedFilter]
}

export function DashboardPage() {
  const [titles, setTitles] = useState<DashboardTitle[]>([])
  const [alerts, setAlerts] = useState<DashboardAlert[]>([])
  const [keywords, setKeywords] = useState<DashboardKeyword[]>([])
  const [selectedFilter, setSelectedFilter] = useState<DashboardFilter>('all')
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

  const filteredTitles = useMemo(() => {
    return getFilteredAndSortedTitles(titles, selectedFilter)
  }, [titles, selectedFilter])

  const topTitle = titles[0]

  const titlesWithSteam = useMemo(() => {
    return titles.filter((title) => title.mention_volume > 0).length
  }, [titles])

  const titlesWithoutSteam = useMemo(() => {
    return titles.filter((title) => title.mention_volume === 0).length
  }, [titles])

  const upcomingTitles = useMemo(() => {
    return titles.filter(isUpcomingTitle).length
  }, [titles])

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

      <HypeChart titles={filteredTitles} />

      <section className="insights-grid">
        <AlertsPanel alerts={alerts} />
        <KeywordsPanel keywords={keywords} />
      </section>

      <section className="dashboard-controls panel">
        <div className="dashboard-controls-header">
          <div>
            <span className="eyebrow">Filtros</span>
            <h2>Explorar títulos monitorados</h2>
            <p>{getFilterDescription(selectedFilter)}</p>
          </div>

          <div className="dashboard-controls-stats">
            <span>{titles.length} títulos</span>
            <span>{titlesWithSteam} com Steam</span>
            <span>{titlesWithoutSteam} sem Steam</span>
            <span>{upcomingTitles} futuros</span>
          </div>
        </div>

        <div className="filter-pills">
          {FILTERS.map((filter) => (
            <button
              key={filter.value}
              type="button"
              className={
                selectedFilter === filter.value
                  ? 'filter-pill active'
                  : 'filter-pill'
              }
              onClick={() => setSelectedFilter(filter.value)}
            >
              {filter.label}
            </button>
          ))}
        </div>
      </section>

      <section className="section-heading">
        <div>
          <span className="eyebrow">Monitoramento</span>
          <h2>Cards de títulos</h2>
          <p>
            Exibindo {filteredTitles.length} de {titles.length} títulos.
          </p>
        </div>
      </section>

      {filteredTitles.length > 0 ? (
        <section className="titles-grid">
          {filteredTitles.map((title) => (
            <TitleCard key={title.id} title={title} />
          ))}
        </section>
      ) : (
        <section className="panel">
          <p className="empty-state">
            Nenhum título encontrado para este filtro.
          </p>
        </section>
      )}
    </main>
  )
}