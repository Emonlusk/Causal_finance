import { useState } from "react";
import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronRight, Download, FileText, Github, Database, BookOpen } from "lucide-react";

const sections = [
  { id: "methodology", label: "Methodology", icon: BookOpen },
  { id: "findings", label: "Key Findings", icon: FileText },
  { id: "data", label: "Data Sources", icon: Database },
  { id: "downloads", label: "Downloads", icon: Download },
];

const Research = () => {
  const [activeSection, setActiveSection] = useState("methodology");
  const [expandedItems, setExpandedItems] = useState<string[]>(["causal"]);

  const toggleExpand = (id: string) => {
    setExpandedItems((prev) => prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]);
  };

  return (
    <DashboardLayout>
      <div className="flex gap-6">
        {/* Sidebar Nav */}
        <div className="w-48 flex-shrink-0 space-y-1">
          {sections.map((s) => (
            <button key={s.id} onClick={() => setActiveSection(s.id)} className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${activeSection === s.id ? "bg-primary text-primary-foreground" : "hover:bg-secondary text-muted-foreground"}`}>
              <s.icon className="w-4 h-4" />
              {s.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 space-y-6">
          {activeSection === "methodology" && (
            <>
              <div>
                <h2 className="text-2xl font-bold mb-2">Methodology</h2>
                <p className="text-muted-foreground">Our approach to causal portfolio optimization</p>
              </div>

              {[
                { id: "causal", title: "Causal Inference Framework", content: "We use Directed Acyclic Graphs (DAGs) to model the causal relationships between economic factors and asset returns. Our framework applies the backdoor adjustment criterion to identify confounding variables and estimate true causal effects using DoWhy and EconML libraries." },
                { id: "data", title: "Data Pipeline", content: "Real-time data integration from Yahoo Finance, FRED, and Quandl. Our preprocessing pipeline handles time alignment, missing data imputation, and feature engineering to ensure consistent causal estimation across different asset classes." },
                { id: "model", title: "Model Implementation", content: "Treatment effects are estimated using Double Machine Learning (DML) with gradient boosting as the base learner. We validate our models using cross-fitting and provide confidence intervals through bootstrap resampling." },
              ].map((item) => (
                <Card key={item.id}>
                  <CardHeader className="cursor-pointer" onClick={() => toggleExpand(item.id)}>
                    <CardTitle className="flex items-center gap-2 text-lg">
                      {expandedItems.includes(item.id) ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                      {item.title}
                    </CardTitle>
                  </CardHeader>
                  {expandedItems.includes(item.id) && (
                    <CardContent><p className="text-muted-foreground">{item.content}</p></CardContent>
                  )}
                </Card>
              ))}
            </>
          )}

          {activeSection === "findings" && (
            <>
              <h2 className="text-2xl font-bold">Key Findings</h2>
              <div className="grid md:grid-cols-3 gap-4">
                {[
                  { title: "Rate Sensitivity", value: "3×", desc: "Tech is 3× more sensitive to rates than healthcare" },
                  { title: "Volatility Reduction", value: "-22%", desc: "Causal portfolios show 22% lower volatility" },
                  { title: "Sharpe Improvement", value: "+0.6", desc: "Average Sharpe ratio improvement vs traditional" },
                ].map((f) => (
                  <Card key={f.title}>
                    <CardContent className="pt-6 text-center">
                      <div className="text-3xl font-bold gradient-text mb-2">{f.value}</div>
                      <div className="font-medium mb-1">{f.title}</div>
                      <div className="text-sm text-muted-foreground">{f.desc}</div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </>
          )}

          {activeSection === "data" && (
            <>
              <h2 className="text-2xl font-bold">Data Sources</h2>
              <div className="space-y-3">
                {["Yahoo Finance - Daily stock prices and fundamentals", "FRED - Federal Reserve economic indicators", "Quandl - Alternative data and commodities", "BLS - Labor statistics and CPI data"].map((s) => (
                  <div key={s} className="p-4 bg-secondary/50 rounded-lg flex items-center gap-3">
                    <Database className="w-5 h-5 text-primary" />
                    <span>{s}</span>
                  </div>
                ))}
              </div>
            </>
          )}

          {activeSection === "downloads" && (
            <>
              <h2 className="text-2xl font-bold">Downloads</h2>
              <div className="grid md:grid-cols-2 gap-4">
                {[
                  { title: "Research Paper", desc: "Full methodology (PDF, 24 pages)", icon: FileText },
                  { title: "Code Repository", desc: "GitHub with replication code", icon: Github },
                  { title: "Data Package", desc: "Sample datasets (ZIP)", icon: Database },
                  { title: "API Documentation", desc: "Integration guide", icon: BookOpen },
                ].map((d) => (
                  <Card key={d.title} className="hover:border-primary/50 transition-colors cursor-pointer">
                    <CardContent className="pt-6 flex items-start gap-4">
                      <div className="p-3 bg-primary/10 rounded-lg"><d.icon className="w-6 h-6 text-primary" /></div>
                      <div>
                        <div className="font-medium">{d.title}</div>
                        <div className="text-sm text-muted-foreground">{d.desc}</div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
};

export default Research;
