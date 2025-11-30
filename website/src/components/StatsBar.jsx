import React from 'react';
import { Activity, TrendingUp, Users, Zap } from 'lucide-react';

const StatsBar = ({ stats }) => {
  if (!stats) return null;

  const statItems = [
    {
      label: 'Agents Online',
      value: stats.total_agents,
      icon: Users,
      color: 'text-cyan-400',
    },
    {
      label: 'Healthy',
      value: `${stats.health_percentage?.toFixed(1)}%`,
      icon: Activity,
      color: 'text-green-400',
    },
    {
      label: 'New This Week',
      value: stats.new_agents_this_week,
      icon: TrendingUp,
      color: 'text-blue-400',
    },
    {
      label: 'Avg Response',
      value: `${stats.avg_response_time_ms}ms`,
      icon: Zap,
      color: 'text-yellow-400',
    },
  ];

  return (
    <div className="w-full bg-black border-b border-zinc-800/50">
      <div className="max-w-full mx-auto px-6 py-2">
        <div className="flex items-center justify-between gap-6 text-[10px] font-mono uppercase tracking-wider">
          {statItems.map((item, index) => (
            <div key={index} className="flex items-center gap-2">
              <div className="text-emerald-500/50">
                <item.icon className="w-3.5 h-3.5" />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-zinc-500">
                  {item.label}
                </span>
                <span className={`text-sm font-bold ${item.color}`}>
                  {item.value}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default StatsBar;
