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
    <aside 
      className={`bg-[#faf6ee] border-r border-[#ece3d2] flex flex-col p-3 h-screen select-none z-20 transition-[width] duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] flex-shrink-0 overflow-hidden ${
        isCollapsed ? "w-[80px]" : "w-[288px]"
      }`}
    >
      {/* Brand Header */}
      <div className="flex items-center flex-nowrap h-12 mb-4 px-1 flex-shrink-0">
        <div className="w-10 h-10 rounded-xl bg-white border border-[#ece3d2] shadow-xs flex items-center justify-center p-1.5 flex-shrink-0">
          <Image src="/LogoHTA.png" alt="Portfolio_Logo" width={34} height={34} className="object-contain" />
        </div>
        
        <div 
          className={`flex flex-col overflow-hidden whitespace-nowrap transition-all duration-300 ${
            isCollapsed ? "w-0 opacity-0 ml-0" : "w-[180px] opacity-100 ml-3"
          }`}
        >
          <h1 className="font-bold text-slate-800 text-sm tracking-tight truncate leading-tight">HoangTheAnalyst</h1>
          <p className="text-[10px] text-amber-700 font-semibold truncate leading-tight">AI Academic Platform</p>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="space-y-1.5 mb-4 flex-shrink-0">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              title={isCollapsed ? item.name : undefined}
              className={`flex items-center flex-nowrap ${
                isCollapsed ? "justify-center px-0 h-10" : "px-3.5 py-2.5"
              } rounded-xl text-xs font-bold transition-colors duration-150 ${
                isActive
                  ? "bg-[#f3e9d2] text-amber-950 border border-[#e5d5b3] shadow-xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-[#f5ede0]"
              }`}
            >
              <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? "text-amber-600" : "text-slate-400"}`} />
              <span 
                className={`overflow-hidden whitespace-nowrap transition-all duration-300 ${
                  isCollapsed ? "w-0 opacity-0 ml-0" : "w-auto opacity-100 ml-3"
                }`}
              >
                {item.name}
              </span>
            </Link>
          );
        })}
      </nav>

      {/* Chat History Section */}
      {pathname === "/" && (
        <div className="flex-1 flex flex-col min-h-0 pt-3 border-t border-[#ece3d2]">
          <div className={`flex items-center flex-nowrap ${isCollapsed ? "justify-center" : "justify-between"} px-1 mb-2 h-8 flex-shrink-0`}>
            <span 
              className={`text-[11px] font-bold text-slate-400 uppercase tracking-wider overflow-hidden whitespace-nowrap transition-all duration-300 ${
                isCollapsed ? "w-0 opacity-0" : "w-[100px] opacity-100"
              }`}
            >
              Chat History
            </span>
            <button
              onClick={onNewChat}
              title="New Chat"
              className={`flex items-center justify-center flex-nowrap ${
                isCollapsed ? "w-9 h-9 rounded-xl p-0" : "px-2.5 py-1.5 rounded-lg gap-1.5"
              } bg-amber-500 hover:bg-amber-600 text-white text-[11px] font-bold transition-all shadow-xs flex-shrink-0`}
            >
              <Plus className="w-3.5 h-3.5 flex-shrink-0" /> 
              <span className={`overflow-hidden whitespace-nowrap transition-all duration-300 ${isCollapsed ? "w-0 opacity-0" : "w-auto opacity-100"}`}>
                New Chat
              </span>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto space-y-1 pr-0.5">
            {conversations.length === 0 ? (
              <div className={`text-[11px] text-slate-400 px-3 py-4 text-center transition-opacity duration-300 ${isCollapsed ? "opacity-0" : "opacity-100"}`}>
                No conversation threads yet
              </div>
            ) : (
              conversations.map((conv) => (
                <div
                  key={conv.id}
                  onClick={() => onSelectConv && onSelectConv(conv.id)}
                  title={isCollapsed ? conv.name : undefined}
                  className={`group flex items-center flex-nowrap ${
                    isCollapsed ? "justify-center px-0 h-10" : "justify-between px-3 py-2"
                  } rounded-xl text-xs font-medium cursor-pointer transition-colors duration-150 ${
                    activeConvId === conv.id
                      ? "bg-[#f3e9d2] text-amber-950 border border-[#e5d5b3] font-bold shadow-xs"
                      : "text-slate-600 hover:bg-[#f5ede0] hover:text-slate-900"
                  }`}
                >
                  <div className={`flex items-center flex-nowrap overflow-hidden ${isCollapsed ? "" : "gap-2.5"}`}>
                    <MessageSquare className={`w-3.5 h-3.5 flex-shrink-0 ${activeConvId === conv.id ? "text-amber-600" : "text-slate-400"}`} />
                    <span className={`overflow-hidden whitespace-nowrap truncate transition-all duration-300 ${isCollapsed ? "w-0 opacity-0" : "w-[150px] opacity-100"}`}>
                      {conv.name}
                    </span>
                  </div>
                  {!isCollapsed && onDeleteConv && (
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

      {/* Collapse Toggle Button */}
      <div className="mt-auto pt-3 border-t border-[#ece3d2] flex-shrink-0">
        <button
          onClick={handleToggle}
          title={isCollapsed ? "Expand" : "Collapse"}
          className={`flex items-center flex-nowrap ${
            isCollapsed ? "justify-center px-0 h-10" : "px-3.5 py-2.5 gap-3"
          } w-full rounded-xl text-xs font-bold text-slate-500 hover:text-amber-800 hover:bg-[#f3e9d2] transition-colors duration-200`}
        >
          {isCollapsed ? <PanelLeftOpen className="w-4 h-4 flex-shrink-0" /> : <PanelLeftClose className="w-4 h-4 flex-shrink-0" />}
          <span className={`overflow-hidden whitespace-nowrap transition-all duration-300 ${isCollapsed ? "w-0 opacity-0" : "w-auto opacity-100"}`}>
            Collapse Menu
          </span>
        </button>
      </div>
    </aside>
  );
}