import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { DashboardTitle } from '../types/dashboard'

type HypeChartProps = {
  titles: DashboardTitle[]
}

export function HypeChart({ titles }: HypeChartProps) {
  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Ranking</span>
          <h2>Hype Score por título</h2>
        </div>
      </div>

      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={titles}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.18} />
            <XAxis
              dataKey="name"
              tick={{ fill: '#cbd5e1', fontSize: 12 }}
              interval={0}
              angle={-8}
              textAnchor="end"
              height={70}
            />
            <YAxis
              tick={{ fill: '#cbd5e1', fontSize: 12 }}
              domain={[0, 100]}
            />
            <Tooltip
              cursor={{ fill: 'rgba(148, 163, 184, 0.08)' }}
              contentStyle={{
                background: '#020617',
                border: '1px solid #334155',
                borderRadius: 12,
                color: '#f8fafc',
              }}
              labelStyle={{
                color: '#f8fafc',
              }}
            />
            <Bar
              dataKey="hype_score"
              name="Hype Score"
              radius={[10, 10, 0, 0]}
              fill="#22d3ee"
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}