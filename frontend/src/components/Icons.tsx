// Line icons drawn for this page, in the ledger's ink. Decorative: always paired with visible text.
type P = { size?: number };
const base = (size: number) => ({ width: size, height: size, viewBox: "0 0 48 48", fill: "none", stroke: "currentColor", strokeWidth: 2.2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true });

export function Coins({ size = 48 }: P) {
  return (
    <svg {...base(size)}>
      <ellipse cx="18" cy="14" rx="11" ry="4.5" />
      <path d="M7 14v6c0 2.5 4.9 4.5 11 4.5s11-2 11-4.5v-6" />
      <path d="M7 20v6c0 2.5 4.9 4.5 11 4.5" />
      <ellipse cx="31" cy="30" rx="11" ry="4.5" />
      <path d="M20 30v6c0 2.5 4.9 4.5 11 4.5s11-2 11-4.5v-6" />
      <path d="M36 9l5 3-5 3M41 12H30" />
    </svg>
  );
}

export function Database({ size = 48 }: P) {
  return (
    <svg {...base(size)}>
      <ellipse cx="24" cy="10" rx="14" ry="5" />
      <path d="M10 10v28c0 2.8 6.3 5 14 5s14-2.2 14-5V10" />
      <path d="M10 19c0 2.8 6.3 5 14 5s14-2.2 14-5M10 28.5c0 2.8 6.3 5 14 5s14-2.2 14-5" />
      <path d="M31 38l3 3 6-7" />
    </svg>
  );
}

export function Law({ size = 48 }: P) {
  return (
    <svg {...base(size)}>
      <path d="M24 6v34M14 40h20" />
      <path d="M10 13h28" />
      <path d="M13 13l-6 13h12l-6-13zM35 13l-6 13h12l-6-13z" />
      <circle cx="24" cy="8" r="2.2" />
    </svg>
  );
}

export function Ticket({ size = 48 }: P) {
  return (
    <svg {...base(size)}>
      <path d="M11 6h20l7 7v29H11z" />
      <path d="M31 6v7h7M17 20h15M17 26h15M17 32h9" />
    </svg>
  );
}

export function AI({ size = 48 }: P) {
  return (
    <svg {...base(size)}>
      <rect x="9" y="12" width="30" height="24" rx="5" />
      <path d="M24 6v6M16 42h16M24 36v6" />
      <circle cx="18" cy="23" r="2.5" />
      <circle cx="30" cy="23" r="2.5" />
      <path d="M18 30h12" />
    </svg>
  );
}

export function Check({ size = 48 }: P) {
  return (
    <svg {...base(size)}>
      <path d="M8 8h24v32H8z" />
      <path d="M13 16l3 3 5-6M13 27l3 3 5-6M24 16h4M24 27h4" />
      <circle cx="35" cy="34" r="7" />
      <path d="M40 39l4 4" />
    </svg>
  );
}

export const ICONS: Record<string, (p: P) => JSX.Element> = { coins: Coins, database: Database, law: Law, ticket: Ticket, ai: AI, check: Check };

export function Icon({ name, size }: { name: string; size?: number }) {
  const C = ICONS[name] ?? Ticket;
  return <C size={size} />;
}
