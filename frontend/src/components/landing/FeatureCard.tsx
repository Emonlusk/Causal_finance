import { LucideIcon } from "lucide-react";
import { ReactNode } from "react";

interface FeatureCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  visual?: ReactNode;
  delay?: number;
}

export function FeatureCard({ icon: Icon, title, description, visual, delay = 0 }: FeatureCardProps) {
  return (
    <div 
      className="feature-card group cursor-pointer opacity-0 animate-fade-in-up"
      style={{ animationDelay: `${delay}ms` }}
    >
      {/* Icon */}
      <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors duration-300">
        <Icon className="w-6 h-6 text-primary" />
      </div>
      
      {/* Content */}
      <h3 className="text-lg font-semibold text-foreground mb-2 group-hover:text-primary transition-colors duration-300">
        {title}
      </h3>
      <p className="text-muted-foreground text-sm leading-relaxed mb-4">
        {description}
      </p>
      
      {/* Visual element */}
      {visual && (
        <div className="mt-auto pt-4 border-t border-border/50">
          {visual}
        </div>
      )}
    </div>
  );
}
