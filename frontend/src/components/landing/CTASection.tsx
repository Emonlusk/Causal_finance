import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";

export function CTASection() {
  return (
    <section className="py-24 bg-gradient-hero relative overflow-hidden">
      {/* Background pattern */}
      <div className="absolute inset-0 opacity-10">
        <svg className="w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
          <defs>
            <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
              <path d="M 10 0 L 0 0 0 10" fill="none" stroke="currentColor" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100" height="100" fill="url(#grid)" />
        </svg>
      </div>

      <div className="container mx-auto px-6 relative z-10">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold text-sidebar-foreground mb-6">
            Ready to Build Smarter Portfolios?
          </h2>
          <p className="text-lg text-sidebar-foreground/70 mb-10">
            Explore a research platform built on causal inference instead of
            plain correlation - discover, estimate, and simulate for yourself.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/register">
              <Button
                size="lg"
                variant="accent"
                className="px-8 py-6 text-base rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 group"
              >
                Get Started
                <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
              </Button>
            </Link>
            <a href="#demo">
              <Button
                size="lg"
                variant="outline"
                className="bg-transparent border-sidebar-border text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground px-8 py-6 text-base rounded-xl"
              >
                Explore Demo
              </Button>
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
