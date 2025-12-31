import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { SummaryCards } from "@/components/dashboard/SummaryCards";
import { PerformanceChart } from "@/components/dashboard/PerformanceChart";
import { ActivityFeed } from "@/components/dashboard/ActivityFeed";
import { QuickSimulator } from "@/components/dashboard/QuickSimulator";

const Dashboard = () => {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Summary Cards */}
        <SummaryCards />

        {/* Performance Chart */}
        <PerformanceChart />

        {/* Bottom Row */}
        <div className="grid lg:grid-cols-2 gap-6">
          <ActivityFeed />
          <QuickSimulator />
        </div>
      </div>
    </DashboardLayout>
  );
};

export default Dashboard;
