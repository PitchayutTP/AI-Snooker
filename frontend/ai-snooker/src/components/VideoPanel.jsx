import React from "react";
import Button from "./Button";

export default function VideoPanel() {
  return (
    <div className="flex-1 flex flex-col w-full h-full bg-black rounded-xl overflow-hidden relative shadow-inner">
      <div className="absolute inset-0 flex items-center justify-center text-gray-500">
        <span>[ พื้นที่แสดงผลภาพสดจากกล้อง WebCam ]</span>
      </div>
      <div className="absolute bottom-6 left-0 right-0 flex justify-center gap-4">
        <Button variant="primary">▶️ เริ่มเก็บสถิติ</Button>
        <Button variant="danger">⏹️ จบการซ้อม</Button>
      </div>
    </div>
  );
}
