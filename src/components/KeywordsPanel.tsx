import type { DashboardKeyword } from '../types/dashboard'
import { translateKeyword } from '../lib/formatters'

type KeywordsPanelProps = {
  keywords: DashboardKeyword[]
}

export function KeywordsPanel({ keywords }: KeywordsPanelProps) {
  const translatedKeywords = keywords.map((item) => ({
    ...item,
    translatedKeyword: translateKeyword(item.keyword),
  }))

  const uniqueKeywords = translatedKeywords.filter(
    (item, index, array) =>
      array.findIndex(
        (currentItem) =>
          currentItem.translatedKeyword === item.translatedKeyword,
      ) === index,
  )

  return (
    <section className="panel">
      <div className="section-heading compact">
        <div>
          <span className="eyebrow">Comunidade</span>
          <h2>Palavras-chave</h2>
        </div>
      </div>

      <div className="keyword-cloud">
        {uniqueKeywords.length > 0 ? (
          uniqueKeywords.map((item) => (
            <span key={`${item.slug}-${item.translatedKeyword}`}>
              {item.translatedKeyword}
            </span>
          ))
        ) : (
          <p className="empty-state">Nenhuma palavra-chave encontrada.</p>
        )}
      </div>
    </section>
  )
}