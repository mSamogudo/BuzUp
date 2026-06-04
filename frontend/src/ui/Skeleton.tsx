export function SkeletonText({ lines = 3, width }: { lines?: number; width?: string }) {
  return (
    <div className="skeleton-group">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="skeleton skeleton-text" style={i === lines - 1 ? { width: width || "60%" } : undefined} />
      ))}
    </div>
  );
}

export function SkeletonCard({ count = 4 }: { count?: number }) {
  return (
    <div className="admin-metric-grid">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton skeleton-card" />
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="skeleton-table">
      <div className="skeleton skeleton-text" style={{ width: "30%", marginBottom: 16 }} />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton-table-row">
          {Array.from({ length: cols }).map((_, j) => (
            <div key={j} className="skeleton skeleton-text" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function SkeletonAvatar({ size = 36 }: { size?: number }) {
  return <div className="skeleton skeleton-avatar" style={{ width: size, height: size }} />;
}
