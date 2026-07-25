import React from "react";
import Button from "../components/Button";

export default function Dashboard({ onStartTraining }) {
  const modules = [
    {
      id: 1,
      title: "บทที่ 1: การยืน",
      status: "passed",
      stars: "⭐⭐⭐",
      desc: "การจัดระเบียบร่างกาย",
    },
    {
      id: 2,
      title: "บทที่ 2: การส่งคิว",
      status: "unlocked",
      stars: "ยังไม่มี",
      desc: "The Delivery",
    },
    {
      id: 3,
      title: "บทที่ 3: Basic Pot",
      status: "locked",
      desc: "ต้องผ่านด่าน 2 ก่อน",
    },
    {
      id: 4,
      title: "บทที่ 4: Escape",
      status: "locked",
      desc: "ต้องผ่านด่าน 3 ก่อน",
    },
  ];

  return (
    <div className="max-w-5xl mx-auto p-6 pt-10 min-h-screen">
      <header className="flex justify-between items-center mb-10 pb-4 border-b">
        <h1 className="text-xl font-bold">👤 Dashboard</h1>
        <div className="font-bold text-gray-600">⭐ รวม: 3 ดาว</div>
      </header>

      <h2 className="text-2xl font-bold text-center mb-8">
        เลือกบทเรียน (Modules)
      </h2>

      <div className="grid grid-cols-2 gap-6">
        {modules.map((mod) => (
          <div
            key={mod.id}
            className={`p-6 border rounded-xl flex flex-col ${mod.status === "locked" ? "bg-gray-50 opacity-60" : "bg-white shadow-sm"}`}
          >
            <h3 className="text-lg font-bold mb-2">{mod.title}</h3>
            <p className="text-gray-500 text-sm mb-4">{mod.desc}</p>

            {mod.status === "passed" && (
              <span className="text-green-600 font-bold mb-4">
                🟢 ผ่านแล้ว ({mod.stars})
              </span>
            )}
            {mod.status === "unlocked" && (
              <span className="text-yellow-600 font-bold mb-4">
                🟡 ปลดล็อกแล้ว
              </span>
            )}
            {mod.status === "locked" && (
              <span className="text-red-500 font-bold mb-4">🔴 ล็อก</span>
            )}

            <div className="mt-auto">
              {mod.status === "unlocked" ? (
                <Button onClick={onStartTraining} className="w-full">
                  เริ่มบทเรียน
                </Button>
              ) : (
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => mod.status === "passed" && onStartTraining()}
                >
                  {mod.status === "locked" ? "🔒 ล็อก" : "ฝึกซ้อมอีกครั้ง"}
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
