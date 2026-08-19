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
      className={`relative overflow-hidden rounded-2xl p-4 sm:p-4.5 border transition-all duration-200 bg-white shadow-xs flex flex-col justify-between min-h-[115px] ${
        alert
          ? "border-rose-300 bg-rose-50/40 text-rose-950"
          : "border-[#e2d5bd] hover:border-amber-400 hover:shadow-sm"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-[11px] font-bold text-slate-500 uppercase tracking-tight leading-snug break-words flex-1">
          {title}
        </span>
        <div className="p-1.5 rounded-xl bg-[#faf5ec] border border-[#eaddc8] text-slate-700 flex-shrink-0 mt-0.5">
          {icon}
        </div>
      </div>

      <div className="mt-2">
        <div className={`text-xl sm:text-2xl font-extrabold tracking-tight ${alert ? "text-rose-600" : "text-slate-900"}`}>
          {value}
        </div>
        {subtitle && (
          <p className="mt-0.5 text-[11px] text-slate-400 font-medium truncate">
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
}