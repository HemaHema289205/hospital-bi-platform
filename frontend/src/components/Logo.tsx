// Brand mark: blue heart with a white pulse line. It reads on both the light
// sidebar and the navy panels, so it needs no background tile.
export default function Logo({ size = 40 }: { size?: number }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} className="shrink-0" aria-hidden="true">
      <defs>
        <linearGradient id="hf-logo-fill" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#4a90ff" />
          <stop offset="1" stopColor="#1552bd" />
        </linearGradient>
      </defs>
      <path
        d="M12 21.3 3.6 13.2C1.4 11 1.2 7.4 3.3 5.2 5.4 3 8.9 3 11 5.2l1 1 1-1c2.1-2.2 5.6-2.2 7.7 0 2.1 2.2 1.9 5.8-.3 8L12 21.3Z"
        fill="url(#hf-logo-fill)"
      />
      <path
        d="M1.5 12.5h6l1.6-3.2 2.6 6.2 2.6-8.5 2.1 5.5h6.1"
        fill="none"
        stroke="#ffffff"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
