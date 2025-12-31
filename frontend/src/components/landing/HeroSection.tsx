import { Button } from "@/components/ui/button";
import { CausalGraphAnimation } from "./CausalGraphAnimation";
import { ArrowRight, Play } from "lucide-react";

export function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden bg-gradient-to-br from-primary via-primary/90 to-accent">
      {/* Animated background graph */}
      <CausalGraphAnimation />
      
      {/* Gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-primary/50" />
      
      {/* Content */}
      <div className="relative z-10 container mx-auto px-6 text-center">
        <div className="max-w-4xl mx-auto">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-foreground/10 backdrop-blur-sm border border-primary-foreground/20 mb-8 opacity-0 animate-fade-in">
            <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
            <span className="text-sm font-medium text-primary-foreground/90">
              Powered by Causal AI
            </span>
          </div>
          
          {/* Main headline */}
          <h1 className="text-4xl md:text-5xl lg:text-6xl xl:text-7xl font-bold text-primary-foreground leading-tight mb-6 opacity-0 animate-fade-in-up animation-delay-100">
            Beyond Correlation.
            <br />
            <span className="text-primary-foreground/90">
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
          <p className="text-lg md:text-xl text-primary-foreground/80 max-w-2xl mx-auto mb-10 opacity-0 animate-fade-in-up animation-delay-300">
            Causal AI for intelligent asset allocation. Discover true economic drivers, 
            optimize with causation, and build portfolios resilient to market changes.
          </p>
          
          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 opacity-0 animate-fade-in-up animation-delay-500">
            <Button
              size="lg"
              className="bg-primary-foreground text-primary hover:bg-primary-foreground/90 font-semibold px-8 py-6 text-lg rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 group"
            >
              Start Free Trial
              <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
            </Button>
            <Button
              size="lg"
              variant="outline"
              className="border-primary-foreground/30 text-primary-foreground hover:bg-primary-foreground/10 font-semibold px-8 py-6 text-lg rounded-xl backdrop-blur-sm"
            >
              <Play className="mr-2 h-5 w-5" />
              Explore Demo
            </Button>
          </div>
          
          {/* Stats bar */}
          <div className="mt-16 pt-8 border-t border-primary-foreground/10 opacity-0 animate-fade-in animation-delay-700">
            <div className="grid grid-cols-3 gap-8 max-w-2xl mx-auto">
              <div className="text-center">
                <div className="text-3xl md:text-4xl font-bold text-primary-foreground mb-1">+18%</div>
                <div className="text-sm text-primary-foreground/60">Sharpe Ratio</div>
              </div>
              <div className="text-center">
                <div className="text-3xl md:text-4xl font-bold text-primary-foreground mb-1">-22%</div>
                <div className="text-sm text-primary-foreground/60">Volatility</div>
              </div>
              <div className="text-center">
                <div className="text-3xl md:text-4xl font-bold text-primary-foreground mb-1">92%</div>
                <div className="text-sm text-primary-foreground/60">Confidence</div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Scroll indicator */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 opacity-0 animate-fade-in animation-delay-1000">
        <div className="w-6 h-10 rounded-full border-2 border-primary-foreground/30 flex items-start justify-center p-2">
          <div className="w-1.5 h-3 rounded-full bg-primary-foreground/50 animate-bounce" />
        </div>
      </div>
    </section>
  );
}
