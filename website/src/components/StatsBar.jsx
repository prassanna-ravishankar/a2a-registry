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
    <div className="w-full bg-black/30 border-b border-cyan-500/20 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-6 py-3">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {statItems.map((item, index) => (
            <div key={index} className="flex items-center gap-3">
              <div className={`${item.color} opacity-50`}>
                <item.icon className="w-5 h-5" />
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-gray-400 font-mono uppercase tracking-wide">
                  {item.label}
                </span>
                <span className={`text-lg font-bold font-mono ${item.color}`}>
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
