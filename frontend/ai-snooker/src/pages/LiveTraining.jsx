import React from "react";
import Button from "../components/Button";

export default function LiveTraining({ onEndTraining }) {
  const stats = { elbowAngle: 92.5, headMovement: 1.2 };

  return (
    <div className="h-screen w-full flex bg-gray-50 overflow-hidden">
      {/* ฝั่งซ้าย 66.6% (Video) */}
      <div className="w-2/3 h-full p-6 flex flex-col">
        <div className="text-center mb-4">
          <h1 className="text-2xl font-bold text-gray-900 flex items-center justify-center gap-2">
            🔴 Live Training: บทที่ 2
          </h1>
          <p className="text-gray-600">การส่งคิว (The Delivery)</p>
        </div>

        <div className="flex-1 bg-gray-200 rounded-xl relative flex items-center justify-center border-4 border-gray-300">
          <span className="text-gray-500 font-bold">
            ภาพวิดีโอจากกล้อง (MediaPipe Overlay)
          </span>

          <div className="absolute bottom-6 flex gap-4">
            <Button variant="success">▶️ เริ่มบันทึก</Button>
            <Button variant="danger" onClick={onEndTraining}>
              ⏹️ จบการซ้อม
            </Button>
          </div>
        </div>
      </div>

      {/* ฝั่งขวา 33.3% (Stats) */}
      <aside className="w-1/3 h-full bg-white border-l shadow-lg p-6 flex flex-col gap-6">
        <div>
          <h2 className="text-lg font-bold mb-4 border-b pb-2">
            บันทึกช็อตล่าสุด
          </h2>
          <ul className="space-y-2 text-sm">
            <li className="flex justify-between bg-green-50 text-green-700 p-2 rounded">
              <span>✅ ช็อตที่ 3</span>
              <b>ผ่าน</b>
            </li>
            <li className="flex justify-between bg-red-50 text-red-700 p-2 rounded">
              <span>❌ ช็อตที่ 2</span>
              <span>หัวขยับเกิน</span>
            </li>
            <li className="flex justify-between bg-green-50 text-green-700 p-2 rounded">
              <span>✅ ช็อตที่ 1</span>
              <b>ผ่าน</b>
            </li>
          </ul>
        </div>

        <div>
          <h2 className="text-lg font-bold mb-4 border-b pb-2">
            ตัวชี้วัดหลัก (Realtime)
          </h2>
          <div className="flex gap-4">
            <div className="flex-1 p-4 border rounded-lg text-center">
              <p className="text-xs text-gray-500">องศาศอก</p>
              <p className="text-2xl font-bold">{stats.elbowAngle}°</p>
            </div>
            <div className="flex-1 p-4 border rounded-lg text-center">
              <p className="text-xs text-gray-500">หัวขยับ</p>
              <p className="text-2xl font-bold text-red-500">
                {stats.headMovement} cm
              </p>
            </div>
          </div>
        </div>

        <div className="flex-1 flex flex-col">
          <h2 className="text-lg font-bold mb-2">กราฟความนิ่งแขน</h2>
          <div className="flex-1 border-2 border-dashed rounded-lg bg-gray-50 flex items-center justify-center text-gray-400">
            [ กราฟ Recharts ]
          </div>
        </div>
      </aside>
    </div>
  );
}
