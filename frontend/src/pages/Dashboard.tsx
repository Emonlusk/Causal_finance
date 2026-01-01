import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { SummaryCards } from "@/components/dashboard/SummaryCards";
import { PerformanceChart } from "@/components/dashboard/PerformanceChart";
import { ActivityFeed } from "@/components/dashboard/ActivityFeed";

const Dashboard = () => {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Summary Cards */}
        <SummaryCards />

        {/* Performance Chart */}
        <PerformanceChart />

        {/* Activity Feed - Full Width */}
        <ActivityFeed />
      </div>
    </DashboardLayout>
  );
};

export default Dashboard;
