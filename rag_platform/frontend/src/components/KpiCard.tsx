import { ReactNode } from "react";

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: ReactNode;
  alert?: boolean;
}

export default function KpiCard({ title, value, subtitle, icon, alert }: KpiCardProps) {
  return (
    <div
      className={`relative overflow-hidden rounded-2xl p-3.5 sm:p-5 border transition-all duration-200 bg-white shadow-xs flex flex-col justify-between ${
        alert
          ? "border-rose-300 bg-rose-50/50 text-rose-950"
          : "border-[#e2d5bd] hover:border-amber-400 hover:shadow-sm"
      }`}
    >
      <div className="flex items-center justify-between gap-1.5">
        <span className="text-[10px] sm:text-[11px] font-bold text-slate-500 uppercase tracking-wider truncate" title={title}>
          {title}
        </span>
        <div className="p-1.5 sm:p-2 rounded-xl bg-[#faf5ec] border border-[#eaddc8] text-slate-700 flex-shrink-0">
          {icon}
        </div>
      </div>
      
      <div className="mt-2 sm:mt-3 flex items-baseline gap-2">
        <div className={`text-lg sm:text-2xl font-extrabold tracking-tight truncate ${alert ? "text-rose-600" : "text-slate-900"}`}>
          {value}
        </div>
      </div>
      
      {subtitle && (
        <p className="mt-0.5 sm:mt-1 text-[11px] sm:text-xs text-slate-400 font-medium truncate" title={subtitle}>
          {subtitle}
        </p>
      )}
    </div>
  );
}