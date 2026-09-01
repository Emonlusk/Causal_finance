import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Menu, X, LogOut, User } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

export function Navbar() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 50);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const navLinks = [
    { label: "Features", href: "#features" },
    { label: "Demo", href: "#demo" },
    { label: "Results", href: "#results" },
    { label: "Dashboard", href: "/dashboard" },
  ];

  // The unscrolled state floats over the hero's fixed near-black gradient
  // (--gradient-hero, identical in light/dark mode - see index.css), so its
  // text uses the --sidebar-* tokens: those are the theme-invariant
  // near-white-on-dark chrome colors, not --primary-foreground (which
  // deliberately flips between light/dark mode for button contrast and
  // would go invisible against the dark hero in dark mode).
  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled
          ? "bg-background/90 backdrop-blur-md border-b border-border shadow-sm"
          : "bg-transparent"
      }`}
    >
      <div className="w-full px-8">
        <div className="flex items-center justify-between h-16 md:h-20">
          {/* Logo - always the brand yellow mark, regardless of scroll/theme */}
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center flex-shrink-0">
              <svg viewBox="0 0 24 24" className="w-5 h-5 text-accent-foreground">
                <circle cx="6" cy="12" r="3" fill="currentColor" />
                <circle cx="18" cy="6" r="3" fill="currentColor" />
                <circle cx="18" cy="18" r="3" fill="currentColor" />
                <line x1="9" y1="12" x2="15" y2="7" stroke="currentColor" strokeWidth="2" />
                <line x1="9" y1="12" x2="15" y2="17" stroke="currentColor" strokeWidth="2" />
              </svg>
            </div>
            <span className={`font-heading font-bold text-lg tracking-tight transition-colors ${
              isScrolled ? "text-foreground" : "text-sidebar-foreground"
            }`}>
              CausalAI
            </span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className={`label-brand text-xs font-semibold transition-colors hover:opacity-80 ${
                  isScrolled ? "text-muted-foreground hover:text-foreground" : "text-sidebar-foreground/70 hover:text-sidebar-foreground"
                }`}
              >
                {link.label}
              </a>
            ))}
          </div>

          {/* Desktop CTAs */}
          <div className="hidden md:flex items-center gap-3">
            {isAuthenticated && user ? (
              <>
                <Link to="/dashboard">
                  <Button
                    variant="ghost"
                    className={
                      isScrolled ? "" : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground"
                    }
                  >
                    Dashboard
                  </Button>
                </Link>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="relative h-9 w-9 rounded-full">
                      <Avatar className="h-9 w-9">
                        <AvatarFallback className="bg-accent text-accent-foreground">
                          {getInitials(user.name || user.email)}
                        </AvatarFallback>
                      </Avatar>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <div className="flex items-center justify-start gap-2 p-2">
                      <div className="flex flex-col space-y-1 leading-none">
                        <p className="font-medium">{user.name}</p>
                        <p className="text-xs text-muted-foreground">{user.email}</p>
                      </div>
                    </div>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => navigate("/dashboard")}>
                      <User className="mr-2 h-4 w-4" />
                      Dashboard
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={handleLogout}>
                      <LogOut className="mr-2 h-4 w-4" />
                      Sign out
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            ) : (
              <>
                <Link to="/login">
                  <Button
                    variant="ghost"
                    className={
                      isScrolled ? "" : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground"
                    }
                  >
                    Log In
                  </Button>
                </Link>
                <Link to="/register">
                  {/* The one primary action in the nav - always the accent yellow */}
                  <Button variant="accent">
                    Get Started
                  </Button>
                </Link>
              </>
            )}
          </div>

          {/* Mobile Menu Toggle */}
          <button
            className="md:hidden p-2"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            {isMobileMenuOpen ? (
              <X className={`w-6 h-6 ${isScrolled ? "text-foreground" : "text-sidebar-foreground"}`} />
            ) : (
              <Menu className={`w-6 h-6 ${isScrolled ? "text-foreground" : "text-sidebar-foreground"}`} />
            )}
          </button>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-border/50">
            <div className="flex flex-col gap-4">
              {navLinks.map((link) => (
                <a
                  key={link.label}
                  href={link.href}
                  className={`label-brand text-xs font-semibold ${
                    isScrolled ? "text-foreground" : "text-sidebar-foreground"
                  }`}
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  {link.label}
                </a>
              ))}
              <div className="flex flex-col gap-2 pt-4 border-t border-border/50">
                {isAuthenticated && user ? (
                  <>
                    <div className="flex items-center gap-2 px-2 py-1">
                      <Avatar className="h-8 w-8">
                        <AvatarFallback className="bg-accent text-accent-foreground text-xs">
                          {getInitials(user.name || user.email)}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex flex-col">
                        <span className="text-sm font-medium">{user.name}</span>
                        <span className="text-xs text-muted-foreground">{user.email}</span>
                      </div>
                    </div>
                    <Link to="/dashboard" onClick={() => setIsMobileMenuOpen(false)}>
                      <Button variant="outline" className="w-full">
                        Dashboard
                      </Button>
                    </Link>
                    <Button
                      variant="destructive"
                      className="w-full"
                      onClick={() => {
                        handleLogout();
                        setIsMobileMenuOpen(false);
                      }}
                    >
                      Sign out
                    </Button>
                  </>
                ) : (
                  <>
                    <Link to="/login" onClick={() => setIsMobileMenuOpen(false)}>
                      <Button variant="outline" className="w-full">
                        Log In
                      </Button>
                    </Link>
                    <Link to="/register" onClick={() => setIsMobileMenuOpen(false)}>
                      <Button variant="accent" className="w-full">
                        Get Started
                      </Button>
                    </Link>
                  </>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}
