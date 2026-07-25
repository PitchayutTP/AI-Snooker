import React from "react";
import Button from "../components/Button";

export default function SummaryReport({ onBackHome }) {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 p-4">
      <div className="w-full max-w-3xl bg-white p-10 rounded-2xl shadow-xl text-center">
        <h1 className="text-4xl font-bold text-green-600 mb-2">
          ✅ TEST PASSED ✅
        </h1>
        <p className="text-lg font-bold text-gray-700 mb-8">
          🎉 คุณปลดล็อกบทที่ 3 แล้ว
        </p>

        <div className="flex justify-center gap-4 mb-8 text-4xl">
          <span>⭐</span>
          <span>⭐</span>
          <span className="grayscale opacity-50">⭐</span>
        </div>

        <h2 className="text-xl font-bold mb-6 border-b pb-2 text-left">
          สถิติสรุป (Summary)
        </h2>

        <div className="grid grid-cols-3 gap-6 mb-10 text-left">
          <div className="p-4 border rounded-xl bg-gray-50">
            <p className="text-sm text-gray-500 mb-1">จำนวนการแทง</p>
            <p className="text-2xl font-bold">15 ช็อต</p>
          </div>
          <div className="p-4 border rounded-xl bg-gray-50">
            <p className="text-sm text-gray-500 mb-1">ความแม่นยำรวม</p>
            <p className="text-2xl font-bold text-green-600">85%</p>
          </div>
          <div className="p-4 border rounded-xl bg-gray-50">
            <p className="text-sm text-gray-500 mb-1">ด่านถัดไป</p>
            <p className="text-2xl font-bold text-blue-600">บทที่ 3</p>
          </div>
        </div>

        <div className="flex justify-center gap-4">
          <Button variant="outline" onClick={onBackHome}>
            ดูรายละเอียดช็อต
          </Button>
          <Button variant="primary" onClick={onBackHome}>
            กลับหน้า Dashboard
          </Button>
        </div>
      </div>
    </div>
  );
}
