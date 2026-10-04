export async function api(path, body) {
  const response = await fetch(`/api${path}`, {
    method: body === undefined ? "GET" : "POST",
    credentials: "same-origin",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith("/auth/"))
      window.dispatchEvent(new Event("auth-expired"));
    const message =
      typeof data.detail === "string"
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail.map((x) => x.msg).join(" / ")
          : `เกิดข้อผิดพลาด (${response.status})`;
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return data;
}
export const number = (value) =>
  value == null || !Number.isFinite(Number(value))
    ? "—"
    : Number(value).toFixed(2);
export const date = (value) =>
  value
    ? new Date(
        value.endsWith("Z") || /[+-]\d\d:\d\d$/.test(value)
          ? value
          : `${value}Z`,
      ).toLocaleString("th-TH")
    : "—";
export const names = {
  PASS: "ผ่าน",
  FAIL: "ไม่ผ่าน",
  INVALID: "ประเมินไม่ได้",
  ABORTED: "ยกเลิก",
  COMPLETED: "เสร็จสิ้น",
  IN_PROGRESS: "กำลังฝึก",
};
