import React from 'react';
import { NavLink } from 'react-router-dom';
import { navigationGroups } from './navigation';
import { useBusiness } from '@/context/BusinessContext';
import {
  LayoutDashboard,
  ShoppingCart,
  MonitorDot,
  RotateCcw,
  Receipt,
  Users,
  ShoppingBag,
  PackageCheck,
  Undo2,
  CreditCard,
  Truck,
  BookOpen,
  Package,
  Tags,
  Ruler,
  Barcode,
  BadgePercent,
  Warehouse,
  Boxes,
  ClipboardCheck,
  FileText,
  Wallet,
  ArrowDownCircle,
  History,
  GitMerge,
  BookMarked,
  Scale,
  CalendarDays,
  TrendingUp,
  Landmark,
  Percent,
  Calculator,
  BarChart3,
  LineChart,
  PieChart,
  Activity,
  Clock,
  Hourglass,
  Coins,
  Building,
  GitBranch,
  UserCheck,
  Settings,
  ChevronLeft,
  ChevronRight,
  FolderKanban,
} from 'lucide-react';

const iconMap: Record<string, React.FC<{ className?: string }>> = {
  LayoutDashboard,
  ShoppingCart,
  MonitorDot,
  RotateCcw,
  Receipt,
  Users,
  ShoppingBag,
  PackageCheck,
  Undo2,
  CreditCard,
  Truck,
  BookOpen,
  Package,
  Tags,
  Ruler,
  Barcode,
  BadgePercent,
  Warehouse,
  Boxes,
  ClipboardCheck,
  FileText,
  Wallet,
  ArrowDownCircle,
  History,
  GitMerge,
  BookMarked,
  Scale,
  CalendarDays,
  TrendingUp,
  Landmark,
  Percent,
  Calculator,
  BarChart3,
  LineChart,
  PieChart,
  Activity,
  Clock,
  Hourglass,
  Coins,
  Building,
  GitBranch,
  UserCheck,
  Settings,
};

interface SidebarProps {
  mobileOpen: boolean;
  setMobileOpen: (open: boolean) => void;
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  mobileOpen,
  setMobileOpen,
  collapsed,
  setCollapsed,
}) => {
  const { businessId, role } = useBusiness();

  const renderIcon = (iconName: string, className: string = 'h-5 w-5') => {
    const IconComponent = iconMap[iconName] || FolderKanban;
    return <IconComponent className={className} />;
  };

  if (!businessId) return null;

  return (
    <>
      {/* Mobile Drawer Overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-xs lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar Container */}
      <aside
        aria-label="Sidebar Navigation"
        className={`fixed inset-y-0 left-0 z-50 flex flex-col bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 transition-all duration-300 ${
          mobileOpen ? 'translate-x-0 w-72' : '-translate-x-full lg:translate-x-0'
        } ${collapsed ? 'lg:w-20' : 'lg:w-64'}`}
      >
        {/* Sidebar Header */}
        <div className="flex h-16 items-center justify-between px-4 border-b border-slate-200 dark:border-slate-800 flex-shrink-0">
          <div className={`flex items-center gap-3 overflow-hidden ${collapsed ? 'lg:hidden' : ''}`}>
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm flex-shrink-0 shadow-sm">
              BH
            </div>
            <div className="truncate">
              <span className="font-bold text-slate-900 dark:text-slate-100 text-sm block truncate">
                BusinessHub
              </span>
              <span className="text-[10px] uppercase font-semibold text-indigo-600 dark:text-indigo-400 block tracking-wider">
                {role || 'MEMBER'}
              </span>
            </div>
          </div>

          {collapsed && (
            <div className="hidden lg:flex mx-auto w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 items-center justify-center text-white font-bold text-sm shadow-sm">
              BH
            </div>
          )}

          {/* Mobile close button */}
          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            className="lg:hidden rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
            aria-label="Close Sidebar"
          >
            ✕
          </button>

          {/* Desktop Collapse Toggle */}
          <button
            type="button"
            onClick={() => setCollapsed(!collapsed)}
            className="hidden lg:flex rounded-lg p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            aria-label={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        </div>

        {/* Navigation Content */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
          {navigationGroups.map((group) => {
            const visibleItems = group.items.filter((item) => {
              if (!item.roles) return true;
              if (!role) return false;
              return item.roles.includes(role);
            });

            if (visibleItems.length === 0) return null;

            return (
              <div key={group.id} className="space-y-1">
                {!collapsed && (
                  <h3 className="px-3 text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-2">
                    {group.title}
                  </h3>
                )}
                <nav className="space-y-0.5">
                  {visibleItems.map((item) => {
                    const targetPath = item.path(businessId);
                    return (
                      <NavLink
                        key={item.id}
                        to={targetPath}
                        onClick={() => setMobileOpen(false)}
                        title={collapsed ? item.label : undefined}
                        className={({ isActive }) =>
                          `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors group relative ${
                            isActive
                              ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 font-semibold'
                              : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/80'
                          } ${collapsed ? 'lg:justify-center lg:px-2' : ''}`
                        }
                      >
                        <span className="flex-shrink-0">{renderIcon(item.iconName)}</span>
                        {!collapsed && <span className="truncate">{item.label}</span>}
                      </NavLink>
                    );
                  })}
                </nav>
              </div>
            );
          })}
        </div>

        {/* Sidebar Footer - Switch Business */}
        <div className="p-3 border-t border-slate-200 dark:border-slate-800 flex-shrink-0">
          <NavLink
            to="/businesses"
            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors ${
              collapsed ? 'lg:justify-center lg:px-2' : ''
            }`}
            title={collapsed ? 'Ganti Bisnis' : undefined}
          >
            <Building className="h-5 w-5 flex-shrink-0 text-slate-400" />
            {!collapsed && <span className="truncate">Ganti Bisnis</span>}
          </NavLink>
        </div>
      </aside>
    </>
  );
};
