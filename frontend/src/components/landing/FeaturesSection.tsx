import { FeatureCard } from "./FeatureCard";
import { MiniDAG } from "./MiniDAG";
import { MiniBarChart } from "./MiniBarChart";
import { 
  Search, 
  Scale, 
  SlidersHorizontal, 
  Activity, 
  FileText, 
  Link2 
} from "lucide-react";

const features = [
  {
    icon: Search,
    title: "Causal Discovery",
    description: "Move beyond correlation to understand causation. Identify true economic drivers affecting your portfolio.",
    visual: <MiniDAG />,
  },
  {
    icon: Scale,
    title: "Smart Allocation",
    description: "Build portfolios resilient to economic changes using causal weights instead of historical correlations.",
    visual: <MiniBarChart traditional={[60, 40, 30]} causal={[40, 55, 50]} />,
  },
  {
    icon: SlidersHorizontal,
    title: "Scenario Planning",
    description: "What-if analysis for policy changes. Test your portfolio against interest rate hikes, inflation spikes, and more.",
    visual: (
      <div className="flex items-center gap-2">
        <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
          <div className="h-full w-2/3 bg-gradient-to-r from-primary to-accent rounded-full" />
        </div>
        <span className="text-xs font-medium text-accent">-0.8%</span>
      </div>
    ),
  },
  {
    icon: Activity,
    title: "Real-time Analysis",
    description: "Always-current economic indicators. Live market data integration keeps your insights up-to-date.",
    visual: (
      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1">
          <span className="text-muted-foreground">VIX</span>
          <span className="font-semibold text-success">18.2</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-muted-foreground">Fed</span>
          <span className="font-semibold text-warning">4.5%</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-muted-foreground">CPI</span>
          <span className="font-semibold text-destructive">3.2%</span>
        </div>
      </div>
    ),
  },
  {
    icon: FileText,
    title: "Research Backed",
    description: "Published causal inference techniques. Our methodology is grounded in peer-reviewed academic research.",
    visual: (
      <div className="flex items-center gap-2">
        <div className="w-8 h-10 bg-muted rounded flex items-center justify-center">
          <FileText className="w-4 h-4 text-muted-foreground" />
        </div>
        <div className="flex-1">
          <div className="h-1.5 bg-muted rounded w-full mb-1" />
          <div className="h-1.5 bg-muted rounded w-3/4" />
        </div>
      </div>
    ),
  },
  {
    icon: Link2,
    title: "Easy Integration",
    description: "Seamless implementation of insights. Export your optimized portfolio directly to your brokerage.",
    visual: (
      <div className="flex items-center justify-center gap-3">
        {["S", "F", "V", "TD"].map((logo) => (
          <div
            key={logo}
            className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center text-xs font-bold text-muted-foreground"
          >
            {logo}
          </div>
        ))}
      </div>
    ),
  },
];

export function FeaturesSection() {
  return (
    <section className="py-24 bg-background">
      <div className="container mx-auto px-6">
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
            Invest Smarter with{" "}
            <span className="gradient-text">Causal Intelligence</span>
          </h2>
          <p className="text-lg text-muted-foreground">
            Our platform combines cutting-edge causal AI with institutional-grade 
            portfolio optimization to help you make better investment decisions.
          </p>
        </div>
        
        {/* Features Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <FeatureCard
              key={feature.title}
              icon={feature.icon}
              title={feature.title}
              description={feature.description}
              visual={feature.visual}
              delay={index * 100}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
