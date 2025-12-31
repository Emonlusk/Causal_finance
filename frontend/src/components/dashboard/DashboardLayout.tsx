import { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { 
  LayoutDashboard, 
  Search, 
  PieChart, 
  Gamepad2, 
  BookOpen, 
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Bell
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useState } from "react";

interface DashboardLayoutProps {
  children: ReactNode;
}

const navItems = [
  { icon: LayoutDashboard, label: "Overview", path: "/dashboard" },
  { icon: Search, label: "Causal Analysis", path: "/analysis" },
  { icon: PieChart, label: "Portfolio Builder", path: "/portfolio" },
  { icon: Gamepad2, label: "Scenario Simulator", path: "/simulator" },
  { icon: BookOpen, label: "Research & Insights", path: "/research" },
];

const quickActions = [
  "Run quick scenario",
  "Rebalance portfolio", 
  "Generate report",
];

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  return (
    <div className="min-h-screen bg-background flex">
      {/* Sidebar */}
      <aside
        className={cn(
          "bg-sidebar text-sidebar-foreground flex flex-col transition-all duration-300 border-r border-sidebar-border",
          collapsed ? "w-16" : "w-64"
        )}
      >
        {/* Logo */}
        <div className="p-4 border-b border-sidebar-border">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-sidebar-primary flex items-center justify-center flex-shrink-0">
              <svg viewBox="0 0 24 24" className="w-5 h-5 text-sidebar-primary-foreground">
                <circle cx="6" cy="12" r="3" fill="currentColor" />
                <circle cx="18" cy="6" r="3" fill="currentColor" />
                <circle cx="18" cy="18" r="3" fill="currentColor" />
                <line x1="9" y1="12" x2="15" y2="7" stroke="currentColor" strokeWidth="2" />
                <line x1="9" y1="12" x2="15" y2="17" stroke="currentColor" strokeWidth="2" />
              </svg>
            </div>
            {!collapsed && <span className="font-bold text-lg">CausalAI</span>}
          </Link>
        </div>

        {/* User Card */}
        {!collapsed && (
          <div className="p-4 border-b border-sidebar-border">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-sidebar-accent flex items-center justify-center">
                <span className="text-sm font-semibold">JD</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm truncate">John Doe</div>
                <div className="text-xs text-sidebar-foreground/60">Pro Plan</div>
              </div>
            </div>
            {/* Risk Meter */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-sidebar-foreground/60">Risk Profile</span>
                <span className="font-medium text-accent">Moderate</span>
              </div>
              <div className="h-1.5 bg-sidebar-accent rounded-full overflow-hidden">
                <div className="h-full w-1/2 bg-gradient-to-r from-success via-warning to-destructive rounded-full" />
              </div>
            </div>
            {/* Portfolio Value */}
            <div className="mt-3 pt-3 border-t border-sidebar-border">
              <div className="text-xs text-sidebar-foreground/60">Portfolio Value</div>
              <div className="text-xl font-bold">$125,430</div>
              <div className="text-xs text-success">+8.3% this month</div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 p-2">
          <ul className="space-y-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors",
                      isActive
                        ? "bg-sidebar-primary text-sidebar-primary-foreground"
                        : "hover:bg-sidebar-accent text-sidebar-foreground/70 hover:text-sidebar-foreground"
                    )}
                  >
                    <item.icon className="w-5 h-5 flex-shrink-0" />
                    {!collapsed && <span className="text-sm font-medium">{item.label}</span>}
                  </Link>
                </li>
              );
            })}
          </ul>

          {/* Quick Actions */}
          {!collapsed && (
            <div className="mt-6">
              <div className="px-3 py-2 text-xs font-semibold text-sidebar-foreground/50 uppercase tracking-wider">
                Quick Actions
              </div>
              <ul className="space-y-1">
                {quickActions.map((action) => (
                  <li key={action}>
                    <button className="w-full text-left px-3 py-2 text-sm text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent rounded-lg transition-colors">
                      {action}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </nav>

        {/* Bottom Actions */}
        <div className="p-2 border-t border-sidebar-border">
          <Link
            to="/settings"
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-sidebar-accent text-sidebar-foreground/70 hover:text-sidebar-foreground transition-colors"
          >
            <Settings className="w-5 h-5" />
            {!collapsed && <span className="text-sm font-medium">Settings</span>}
          </Link>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-sidebar-accent text-sidebar-foreground/70 hover:text-sidebar-foreground transition-colors"
          >
            {collapsed ? (
              <ChevronRight className="w-5 h-5" />
            ) : (
              <>
                <ChevronLeft className="w-5 h-5" />
                <span className="text-sm font-medium">Collapse</span>
              </>
            )}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <header className="h-16 border-b border-border bg-card flex items-center justify-between px-6">
          <div>
            <h1 className="text-lg font-semibold text-foreground">
              {navItems.find((item) => item.path === location.pathname)?.label || "Dashboard"}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-destructive rounded-full" />
            </Button>
            <Button variant="ghost" size="icon">
              <LogOut className="w-5 h-5" />
            </Button>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
