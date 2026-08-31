import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { getRoadColor } from '../../utils/roadColor';

interface ConditionHistoryProps {
  history: { date: string; score: number }[];
}

export function ConditionHistory({ history }: ConditionHistoryProps) {
  if (!history.length) {
    return <p className="history-empty">No historical data available.</p>;
  }

  return (
    <div className="history-chart-container">
      <h4 className="history-chart-title">Condition Trend (5-day)</h4>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={history} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
          <XAxis
            dataKey="date"
            tickFormatter={(v: string) => v.slice(5)} // "08-26"
            tick={{ fill: '#94a3b8', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: '#94a3b8', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: 6,
              fontSize: 12,
              color: '#f1f5f9',
            }}
            labelFormatter={(l) => `Date: ${l}`}
            formatter={(value) => [`${value}/100`, 'Score']}
          />
          <Bar dataKey="score" radius={[3, 3, 0, 0]}>
            {history.map((entry, i) => (
              <Cell key={i} fill={getRoadColor(entry.score)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
