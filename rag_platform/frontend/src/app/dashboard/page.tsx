"use client";
import { useState, useEffect, useMemo, useRef } from "react";
import Sidebar from "@/components/Sidebar";
import KpiCard from "@/components/KpiCard";
import { 
  Activity, 
  Users, 
  Layers, 
  Clock, 
  Target, 
  AlertTriangle, 
  Calendar, 
  BookOpen, 
  ChevronDown, 
  Check, 
  RotateCcw,
  Table as TableIcon
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart, Line, BarChart, Bar, ScatterChart, Scatter,
  XAxis, YAxis, Tooltip, CartesianGrid, Legend
} from "recharts";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export default function DashboardPage() {
  const [isMounted, setIsMounted] = useState(false);
  const [rawData, setRawData] = useState<any>(null);
  const [metadata, setMetadata] = useState<Record<string, string[]>>({});
  const [selectedSubject, setSelectedSubject] = useState<string>("All");
  const [selectedDateRange, setSelectedDateRange] = useState<string>("All");

  const [openSubjectMenu, setOpenSubjectMenu] = useState(false);
  const [openDateMenu, setOpenDateMenu] = useState(false);

  const subjectRef = useRef<HTMLDivElement>(null);
  const dateRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setIsMounted(true);

    const cachedDash = sessionStorage.getItem("cache_dashboard_data");
    if (cachedDash) {
      try {
        setRawData(JSON.parse(cachedDash));
      } catch (e) {
        console.warn("Failed to parse cached dashboard data");
      }
    } else {
      fetch(`${API_BASE}/api/dashboard`)
        .then((res) => (res.ok ? res.json() : null))
        .then((d) => {
          if (d) {
            setRawData(d);
            sessionStorage.setItem("cache_dashboard_data", JSON.stringify(d));
          }
        })
        .catch((err) => console.warn("Failed to fetch dashboard data:", err));
    }

    const cachedMeta = sessionStorage.getItem("cache_metadata");
    if (cachedMeta) {
      try {
        setMetadata(JSON.parse(cachedMeta));
      } catch (e) {
        console.warn("Failed to parse cached metadata");
      }
    } else {
      fetch(`${API_BASE}/api/metadata`)
        .then((res) => (res.ok ? res.json() : {}))
        .then((data) => {
          if (data) {
            setMetadata(data);
            sessionStorage.setItem("cache_metadata", JSON.stringify(data));
          }
        })
        .catch((err) => console.warn("Failed to fetch metadata:", err));
    }
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (subjectRef.current && !subjectRef.current.contains(event.target as Node)) {
        setOpenSubjectMenu(false);
      }
      if (dateRef.current && !dateRef.current.contains(event.target as Node)) {
        setOpenDateMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filteredSubjectDist = useMemo(() => {
    if (!rawData?.subject_distribution) return [];
    if (selectedSubject === "All") return rawData.subject_distribution;
    return rawData.subject_distribution.filter(
      (item: any) => item.selected_subject?.toLowerCase() === selectedSubject.toLowerCase()
    );
  }, [rawData, selectedSubject]);

  const filteredDailyTrends = useMemo(() => {
    if (!rawData?.daily_trends) return [];
    if (selectedDateRange === "All") return rawData.daily_trends;

    const now = new Date();
    return rawData.daily_trends.filter((item: any) => {
      const itemDate = new Date(item.log_date);
      if (selectedDateRange === "yesterday") {
        const yesterday = new Date();
        yesterday.setDate(now.getDate() - 1);
        return itemDate.toDateString() === yesterday.toDateString();
      }
      if (selectedDateRange === "7d") {
        const past7 = new Date();
        past7.setDate(now.getDate() - 7);
        return itemDate >= past7;
      }
      if (selectedDateRange === "30d") {
        const past30 = new Date();
        past30.setDate(now.getDate() - 30);
        return itemDate >= past30;
      }
      return true;
    });
  }, [rawData, selectedDateRange]);

  const filteredScatter = useMemo(() => {
    if (!rawData?.scatter_data) return [];
    if (selectedSubject === "All") return rawData.scatter_data;
    return rawData.scatter_data.filter(
      (item: any) => item.selected_subject?.toLowerCase() === selectedSubject.toLowerCase()
    );
  }, [rawData, selectedSubject]);

  const filteredMartsTable = useMemo(() => {
    if (!rawData?.marts_table_data) return [];
    if (selectedSubject === "All") return rawData.marts_table_data;
    return rawData.marts_table_data.filter(
      (row: any) => row.selected_subject?.toLowerCase() === selectedSubject.toLowerCase()
    );
  }, [rawData, selectedSubject]);

  const { totalQueries, emptyRetrievals, emptyRate } = useMemo(() => {
    if (!rawData?.kpi) return { totalQueries: 0, emptyRetrievals: 0, emptyRate: "0" };
    const tQ = filteredSubjectDist.reduce((acc: number, cur: any) => acc + (cur.total_queries || 0), 0) || rawData.kpi.total_queries;
    const eR = filteredSubjectDist.reduce((acc: number, cur: any) => acc + (cur.empty_retrievals || 0), 0);
    const rate = tQ > 0 ? ((eR / tQ) * 100).toFixed(1) : rawData.kpi.empty_rate;
    return { totalQueries: tQ, emptyRetrievals: eR, emptyRate: rate };
  }, [rawData, filteredSubjectDist]);

  const dateOptions = [
    { label: "All Time", value: "All" },
    { label: "Yesterday", value: "yesterday" },
    { label: "Last 7 Days", value: "7d" },
    { label: "Last 30 Days", value: "30d" },
  ];

  if (!isMounted || !rawData?.kpi) {
    return (
      <div className="flex h-screen w-screen overflow-hidden bg-[#fdfbf7]">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center text-slate-400 text-sm font-medium animate-pulse">
          Loading learning telemetry and performance metrics...
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#fdfbf7]">
      <Sidebar />
      
      <div className="flex-1 overflow-y-auto min-w-0 px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-10 space-y-6 sm:space-y-8">
        <div className="max-w-7xl mx-auto space-y-6 sm:space-y-8">
          
          {/* Header & Slicers Bar */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-slate-900">📊 Daily Analytics Report</h1>
              <p className="text-xs sm:text-sm text-slate-500 mt-1">
                Live monitoring of chat interactions, vector retrieval similarity, and latency metrics.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
              {/* Subject Slicer */}
              <div className="relative flex-1 sm:flex-initial min-w-[150px] sm:min-w-[180px]" ref={subjectRef}>
                <button
                  type="button"
                  onClick={() => {
                    setOpenSubjectMenu(!openSubjectMenu);
                    setOpenDateMenu(false);
                  }}
                  className="w-full flex items-center justify-between gap-2 bg-white border border-[#ece3d2] hover:border-[#dfd3bc] px-3 py-2 sm:px-3.5 sm:py-2 rounded-xl text-xs text-slate-700 shadow-xs transition"
                >
                  <div className="flex items-center gap-2 truncate">
                    <BookOpen className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                    <span className="text-slate-400 font-medium">Subject:</span>
                    <span className="font-bold text-slate-800 truncate">
                      {selectedSubject === "All" ? "All Subjects" : selectedSubject}
                    </span>
                  </div>
                  <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${openSubjectMenu ? "rotate-180 text-amber-600" : ""}`} />
                </button>

                {openSubjectMenu && (
                  <div className="absolute top-full mt-1.5 right-0 w-full bg-white border border-[#ece3d2] rounded-2xl shadow-xl p-1.5 z-30 space-y-0.5 max-h-60 overflow-y-auto">
                    <button
                      onClick={() => {
                        setSelectedSubject("All");
                        setOpenSubjectMenu(false);
                      }}
                      className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-xl transition ${
                        selectedSubject === "All" ? "bg-[#f5ede0] text-amber-950 font-bold" : "text-slate-700 hover:bg-[#fbf7ee]"
                      }`}
                    >
                      <span>All Subjects</span>
                      {selectedSubject === "All" && <Check className="w-3.5 h-3.5 text-amber-600" />}
                    </button>
                    {Object.keys(metadata).map((s) => (
                      <button
                        key={s}
                        onClick={() => {
                          setSelectedSubject(s);
                          setOpenSubjectMenu(false);
                        }}
                        className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-xl transition ${
                          selectedSubject === s ? "bg-[#f5ede0] text-amber-950 font-bold" : "text-slate-700 hover:bg-[#fbf7ee]"
                        }`}
                      >
                        <span className="truncate">{s}</span>
                        {selectedSubject === s && <Check className="w-3.5 h-3.5 text-amber-600" />}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Time Slicer */}
              <div className="relative flex-1 sm:flex-initial min-w-[140px] sm:min-w-[160px]" ref={dateRef}>
                <button
                  type="button"
                  onClick={() => {
                    setOpenDateMenu(!openDateMenu);
                    setOpenSubjectMenu(false);
                  }}
                  className="w-full flex items-center justify-between gap-2 bg-white border border-[#ece3d2] hover:border-[#dfd3bc] px-3 py-2 sm:px-3.5 sm:py-2 rounded-xl text-xs text-slate-700 shadow-xs transition"
                >
                  <div className="flex items-center gap-2 truncate">
                    <Calendar className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                    <span className="text-slate-400 font-medium">Time:</span>
                    <span className="font-bold text-slate-800 truncate">
                      {dateOptions.find((d) => d.value === selectedDateRange)?.label}
                    </span>
                  </div>
                  <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${openDateMenu ? "rotate-180 text-amber-600" : ""}`} />
                </button>

                {openDateMenu && (
                  <div className="absolute top-full mt-1.5 right-0 w-full bg-white border border-[#ece3d2] rounded-2xl shadow-xl p-1.5 z-30 space-y-0.5">
                    {dateOptions.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => {
                          setSelectedDateRange(opt.value);
                          setOpenDateMenu(false);
                        }}
                        className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-xl transition ${
                          selectedDateRange === opt.value ? "bg-[#f5ede0] text-amber-950 font-bold" : "text-slate-700 hover:bg-[#fbf7ee]"
                        }`}
                      >
                        <span>{opt.label}</span>
                        {selectedDateRange === opt.value && <Check className="w-3.5 h-3.5 text-amber-600" />}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {(selectedSubject !== "All" || selectedDateRange !== "All") && (
                <button
                  onClick={() => {
                    setSelectedSubject("All");
                    setSelectedDateRange("All");
                  }}
                  className="p-2 rounded-xl bg-white border border-[#ece3d2] hover:bg-[#faf6ee] text-slate-500 hover:text-amber-700 transition shadow-xs"
                  title="Reset Filters"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 2xl:grid-cols-6 gap-3.5 sm:gap-4">
            <KpiCard title="Total Messages" value={totalQueries} icon={<Activity className="w-4 h-4 text-blue-600" />} />
            <KpiCard title="Total Subs" value={rawData.kpi.unique_users} icon={<Users className="w-4 h-4 text-indigo-600" />} />
            <KpiCard title="Total Sessions" value={rawData.kpi.unique_sessions} icon={<Layers className="w-4 h-4 text-purple-600" />} />
            <KpiCard title="Avg Latency" value={`${rawData.kpi.avg_latency}s`} icon={<Clock className="w-4 h-4 text-amber-600" />} />
            <KpiCard title="Avg Cos Similarity" value={rawData.kpi.avg_similarity} icon={<Target className="w-4 h-4 text-emerald-600" />} />
            <KpiCard
              title="Unanswered Rate"
              value={`${emptyRate}%`}
              subtitle={`${emptyRetrievals || rawData.kpi.empty_count} missed`}
              icon={<AlertTriangle className="w-4 h-4 text-rose-600" />}
              alert={Number(emptyRate) > 5}
            />
          </div>

          {/* 8 Charts Grid: Có debounce={50} giúp chuyển động mượt, không giật lag khi đóng/mở Sidebar */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
            
            {/* Chart 1 */}
            <div className="p-4 sm:p-5 rounded-2xl bg-white border border-[#e2d5bd] h-72 shadow-xs flex flex-col">
              <div className="text-xs font-bold text-slate-700 mb-2">1. Daily Active Learners</div>
              <div className="w-full h-[215px]">
                <ResponsiveContainer width="100%" height="100%" debounce={50}>
                  <LineChart data={filteredDailyTrends}>
                    <CartesianGrid stroke="#f1ede4" vertical={false} />
                    <XAxis dataKey="log_date" stroke="#64748b" tick={{ fontSize: 11, fontWeight: 600 }} />
                    <YAxis stroke="#64748b" tick={{ fontSize: 11, fontWeight: 600 }} allowDecimals={false} />
                    <Tooltip 
                      formatter={(val: any) => [`${val} Learners`, "Active Users"]} 
                      labelFormatter={(label) => `Date: ${label}`}
                      contentStyle={{ backgroundColor: "#ffffff", borderRadius: 10, borderColor: "#e2d5bd", boxShadow: "0 4px 12px rgba(0,0,0,0.06)" }} 
                    />
                    <Line name="Active Learners" type="monotone" dataKey="unique_users" stroke="#0284c7" strokeWidth={2.5} dot={{ r: 4, fill: "#0284c7" }} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 2 */}
            <div className="p-4 sm:p-5 rounded-2xl bg-white border border-[#e2d5bd] h-72 shadow-xs flex flex-col">
              <div className="text-xs font-bold text-slate-700 mb-2">2. Daily Study Sessions</div>
              <div className="w-full h-[215px]">
                <ResponsiveContainer width="100%" height="100%" debounce={50}>
                  <LineChart data={filteredDailyTrends}>
                    <CartesianGrid stroke="#f1ede4" vertical={false} />
                    <XAxis dataKey="log_date" stroke="#64748b" tick={{ fontSize: 11, fontWeight: 600 }} />
                    <YAxis stroke="#64748b" tick={{ fontSize: 11, fontWeight: 600 }} allowDecimals={false} />
                    <Tooltip 
                      formatter={(val: any) => [`${val} Sessions`, "Active Sessions"]} 
                      labelFormatter={(label) => `Date: ${label}`}
                      contentStyle={{ backgroundColor: "#ffffff", borderRadius: 10, borderColor: "#e2d5bd", boxShadow: "0 4px 12px rgba(0,0,0,0.06)" }} 
                    />
                    <Line name="Study Sessions" type="monotone" dataKey="unique_sessions" stroke="#7c3aed" strokeWidth={2.5} dot={{ r: 4, fill: "#7c3aed" }} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 3 */}
            <div className="p-4 sm:p-5 rounded-2xl bg-white border border-[#e2d5bd] h-72 shadow-xs flex flex-col">
              <div className="text-xs font-bold text-slate-700 mb-2">3. Inquiry Volume vs Successful Retrieval</div>
              <div className="w-full h-[215px]">
                <ResponsiveContainer width="100%" height="100%" debounce={50}>
                  <LineChart data={filteredDailyTrends}>
                    <CartesianGrid stroke="#f1ede4" vertical={false} />
                    <XAxis dataKey="log_date" stroke="#64748b" tick={{ fontSize: 11, fontWeight: 600 }} />
                    <YAxis stroke="#64748b" tick={{ fontSize: 11, fontWeight: 600 }} allowDecimals={false} />
                    <Tooltip 
                      formatter={(val: any, name: string) => [
                        `${val} Queries`,
                        name === "total_queries" ? "Total Inquiries" : "Successful Retrieval"
                      ]} 
                      labelFormatter={(label) => `Date: ${label}`}
                      contentStyle={{ backgroundColor: "#ffffff", borderRadius: 10, borderColor: "#e2d5bd", boxShadow: "0 4px 12px rgba(0,0,0,0.06)" }} 
                    />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: 11, paddingTop: 4 }} />
                    <Line name="Total Inquiries" type="monotone" dataKey="total_queries" stroke="#2563eb" strokeWidth={2.5} isAnimationActive={false} />
                    <Line name="Successful Retrieval" type="monotone" dataKey="success_queries" stroke="#059669" strokeDasharray="4 4" strokeWidth={2.5} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 4 */}
            <div className="p-4 sm:p-5 rounded-2xl bg-white border border-[#e2d5bd] h-72 shadow-xs flex flex-col">
              <div className="text-xs font-bold text-slate-700 mb-2">4. Question Distribution by Subject</div>
              <div className="w-full h-[215px]">
                <ResponsiveContainer width="100%" height="100%" debounce={50}>
                  <BarChart data={filteredSubjectDist}>
                    <CartesianGrid stroke="#f1ede4" vertical={false} />
                    <XAxis dataKey="selected_subject" stroke="#64748b" tick={{ fontSize: 11, fontWeight: 600 }} />
                    <YAxis stroke="#64748b" tick={{ fontSize: 11, fontWeight: 600 }} allowDecimals={false} />
                    <Tooltip 
                      formatter={(val: any) => [`${val} Questions`, "Inquiries Count"]} 
                      labelFormatter={(label) => `Subject: ${label}`}
                      contentStyle={{ backgroundColor: "#ffffff", borderRadius: 10, borderColor: "#e2d5bd", boxShadow: "0 4px 12px rgba(0,0,0,0.06)" }} 
                    />
                    <Bar name="Total Questions" dataKey="total_queries" fill="#ea580c" radius={[6, 6, 0, 0]} isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 5 */}
            <div className="p-4 sm:p-5 rounded-2xl bg-white border border-[#e2d5bd] h-72 shadow-xs flex flex-col">
              <div className="text-xs font-bold text-slate-700 mb-2">5. Top Match Similarity vs Similarity Threshold</div>
              <div className="w-full h-[215px]">
                <ResponsiveContainer width="100%" height="100%" debounce={50}>
                  <BarChart data={filteredSubjectDist}>
                    <CartesianGrid stroke="#f1ede4" vertical={false} />
                    <XAxis dataKey="selected_subject" stroke="#64748b" tick={{ fontSize: 11, fontWeight: 600 }} />
                    <YAxis stroke="#64748b" tick={{ fontSize: 11, fontWeight: 600 }} domain={[0, 1]} />
                    <Tooltip 
                      formatter={(val: any, name: string) => [
                        Number(val).toFixed(3),
                        name === "avg_top_similarity" ? "Avg Match Score" : "Threshold"
                      ]} 
                      labelFormatter={(label) => `Subject: ${label}`}
                      contentStyle={{ backgroundColor: "#ffffff", borderRadius: 10, borderColor: "#e2d5bd", boxShadow: "0 4px 12px rgba(0,0,0,0.06)" }} 
                    />
                    <Legend iconType="square" wrapperStyle={{ fontSize: 11, paddingTop: 4 }} />
                    <Bar name="Avg Match Score" dataKey="avg_top_similarity" fill="#4f46e5" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                    <Bar name="Threshold" dataKey="avg_threshold" fill="#cbd5e1" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 6 */}
            <div className="p-4 sm:p-5 rounded-2xl bg-white border border-[#e2d5bd] h-72 shadow-xs flex flex-col">
              <div className="text-xs font-bold text-slate-700 mb-2">6. Similarity Score vs Latency Correlation</div>
              <div className="w-full h-[215px]">
                <ResponsiveContainer width="100%" height="100%" debounce={50}>
                  <ScatterChart>
                    <CartesianGrid stroke="#f1ede4" />
                    <XAxis dataKey="top_similarity_score" name="Similarity Score" stroke="#64748b" tick={{ fontSize: 11, fontWeight: 600 }} domain={[0, 1]} />
                    <YAxis dataKey="latency_seconds" name="Latency (s)" stroke="#64748b" tick={{ fontSize: 11, fontWeight: 600 }} unit="s" />
                    <Tooltip 
                      formatter={(val: any, name: string) => [
                        name === "Similarity Score" ? Number(val).toFixed(3) : `${val}s`,
                        name
                      ]} 
                      contentStyle={{ backgroundColor: "#ffffff", borderRadius: 10, borderColor: "#e2d5bd", boxShadow: "0 4px 12px rgba(0,0,0,0.06)" }} 
                    />
                    <Scatter name="Query Execution" data={filteredScatter} fill="#d97706" isAnimationActive={false} />
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 7 */}
            <div className="p-4 sm:p-5 rounded-2xl bg-white border border-[#e2d5bd] h-72 shadow-xs flex flex-col">
              <div className="text-xs font-bold text-slate-700 mb-2">7. Unretrieved Chunk Count by Subject</div>
              <div className="w-full h-[215px]">
                <ResponsiveContainer width="100%" height="100%" debounce={50}>
                  <BarChart data={filteredSubjectDist}>
                    <CartesianGrid stroke="#f1ede4" vertical={false} />
                    <XAxis dataKey="selected_subject" stroke="#64748b" tick={{ fontSize: 11, fontWeight: 600 }} />
                    <YAxis stroke="#64748b" tick={{ fontSize: 11, fontWeight: 600 }} allowDecimals={false} />
                    <Tooltip 
                      formatter={(val: any) => [`${val} Queries`, "Unretrieved (Below Threshold)"]} 
                      labelFormatter={(label) => `Subject: ${label}`}
                      contentStyle={{ backgroundColor: "#ffffff", borderRadius: 10, borderColor: "#e2d5bd", boxShadow: "0 4px 12px rgba(0,0,0,0.06)" }} 
                    />
                    <Bar name="Missed Retrievals" dataKey="empty_retrievals" fill="#dc2626" radius={[6, 6, 0, 0]} isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Chart 8 */}
            <div className="p-4 sm:p-5 rounded-2xl bg-white border border-[#e2d5bd] h-72 shadow-xs flex flex-col">
              <div className="text-xs font-bold text-slate-700 mb-2">8. Latency Bounds Over Time (Seconds)</div>
              <div className="w-full h-[215px]">
                <ResponsiveContainer width="100%" height="100%" debounce={50}>
                  <LineChart data={filteredDailyTrends}>
                    <CartesianGrid stroke="#f1ede4" vertical={false} />
                    <XAxis dataKey="log_date" stroke="#64748b" tick={{ fontSize: 11, fontWeight: 600 }} />
                    <YAxis stroke="#64748b" tick={{ fontSize: 11, fontWeight: 600 }} unit="s" />
                    <Tooltip 
                      formatter={(val: any, name: string) => [
                        `${val}s`,
                        name === "max_latency" ? "Max Latency" : name === "avg_latency" ? "Avg Latency" : "Min Latency"
                      ]} 
                      labelFormatter={(label) => `Date: ${label}`}
                      contentStyle={{ backgroundColor: "#ffffff", borderRadius: 10, borderColor: "#e2d5bd", boxShadow: "0 4px 12px rgba(0,0,0,0.06)" }} 
                    />
                    <Legend iconType="plainline" wrapperStyle={{ fontSize: 11, paddingTop: 4 }} />
                    <Line name="Max Latency" type="monotone" dataKey="max_latency" stroke="#dc2626" strokeWidth={1.8} dot={false} isAnimationActive={false} />
                    <Line name="Avg Latency" type="monotone" dataKey="avg_latency" stroke="#d97706" strokeWidth={2.5} dot={{ r: 3 }} isAnimationActive={false} />
                    <Line name="Min Latency" type="monotone" dataKey="min_latency" stroke="#16a34a" strokeWidth={1.8} dot={false} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Marts Log Telemetry Records Table */}
          <div className="p-4 sm:p-6 rounded-2xl bg-white border border-[#e2d5bd] shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-[#f5ede0] border border-[#e5d5b3] text-amber-700">
                  <TableIcon className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-800">9. Telemetry Records</h3>
                </div>
              </div>
              <span className="text-xs font-semibold text-slate-400 bg-slate-50 border border-slate-200 px-3 py-1 rounded-lg">
                Totals: {filteredMartsTable.length} Rows
              </span>
            </div>

            <div className="max-h-96 overflow-y-auto overflow-x-auto rounded-xl border border-[#ece3d2]">
              <table className="w-full text-left border-collapse text-[11px] min-w-[700px]">
                <thead className="sticky top-0 z-10 bg-[#faf6ee] shadow-xs">
                  <tr className="text-slate-600 font-bold border-b border-[#ece3d2] uppercase tracking-wider">
                    <th className="py-2.5 px-3">Query SK</th>
                    <th className="py-2.5 px-3">Created At</th>
                    <th className="py-2.5 px-3">Subject</th>
                    <th className="py-2.5 px-3">Lesson</th>
                    <th className="py-2.5 px-3 text-right">Threshold</th>
                    <th className="py-2.5 px-3 text-right">Chunks</th>
                    <th className="py-2.5 px-3 text-right">Match Score</th>
                    <th className="py-2.5 px-3 text-right">Latency (s)</th>
                    <th className="py-2.5 px-3 text-right">Query Len</th>
                    <th className="py-2.5 px-3 text-right">Resp Len</th>
                    <th className="py-2.5 px-3 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#f1ede4] text-slate-700 font-medium">
                  {filteredMartsTable.length === 0 ? (
                    <tr>
                      <td colSpan={11} className="py-8 text-center text-slate-400 font-normal">
                        No telemetry logs matching selected filters.
                      </td>
                    </tr>
                  ) : (
                    filteredMartsTable.map((row: any, idx: number) => (
                      <tr key={idx} className="hover:bg-[#fcf9f2] transition duration-100">
                        <td className="py-2.5 px-3 font-mono text-slate-500 truncate max-w-[100px]" title={row.query_sk}>
                          {row.query_sk?.substring(0, 8)}...
                        </td>
                        <td className="py-2.5 px-3 whitespace-nowrap text-slate-600">
                          {row.created_at}
                        </td>
                        <td className="py-2.5 px-3 font-semibold text-slate-800">
                          {row.selected_subject}
                        </td>
                        <td className="py-2.5 px-3 truncate max-w-[140px]" title={row.selected_lesson}>
                          {row.selected_lesson}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-slate-500">
                          {Number(row.similarity_threshold).toFixed(2)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-bold text-slate-800">
                          {row.chunks_retrieved}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono font-semibold text-indigo-600">
                          {Number(row.top_similarity_score).toFixed(3)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                          {Number(row.latency_seconds).toFixed(2)}s
                        </td>
                        <td className="py-2.5 px-3 text-right text-slate-500">
                          {row.user_query_length}
                        </td>
                        <td className="py-2.5 px-3 text-right text-slate-500">
                          {row.ai_response_length}
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          {row.no_chunks_retrieved ? (
                            <span className="inline-block px-2 py-0.5 rounded-full bg-rose-50 text-rose-600 text-[10px] font-bold border border-rose-200">
                              Missed
                            </span>
                          ) : row.high_latency ? (
                            <span className="inline-block px-2 py-0.5 rounded-full bg-amber-50 text-amber-600 text-[10px] font-bold border border-amber-200">
                              Slow
                            </span>
                          ) : (
                            <span className="inline-block px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-600 text-[10px] font-bold border border-emerald-200">
                              Success
                            </span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}