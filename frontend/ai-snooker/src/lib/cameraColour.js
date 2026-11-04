// Map clicks to the visible image, including object-fit: contain letterboxing.
export const DEFAULT_BALL_COLOURS = {
  cue_ball: [
    { lower: [0, 0, 100], upper: [179, 85, 255] },
    { lower: [10, 0, 100], upper: [40, 150, 255] },
  ],
  target_ball: [
    { lower: [0, 110, 70], upper: [10, 255, 255] },
    { lower: [170, 110, 70], upper: [179, 255, 255] },
  ],
};
export const BLUE_BALL_RANGES = [{ lower: [95, 70, 45], upper: [135, 255, 255] }];
export const M3_BALL_COLOURS = { ...DEFAULT_BALL_COLOURS, cue_ball: BLUE_BALL_RANGES };
export function blueBallRanges(hsv) {
  validateBallColour("cue_ball", hsv, "BLUE");
  const [h, s, v] = hsv;
  return [
    {
      lower: [Math.max(95, h - 12), Math.max(60, s - 110), Math.max(35, v - 120)],
      upper: [Math.min(135, h + 12), 255, 255],
    },
  ];
}
export function imagePoint(rect, width, height, clientX, clientY) {
  const scale = Math.min(rect.width / width, rect.height / height);
  if (!(scale > 0)) throw new Error("ภาพยังไม่พร้อม");
  const x = (clientX - rect.left - (rect.width - width * scale) / 2) / scale;
  const y = (clientY - rect.top - (rect.height - height * scale) / 2) / scale;
  if (x < 0 || y < 0 || x >= width || y >= height) throw new Error("คลิกภายในเนื้อภาพกล้อง");
  return [Math.floor(x), Math.floor(y)];
}
export function rgbToHsv(r, g, b) {
  r /= 255;
  g /= 255;
  b /= 255;
  const max = Math.max(r, g, b),
    min = Math.min(r, g, b),
    d = max - min;
  let h = 0;
  if (d) h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [
    Math.round(((h * 60 + 360) % 360) / 2) % 180,
    Math.round(max ? (d / max) * 255 : 0),
    Math.round(max * 255),
  ];
}
export function ranges([h, s, v], white = false, ball = false) {
  // Neutral white and warm ivory have separate saturation limits. Raising the
  // limit for every hue would also admit the green cloth or coloured balls.
  if (white) {
    const lowV = Math.max(90, v - 110);
    return [
      { lower: [0, 0, lowV], upper: [179, Math.min(100, Math.max(85, s + 40)), 255] },
      { lower: [10, 0, lowV], upper: [40, Math.min(150, Math.max(120, s + 50)), 255] },
    ];
  }
  const lowS = ball ? Math.max(70, s - 100) : Math.max(35, s - 65),
    lowV = ball ? Math.max(35, v - 120) : Math.max(25, v - 80),
    lo = h - 10,
    hi = h + 10;
  if (lo < 0)
    return [
      { lower: [0, lowS, lowV], upper: [hi, 255, 255] },
      { lower: [180 + lo, lowS, lowV], upper: [179, 255, 255] },
    ];
  if (hi > 179)
    return [
      { lower: [lo, lowS, lowV], upper: [179, 255, 255] },
      { lower: [0, lowS, lowV], upper: [hi - 180, 255, 255] },
    ];
  return [{ lower: [lo, lowS, lowV], upper: [hi, 255, 255] }];
}
export function hsvAt(image, event) {
  const [x, y] = imagePoint(
    image.getBoundingClientRect(),
    image.naturalWidth,
    image.naturalHeight,
    event.clientX,
    event.clientY,
  );
  const left = Math.max(0, x - 2),
    top = Math.max(0, y - 2),
    w = Math.min(5, image.naturalWidth - left),
    h = Math.min(5, image.naturalHeight - top);
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(image, left, top, w, h, 0, 0, w, h);
  const pixels = ctx.getImageData(0, 0, w, h).data,
    channels = [[], [], []];
  for (let i = 0; i < pixels.length; i += 4)
    for (let c = 0; c < 3; c++) channels[c].push(pixels[i + c]);
  const rgb = channels.map((a) => a.sort((a, b) => a - b)[Math.floor(a.length / 2)]);
  return { xy: [x, y], hsv: rgbToHsv(...rgb) };
}
export function validateBallColour(role, [h, s, v], cueColour = "WHITE") {
  if (role === "cue_ball" && cueColour === "BLUE") {
    if (h < 95 || h > 135 || s < 60 || v < 45)
      throw new Error("เลือกส่วนสีน้ำเงินของลูกน้ำเงิน หลีกเลี่ยงจุดสะท้อน เงามืด และผ้าโต๊ะ");
    return;
  }
  if (role === "target_ball" && (s < 70 || v < 35 || (h > 15 && h < 165)))
    throw new Error("เลือกรอยสีแดงบนลูกแดง หลีกเลี่ยงจุดสะท้อนสีขาวและผ้าโต๊ะ");
  if (role === "cue_ball" && (v < 100 || (s > 100 && !(h >= 10 && h <= 40 && s <= 150))))
    throw new Error(
      "เลือกบริเวณสีขาวหรือครีมอมเหลืองของลูกขาว หลีกเลี่ยงเงามืด ผ้าเขียว และสีเหลืองเข้ม",
    );
}
