import { Star } from "lucide-react";

const testimonials = [
  {
    quote: "The causal insights completely changed how I think about portfolio construction. No more chasing correlations that disappear.",
    author: "Sarah Chen",
    role: "Portfolio Manager, Apex Capital",
    rating: 5,
  },
  {
    quote: "Finally, a tool that helps me understand WHY my portfolio behaves the way it does during market stress.",
    author: "Michael Torres",
    role: "CIO, Vertex Investments",
    rating: 5,
  },
  {
    quote: "The scenario simulator saved us during the 2023 rate hikes. We were positioned correctly because we understood the causal chain.",
    author: "Dr. Emily Watson",
    role: "Quantitative Researcher, Stanford",
    rating: 5,
  },
];

const logos = [
  "Harvard Business School",
  "MIT Sloan",
  "Stanford GSB",
  "Wharton",
  "Chicago Booth",
];

export function SocialProof() {
  return (
    <section className="py-24 bg-background">
      <div className="container mx-auto px-6">
        {/* Stats Row */}
        <div className="grid md:grid-cols-4 gap-8 mb-20">
          <div className="text-center">
            <div className="text-4xl md:text-5xl font-bold gradient-text mb-2">$2.4B+</div>
            <div className="text-muted-foreground">Assets Analyzed</div>
          </div>
          <div className="text-center">
            <div className="text-4xl md:text-5xl font-bold gradient-text mb-2">+18%</div>
            <div className="text-muted-foreground">Avg. Sharpe Improvement</div>
          </div>
          <div className="text-center">
            <div className="text-4xl md:text-5xl font-bold gradient-text mb-2">-22%</div>
            <div className="text-muted-foreground">Volatility Reduction</div>
          </div>
          <div className="text-center">
            <div className="text-4xl md:text-5xl font-bold gradient-text mb-2">500+</div>
            <div className="text-muted-foreground">Active Portfolios</div>
          </div>
        </div>
        
        {/* Testimonials */}
        <div className="grid md:grid-cols-3 gap-6 mb-16">
          {testimonials.map((testimonial, index) => (
            <div
              key={index}
              className="bg-card rounded-xl p-6 border border-border hover-lift"
            >
              {/* Rating */}
              <div className="flex gap-1 mb-4">
                {Array.from({ length: testimonial.rating }).map((_, i) => (
                  <Star key={i} className="w-4 h-4 fill-warning text-warning" />
                ))}
              </div>
              
              {/* Quote */}
              <blockquote className="text-foreground mb-6 leading-relaxed">
                "{testimonial.quote}"
              </blockquote>
              
              {/* Author */}
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <span className="text-sm font-semibold text-primary">
                    {testimonial.author.split(" ").map((n) => n[0]).join("")}
                  </span>
                </div>
                <div>
                  <div className="font-medium text-foreground">{testimonial.author}</div>
                  <div className="text-sm text-muted-foreground">{testimonial.role}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
        
        {/* University Logos */}
        <div className="border-t border-border pt-12">
          <p className="text-center text-sm text-muted-foreground mb-8">
            Research methodology validated by leading institutions
          </p>
          <div className="flex flex-wrap justify-center items-center gap-8 md:gap-12">
            {logos.map((logo) => (
              <div
                key={logo}
                className="text-muted-foreground/50 font-semibold text-sm hover:text-muted-foreground transition-colors"
              >
                {logo}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
