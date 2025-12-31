import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RefreshCw, TrendingUp, Bell, FileText } from "lucide-react";

const activities = [
  {
    icon: RefreshCw,
    title: "Portfolio rebalanced",
    description: "Reduced tech allocation by 5%",
    time: "2 days ago",
    color: "text-primary",
  },
  {
    icon: TrendingUp,
    title: "Causal model updated",
    description: "New economic data incorporated",
    time: "1 week ago",
    color: "text-accent",
  },
  {
    icon: Bell,
    title: "Economic Alert",
    description: "Fed meeting scheduled today",
    time: "Today",
    color: "text-warning",
  },
  {
    icon: FileText,
    title: "Report generated",
    description: "Q4 performance analysis ready",
    time: "2 weeks ago",
    color: "text-muted-foreground",
  },
];

export function ActivityFeed() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {activities.map((activity, index) => (
            <div key={index} className="flex items-start gap-3">
              <div className={`p-2 rounded-lg bg-secondary ${activity.color}`}>
                <activity.icon className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm">{activity.title}</div>
                <div className="text-xs text-muted-foreground">{activity.description}</div>
              </div>
              <div className="text-xs text-muted-foreground whitespace-nowrap">
                {activity.time}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
