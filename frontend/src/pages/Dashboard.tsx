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

        {/* Performance Chart + Quick Simulator */}
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <PerformanceChart />
          </div>
          <QuickSimulator />
        </div>

        {/* Activity Feed - Full Width */}
        <ActivityFeed />
      </div>
    </DashboardLayout>
  );
};

export default Dashboard;
