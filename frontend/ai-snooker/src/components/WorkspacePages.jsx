import DashboardPage from "../pages/DashboardPage";
import ProfilePage from "../pages/ProfilePage";
import SetupPage from "../pages/SetupPage";
import CriteriaPage from "../pages/CriteriaPage";
import TrainingPage from "../pages/TrainingPage";
import SummaryPage from "../pages/SummaryPage";
import HistoryPage from "../pages/HistoryPage";
import M4PreviewPage from "../pages/M4PreviewPage";

export function WorkspacePages({
  page,
  view,
  m1Auto,
  prepareM1,
  cancelM1,
  cancelM1Training,
  resetTrainingState,
}) {
  switch (page) {
    case "dashboard":
      return <DashboardPage {...view} />;
    case "profile":
      return <ProfilePage {...view} onTrainingReset={resetTrainingState} />;
    case "setup":
      return <SetupPage {...view} m1Auto={m1Auto} prepareM1={prepareM1} cancelM1={cancelM1} />;
    case "criteria":
      return <CriteriaPage {...view} />;
    case "training":
      return <TrainingPage {...view} m1Auto={m1Auto} cancelM1={cancelM1Training} />;
    case "m4-preview":
      return <M4PreviewPage setPage={view.setPage} />;
    case "summary":
      return view.report ? <SummaryPage {...view} /> : null;
    case "history":
    case "compare":
      return <HistoryPage {...view} />;
    default:
      return null;
  }
}
