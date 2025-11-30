import React from 'react';
import { Activity, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';

const HealthBadge = ({ uptime, avgResponseTime, lastCheck, size = 'md' }) => {
  if (uptime === null || uptime === undefined) {
    return null;
  }

  const getHealthStatus = (uptime) => {
    if (uptime >= 95) return 'healthy';
    if (uptime >= 80) return 'degraded';
    return 'down';
  };

  const status = getHealthStatus(uptime);

  const statusConfig = {
    healthy: {
      color: 'text-green-400',
      bg: 'bg-green-500/10',
      border: 'border-green-500/20',
      icon: CheckCircle2,
      label: 'Healthy',
    },
    degraded: {
      color: 'text-yellow-400',
      bg: 'bg-yellow-500/10',
      border: 'border-yellow-500/20',
      icon: AlertTriangle,
      label: 'Degraded',
    },
    down: {
      color: 'text-red-400',
      bg: 'bg-red-500/10',
      border: 'border-red-500/20',
      icon: XCircle,
      label: 'Down',
    },
  };

  const config = statusConfig[status];
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-1',
    lg: 'text-base px-3 py-1.5',
  };

  return (
    <div
      className={`inline-flex items-center gap-1.5 rounded-md border ${config.bg} ${config.border} ${config.color} ${sizeClasses[size]} font-mono`}
      title={`Uptime: ${uptime.toFixed(1)}%${avgResponseTime ? ` | Avg response: ${avgResponseTime}ms` : ''}`}
    >
      <Icon className="w-3.5 h-3.5" />
      <span>{uptime.toFixed(1)}% uptime</span>
      {avgResponseTime && (
        <>
          <span className="opacity-30">|</span>
          <Activity className="w-3 h-3 opacity-50" />
          <span className="opacity-80">{avgResponseTime}ms</span>
        </>
      )}
    </div>
  );
};

export default HealthBadge;
