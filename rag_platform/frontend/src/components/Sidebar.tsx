"use client";
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  MessageSquareText, 
  GraduationCap, 
  BarChart3, 
  Plus, 
  Trash2, 
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen
} from "lucide-react";
import Image from "next/image";

interface Conversation {
  id: string;
  name: string;
}

interface SidebarProps {
  conversations?: Conversation[];
  activeConvId?: string;
  onSelectConv?: (id: string) => void;
  onNewChat?: () => void;
  onDeleteConv?: (id: string, e: React.MouseEvent) => void;
  collapsed?: boolean;
  onToggleCollapse?: (collapsed: boolean) => void;
}

export default function Sidebar({
  conversations = [],
  activeConvId,
  onSelectConv,
  onNewChat,
  onDeleteConv,
  collapsed: externalCollapsed,
  onToggleCollapse,
}: SidebarProps) {
  const pathname = usePathname();
  const [internalCollapsed, setInternalCollapsed] = useState(false);

  const isCollapsed = externalCollapsed !== undefined ? externalCollapsed : internalCollapsed;

  const handleToggle = () => {
    const nextState = !isCollapsed;
    if (onToggleCollapse) {
      onToggleCollapse(nextState);
    } else {
      setInternalCollapsed(nextState);
    }
  };

  const navItems = [
    { name: "AI Study Tutor", href: "/", icon: MessageSquareText },
    { name: "Exam & Quiz Room", href: "/exam", icon: GraduationCap },
    { name: "Daily Analytics Report", href: "/dashboard", icon: BarChart3 },
  ];

  return (
    <>
      {/* 1. Sidebar Open Button When Sidebar is Collapsed */}
      {isCollapsed && (
        <button
          onClick={handleToggle}
          title="Open Menu"
          className="fixed top-3.5 left-3.5 z-40 p-2.5 rounded-xl bg-white border border-[#ece3d2] text-amber-800 hover:bg-[#faf6ee] hover:border-[#dfd3bc] shadow-md shadow-amber-950/5 transition-colors duration-150"
        >
          <PanelLeftOpen className="w-4 h-4 text-amber-700" />
        </button>
      )}

      {/* 2. Opacity Only Activate In Small Screens */}
      {!isCollapsed && (
        <div
          onClick={handleToggle}
          className="fixed inset-0 bg-slate-900/15 z-40 md:hidden transition-opacity duration-150"
        />
      )}

      {/* 3. Sidebar Frame */}
      <aside 
        className={`bg-[#faf6ee] border-r border-[#ece3d2] flex flex-col h-screen select-none z-50 transition-all duration-180 ease-out overflow-hidden
          fixed inset-y-0 left-0 shadow-xl md:shadow-none
          md:relative md:flex-shrink-0
          ${
            isCollapsed 
              ? "-translate-x-full md:translate-x-0 md:w-0 md:p-0 md:border-r-0 md:opacity-0 pointer-events-none" 
              : "translate-x-0 w-[270px] sm:w-[288px] p-3 opacity-100"
          }
        `}
      >

        <div className="flex items-center justify-between h-12 mb-3 sm:mb-4 px-1 flex-shrink-0">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-white border border-[#ece3d2] shadow-xs flex items-center justify-center p-1 sm:p-1.5 flex-shrink-0">
              <Image src="/LogoHTA.png" alt="Platform Logo" width={32} height={32} className="object-contain" priority />
            </div>
            
            <div className="flex flex-col overflow-hidden whitespace-nowrap">
              <h1 className="font-bold text-slate-800 text-xs sm:text-sm tracking-tight truncate leading-tight">HoangTheAnalyst</h1>
              <p className="text-[10px] text-amber-700 font-semibold truncate leading-tight">AI Academic Platform</p>
            </div>
          </div>

          {/* Sidebar Toggle Button */}
          <button 
            onClick={handleToggle}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-[#f3e9d2] transition-colors duration-100 flex-shrink-0"
            title="Close Sidebar"
          >
            <PanelLeftClose className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="space-y-1 sm:space-y-1.5 mb-3 sm:mb-4 flex-shrink-0">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center px-3.5 py-2.5 rounded-xl text-xs font-bold transition-colors duration-100 ${
                  isActive
                    ? "bg-[#f3e9d2] text-amber-950 border border-[#e5d5b3] shadow-xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-[#f5ede0]"
                }`}
              >
                <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? "text-amber-600" : "text-slate-400"}`} />
                <span className="ml-3 overflow-hidden whitespace-nowrap truncate">
                  {item.name}
                </span>
              </Link>
            );
          })}
        </nav>

        {/* Chat History Section */}
        {pathname === "/" && (
          <div className="flex-1 flex flex-col min-h-0 pt-3 border-t border-[#ece3d2]">
            <div className="flex items-center justify-between px-1 mb-2 h-8 flex-shrink-0">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider overflow-hidden whitespace-nowrap">
                Chat History
              </span>
              <button
                onClick={onNewChat}
                title="New Chat"
                className="flex items-center justify-center px-2.5 py-1.5 rounded-lg gap-1.5 bg-amber-500 hover:bg-amber-600 text-white text-[11px] font-bold transition-all shadow-xs flex-shrink-0"
              >
                <Plus className="w-3.5 h-3.5 flex-shrink-0" /> 
                <span className="truncate">New Chat</span>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-1 pr-0.5">
              {conversations.length === 0 ? (
                <div className="text-[11px] text-slate-400 px-3 py-4 text-center">
                  No conversation threads yet
                </div>
              ) : (
                conversations.map((conv) => (
                  <div
                    key={conv.id}
                    onClick={() => onSelectConv && onSelectConv(conv.id)}
                    className={`group flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium cursor-pointer transition-colors duration-100 ${
                      activeConvId === conv.id
                        ? "bg-[#f3e9d2] text-amber-950 border border-[#e5d5b3] font-bold shadow-xs"
                        : "text-slate-600 hover:bg-[#f5ede0] hover:text-slate-900"
                    }`}
                  >
                    <div className="flex items-center gap-2.5 overflow-hidden">
                      <MessageSquare className={`w-3.5 h-3.5 flex-shrink-0 ${activeConvId === conv.id ? "text-amber-600" : "text-slate-400"}`} />
                      <span className="overflow-hidden whitespace-nowrap truncate max-w-[150px]">
                        {conv.name}
                      </span>
                    </div>
                    {onDeleteConv && (
                      <button
                        onClick={(e) => onDeleteConv(conv.id, e)}
                        className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-rose-600 p-1 transition flex-shrink-0"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </aside>
    </>
  );
}