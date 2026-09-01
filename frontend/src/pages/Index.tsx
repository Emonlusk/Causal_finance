import { Navbar } from "@/components/landing/Navbar";
import { HeroSection } from "@/components/landing/HeroSection";
import { FeaturesSection } from "@/components/landing/FeaturesSection";
import { InteractiveDemo } from "@/components/landing/InteractiveDemo";
import { VerifiedResults } from "@/components/landing/VerifiedResults";
import { CTASection } from "@/components/landing/CTASection";
import { Footer } from "@/components/landing/Footer";

const Index = () => {
  return (
    <div className="min-h-screen">
      <Navbar />
      <HeroSection />
      <FeaturesSection />
      <InteractiveDemo />
      <VerifiedResults />
      <CTASection />
      <Footer />
    </div>
  );
};

export default Index;
