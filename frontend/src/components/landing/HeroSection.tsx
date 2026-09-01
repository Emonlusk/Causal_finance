import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { CausalGraphAnimation } from "./CausalGraphAnimation";
import { ArrowRight, Play } from "lucide-react";

export function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden bg-gradient-hero pt-24 pb-12">
      {/* Animated background graph */}
      <CausalGraphAnimation />

      {/* Content - the hero is fixed near-black chrome (--gradient-hero is
          identical in light/dark mode), so its text uses the theme-invariant
          sidebar-foreground tokens rather than primary/primary-foreground,
          which deliberately flips between light/dark mode for button
          contrast elsewhere in the app. */}
      <div className="relative z-10 container mx-auto px-6 text-center">
        <div className="max-w-4xl mx-auto">
          {/* Main headline */}
          <h1 className="text-4xl md:text-5xl lg:text-6xl xl:text-7xl font-bold text-sidebar-foreground leading-tight mb-6 opacity-0 animate-fade-in-up animation-delay-100">
            Beyond Correlation.
            <br />
            <span className="text-sidebar-foreground/90">
              Build Portfolios That Understand{" "}
              <span className="relative">
                Why
                <svg className="absolute -bottom-2 left-0 w-full h-3" viewBox="0 0 100 12" preserveAspectRatio="none">
                  <path
                    d="M0,6 Q25,0 50,6 T100,6"
                    fill="none"
                    stroke="hsl(var(--accent))"
                    strokeWidth="3"
                    className="animate-draw-line"
                    style={{ strokeDasharray: 100, strokeDashoffset: 100, animationDelay: "1s" }}
                  />
                </svg>
              </span>{" "}
              Markets Move
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-lg md:text-xl text-sidebar-foreground/70 max-w-2xl mx-auto mb-10 opacity-0 animate-fade-in-up animation-delay-300">
            Causal AI for intelligent asset allocation. Discover true economic drivers,
            optimize with causation, and build portfolios resilient to market changes.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 opacity-0 animate-fade-in-up animation-delay-500">
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
                className="bg-transparent border-sidebar-border text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground px-8 py-6 text-base rounded-xl backdrop-blur-sm"
              >
                <Play className="mr-2 h-5 w-5" />
                Explore Demo
              </Button>
            </a>
          </div>
        </div>
      </div>

      {/* Scroll indicator */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 opacity-0 animate-fade-in animation-delay-1000">
        <div className="w-6 h-10 rounded-full border-2 border-sidebar-border flex items-start justify-center p-2">
          <div className="w-1.5 h-3 rounded-full bg-sidebar-foreground/50 animate-bounce" />
        </div>
      </div>
    </section>
  );
}
