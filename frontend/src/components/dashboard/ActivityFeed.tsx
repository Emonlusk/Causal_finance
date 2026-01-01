import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { RefreshCw, TrendingUp, Bell, FileText, AlertCircle, Briefcase, LineChart } from "lucide-react";
import { useActivities } from "@/lib/hooks";
import { formatDistanceToNow } from "date-fns";

const activityIcons: Record<string, typeof RefreshCw> = {
  portfolio_rebalance: RefreshCw,
  causal_analysis: LineChart,
  model_update: TrendingUp,
  scenario_run: FileText,
  portfolio_created: Briefcase,
  economic_alert: Bell,
  market_alert: AlertCircle,
};

const activityColors: Record<string, string> = {
  portfolio_rebalance: "text-primary",
  causal_analysis: "text-accent",
  model_update: "text-success",
  scenario_run: "text-blue-500",
  portfolio_created: "text-primary",
  economic_alert: "text-warning",
  market_alert: "text-destructive",
};

// Fallback activities for when user has no activities yet
const defaultActivities = [
  {
    id: 0,
    activity_type: "portfolio_created",
    title: "Welcome to Causal Finance",
    description: "Start by creating your first portfolio",
    created_at: new Date().toISOString(),
    is_read: false,
  },
];

export function ActivityFeed() {
  const { data, isLoading, error } = useActivities(10);
  
  const activities = data?.activities?.length ? data.activities : defaultActivities;

  const formatTime = (dateString: string) => {
    try {
      return formatDistanceToNow(new Date(dateString), { addSuffix: true });
    } catch {
      return "recently";
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex items-start gap-3">
                <Skeleton className="w-8 h-8 rounded-lg" />
                <div className="flex-1">
                  <Skeleton className="h-4 w-3/4 mb-1" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="text-sm text-muted-foreground text-center py-4">
            Unable to load activities
          </div>
        ) : (
          <div className="space-y-4">
            {activities.map((activity) => {
              const Icon = activityIcons[activity.activity_type] || FileText;
              const color = activityColors[activity.activity_type] || "text-muted-foreground";
              
              return (
                <div key={activity.id} className="flex items-start gap-3">
                  <div className={`p-2 rounded-lg bg-secondary ${color}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm">{activity.title}</div>
                    <div className="text-xs text-muted-foreground">{activity.description}</div>
                  </div>
                  <div className="text-xs text-muted-foreground whitespace-nowrap">
                    {formatTime(activity.created_at)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
