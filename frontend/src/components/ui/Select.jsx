export default function Select({ className = "", children, ...props }) {
  return (
    <select
      className={`ops-select w-full rounded-md border ${className}`}
      {...props}
    >
      {children}
    </select>
  );
}
