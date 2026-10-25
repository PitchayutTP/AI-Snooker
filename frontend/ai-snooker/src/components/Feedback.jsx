export function Feedback({ items = [] }) {
  return (
    <ul className="feedback">
      {items.map((item, i) => (
        <li className={item.level} key={`${item.metric}-${i}`}>
          {item.message}
        </li>
      ))}
    </ul>
  );
}

