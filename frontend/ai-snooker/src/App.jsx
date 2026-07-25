import React, { useState } from "react";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import LiveTraining from "./pages/LiveTraining";
import SummaryReport from "./pages/SummaryReport";

export default function App() {
  const [currentPage, setCurrentPage] = useState("login");

  return (
    <div className="text-gray-900 font-sans h-screen w-screen overflow-x-hidden">
      {currentPage === "login" && (
        <Login onLogin={() => setCurrentPage("dashboard")} />
      )}

      {currentPage === "dashboard" && (
        <Dashboard onStartTraining={() => setCurrentPage("training")} />
      )}

      {currentPage === "training" && (
        <LiveTraining onEndTraining={() => setCurrentPage("report")} />
      )}

      {currentPage === "report" && (
        <SummaryReport onBackHome={() => setCurrentPage("dashboard")} />
      )}
    </div>
  );
}
