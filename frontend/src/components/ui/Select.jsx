export default function Select({ className = "", children, ...props }) {
  return (
    <select
      className={`ops-select w-full rounded-md border px-2.5 py-1.5 text-sm ${className}`}
      {...props}
    >
      {children}
    </select>
  );
}
