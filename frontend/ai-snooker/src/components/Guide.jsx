export function Guide({ exercise }) {
  const lesson = exercise?.lesson;
  if (!lesson) return null;
  const fraction = exercise.setup?.fraction ?? 1;
  return (
    <section className="panel guide">
      <h2>เป้าหมายและขั้นตอนฝึก</h2>
      <p>{lesson.goal}</p>
      <p className="notice">{lesson.camera}</p>
      <svg
        viewBox="0 0 440 170"
        className="lesson-diagram"
        role="img"
        aria-label={
          exercise.module_id === 3
            ? `ภาพแนวคิดการกระทบเหลี่ยม ${fraction}`
            : exercise.module_id === 2
              ? "ภาพแบบฝึกน้ำเงินผ่านช่องแดงสองแถว"
              : "ภาพตำแหน่งกล้องด้านข้างสำหรับฝึกท่าทาง"
        }
      >
        {exercise.module_id === 2 ? (
          <>
            <rect x="10" y="10" width="420" height="150" rx="9" fill="#e8eeeb" />
            {[0, 1, 2].map((n) => (
              <g key={n}>
                {[45, 125].map((y) => (
                  <circle key={y} cx={170 + n * 30} cy={y} r="15" fill="#b65050" />
                ))}
                <text x={170 + n * 30} y="20" textAnchor="middle" fontSize="12">
                  {n + 1}
                </text>
              </g>
            ))}
            <line x1="230" y1="25" x2="230" y2="145" stroke="#ca9020" strokeDasharray="5 4" />
            <circle cx="170" cy="85" r="15" fill="#2463ce" stroke="#798392" />
            <path d="M30 85H150 M190 85H335" stroke="#798392" strokeWidth="4" />
            <text x="220" y="158" textAnchor="middle" fontSize="11">
              น้ำเงินผ่านช่องแดง หัวคิวส่งถึงแนวคู่ที่ 3
            </text>
          </>
        ) : exercise.module_id === 3 ? (
          <>
            <rect x="10" y="10" width="420" height="150" rx="9" fill="#e8eeeb" stroke="#abb9b0" />
            <circle cx="310" cy="85" r="25" fill="#b65050" />
            <line
              x1="60"
              y1={85 + 50 * (1 - fraction)}
              x2="265"
              y2={85 + 50 * (1 - fraction)}
              stroke="#566a60"
              strokeDasharray="7 5"
            />
            <circle cx="110" cy={85 + 50 * (1 - fraction)} r="25" fill="#2463ce" stroke="#9eaaa3" />
            <text x="205" y="146" textAnchor="middle" fontSize="12">
              ภาพแนวคิด ไม่ใช่ตำแหน่งตั้งลูกที่สอบเทียบ
            </text>
          </>
        ) : (
          <>
            <path d="M60 130H390" stroke="#9eaaa3" strokeWidth="5" />
            <circle cx="245" cy="42" r="15" fill="#e2e5ea" stroke="#798392" />
            <path
              d="M230 55L150 75L128 127 M182 68L216 97L292 112 M160 75L190 130"
              fill="none"
              stroke="#798392"
              strokeWidth="8"
              strokeLinecap="round"
            />
            <path d="M185 116L360 116" stroke="#a28c6c" strokeWidth="5" />
            <rect x="30" y="45" width="40" height="28" rx="3" fill="#dde2e9" stroke="#798392" />
            <path
              d="M70 50L88 40V78L70 68 M48 74V130"
              fill="none"
              stroke="#798392"
              strokeWidth="3"
            />
            <text x="240" y="160" textAnchor="middle" fontSize="12">
              กล้องด้านข้างต้องเห็นจุดร่างกายและแนวคิวครบ
            </text>
          </>
        )}
      </svg>
      <ol>
        {lesson.steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      <p className="muted">ถ้าข้อมูลไม่ครบให้จัดอุปกรณ์ใหม่ ผลที่ประเมินไม่ได้จะไม่ถูกแทนเป็น 0</p>
    </section>
  );
}
