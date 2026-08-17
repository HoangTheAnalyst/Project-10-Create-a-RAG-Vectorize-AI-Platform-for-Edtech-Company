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
      className={`relative overflow-hidden rounded-2xl p-5 border transition-all duration-200 bg-white shadow-xs ${
        alert
          ? "border-rose-300 bg-rose-50/50 text-rose-950"
          : "border-[#e2d5bd] hover:border-amber-400 hover:shadow-sm"
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">{title}</span>
        <div className="p-2 rounded-xl bg-[#faf5ec] border border-[#eaddc8] text-slate-700">{icon}</div>
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <div className={`text-2xl font-extrabold tracking-tight ${alert ? "text-rose-600" : "text-slate-900"}`}>
          {value}
        </div>
      </div>
      {subtitle && <p className="mt-1 text-xs text-slate-400 font-medium">{subtitle}</p>}
    </div>
  );
}