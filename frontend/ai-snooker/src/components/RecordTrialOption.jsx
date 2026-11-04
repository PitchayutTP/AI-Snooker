export function RecordTrialOption({ config, setConfig, setPrepared, disabled }) {
  return (
    <p>
      <label>
        <input
          type="checkbox"
          checked={Boolean(config.record_frames)}
          disabled={disabled}
          onChange={(event) => {
            setConfig({ ...config, record_frames: event.target.checked });
            setPrepared("");
          }}
        />{" "}
        บันทึกคลิปของแต่ละครั้งฝึกในรอบนี้
      </label>
    </p>
  );
}
