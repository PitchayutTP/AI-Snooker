import React from "react";

export default function StatsPanel({ stats }) {
  return (
    <div className="flex flex-col h-full gap-6">
      <h2 className="text-xl font-bold text-gray-800 border-b pb-2">
        สถิติ Real-time
      </h2>

      <div className="flex justify-between bg-gray-50 p-4 rounded-lg border">
        <div className="text-center w-1/2">
          <p className="text-sm text-gray-500">องศาศอก</p>
          <p className="text-3xl font-bold text-blue-600">
            {stats.elbowAngle}°
          </p>
        </div>
        <div className="text-center w-1/2 border-l pl-4">
          <p className="text-sm text-gray-500">หัวขยับ</p>
          <p className="text-3xl font-bold text-red-500">
            {stats.headMovement} cm
          </p>
        </div>
      </div>

      <div className="flex-1 bg-gray-50 border rounded-lg p-4 flex flex-col">
        <p className="text-sm text-gray-500 mb-2 font-bold">กราฟความนิ่งแขน</p>
        <div className="flex-1 flex items-center justify-center text-gray-400 border-2 border-dashed border-gray-200 rounded">
          [ พื้นที่รอกราฟ Recharts ]
        </div>
      </div>

      <div className="h-1/3 bg-white border rounded-lg p-4 overflow-y-auto">
        <p className="text-sm font-bold text-gray-500 mb-3">บันทึกช็อตล่าสุด</p>
        <ul className="space-y-3 text-sm">
          <li className="flex items-center justify-between text-green-600 bg-green-50 p-2 rounded">
            <span>✅ ช็อตที่ 3</span>
            <span className="font-bold">ผ่าน</span>
          </li>
          <li className="flex items-center justify-between text-red-600 bg-red-50 p-2 rounded">
            <span>❌ ช็อตที่ 2</span>
            <span>หัวขยับเกิน</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
