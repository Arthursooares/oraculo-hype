export type DashboardTitle = {
  id: string
  name: string
  slug: string
  media_type: 'game' | 'comic'
  franchise: string | null
  release_date: string | null
  cover_url: string | null
  status: string
  rawg_id: number | null
  rawg_rating: number | null
  rawg_rating_top: number | null
  rawg_metacritic: number | null
  steam_appid: number | null
  data_origin: string
  last_synced_at: string | null
  hype_score: number
  sentiment_avg: number
  mention_volume: number
  critic_score_avg: number
  user_score_avg: number
  calculated_for: string | null
}

export type DashboardAlert = {
  id: string
  title_name: string
  slug: string
  alert_type:
    | 'review_bombing'
    | 'hype_surge'
    | 'sentiment_drop'
    | 'high_controversy'
  severity: 'low' | 'medium' | 'high'
  message: string
  detected_at: string
  resolved: boolean
}

export type DashboardKeyword = {
  title_name: string
  slug: string
  keyword: string
  frequency: number
}

export type DashboardHypeHistory = {
  id: string
  title_id: string
  title_name: string
  slug: string
  media_type: 'game' | 'comic'
  hype_score: number
  sentiment_avg: number | null
  mention_volume: number
  critic_score_avg: number | null
  user_score_avg: number | null
  calculated_for: string
}

export type DashboardRecentMention = {
  id: string
  title_id: string
  title_name: string
  slug: string
  source_name: string
  author: string | null
  content: string
  url: string | null
  upvotes: number
  published_at: string | null
  sentiment_score: number | null
  sentiment_label: 'negative' | 'neutral' | 'positive' | null
  summary: string | null
  keywords: string[] | null
}

export type DashboardYoutubeMetric = {
  id: string
  title_id: string
  title_name: string
  slug: string
  youtube_video_id: string
  video_title: string
  channel_title: string | null
  published_at: string | null
  url: string | null
  thumbnail_url: string | null
  view_count: number
  like_count: number
  comment_count: number
  collected_at: string | null
}