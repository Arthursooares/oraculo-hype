import { Sparkles } from 'lucide-react'
import type { DashboardTitle } from '../types/dashboard'

type HeaderProps = {
  topTitle: DashboardTitle | undefined
}

export function Header({ topTitle }: HeaderProps) {
  return (
    <header className="hero">
      <div className="hero-copy">
        <span className="eyebrow">Sistema Preditivo de Mercado</span>

        <h1>Oráculo de Hype</h1>

        <p>
          Dashboard de inteligência para acompanhar hype, sentimento e sinais de
          anomalia em jogos, quadrinhos e cultura pop.
        </p>
      </div>

      <aside className="hero-card">
        <Sparkles size={32} />

        <div>
          <span>Título em destaque</span>
          <strong>{topTitle?.name ?? 'Sem dados'}</strong>
          <p>Hype Score: {topTitle?.hype_score ?? 0}</p>
        </div>
      </aside>
    </header>
  )
}