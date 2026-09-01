import { Link } from "react-router-dom";

export function Footer() {
  const links = [
    { label: "Features", href: "#features" },
    { label: "Demo", href: "#demo" },
    { label: "Dashboard", href: "/dashboard" },
  ];

  return (
    <footer className="bg-foreground text-background py-16">
      <div className="container mx-auto px-6">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-8 mb-12">
          {/* Brand */}
          <div className="max-w-sm">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
                <svg viewBox="0 0 24 24" className="w-5 h-5 text-accent-foreground">
                  <circle cx="6" cy="12" r="3" fill="currentColor" />
                  <circle cx="18" cy="6" r="3" fill="currentColor" />
                  <circle cx="18" cy="18" r="3" fill="currentColor" />
                  <line x1="9" y1="12" x2="15" y2="7" stroke="currentColor" strokeWidth="2" />
                  <line x1="9" y1="12" x2="15" y2="17" stroke="currentColor" strokeWidth="2" />
                </svg>
              </div>
              <span className="font-heading font-bold text-lg tracking-tight">CausalAI</span>
            </div>
            <p className="text-background/60 text-sm">
              A research project applying causal inference - Granger causality, DoWhy,
              EconML double machine learning - to portfolio allocation.
            </p>
          </div>

          {/* Links */}
          <div>
            <h4 className="label-brand text-xs font-semibold mb-4">Explore</h4>
            <ul className="space-y-2">
              {links.map((link) => (
                <li key={link.label}>
                  {link.href.startsWith("#") ? (
                    <a
                      href={link.href}
                      className="text-background/60 hover:text-background text-sm transition-colors"
                    >
                      {link.label}
                    </a>
                  ) : (
                    <Link
                      to={link.href}
                      className="text-background/60 hover:text-background text-sm transition-colors"
                    >
                      {link.label}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom */}
        <div className="pt-8 border-t border-background/10">
          <p className="text-sm text-background/40">
            © {new Date().getFullYear()} CausalAI. Built for research purposes.
          </p>
        </div>
      </div>
    </footer>
  );
}
