import type { SVGProps } from "react";

export type IconName =
  | "command"
  | "cases"
  | "issues"
  | "compare"
  | "replay"
  | "report"
  | "play"
  | "pause"
  | "restart"
  | "check"
  | "close"
  | "chevron"
  | "menu"
  | "sun"
  | "moon"
  | "monitor"
  | "shield"
  | "quote"
  | "copy"
  | "arrow-up"
  | "arrow-down"
  | "external"
  | "clock"
  | "spark"
  | "code"
  | "workflow"
  | "database"
  | "github"
  | "briefcase";

const PATHS: Record<IconName, string[]> = {
  command: ["M4 4h6v6H4z", "M14 4h6v6h-6z", "M4 14h6v6H4z", "M14 14h6v6h-6z"],
  cases: ["M4 5h5v14H4z", "M10 5h4v14h-4z", "M15 5h5v14h-5z"],
  issues: ["M12 3 2.8 20h18.4z", "M12 9v5", "M12 17.2v.1"],
  compare: ["M4 8h12", "M12 4l4 4-4 4", "M20 16H8", "M12 12l-4 4 4 4"],
  replay: ["M12 3a9 9 0 1 0 9 9", "M21 3v6h-6", "M10 8.5v7l6-3.5z"],
  report: ["M6 3h9l4 4v14H6z", "M14 3v5h5", "M9 12h6", "M9 16h6"],
  play: ["M8 5v14l11-7z"],
  pause: ["M8 5v14", "M16 5v14"],
  restart: ["M4 4v6h6", "M4.6 15a8 8 0 1 0 1.9-7.7L4 10"],
  check: ["M4 12.5 9 17.5 20 6.5"],
  close: ["M6 6l12 12", "M18 6 6 18"],
  chevron: ["M9 6l6 6-6 6"],
  menu: ["M4 7h16", "M4 12h16", "M4 17h16"],
  sun: ["M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z", "M12 2v2", "M12 20v2", "M2 12h2", "M20 12h2", "M4.9 4.9l1.4 1.4", "M17.7 17.7l1.4 1.4", "M19.1 4.9l-1.4 1.4", "M6.3 17.7l-1.4 1.4"],
  moon: ["M20 14.5A8.5 8.5 0 0 1 9.5 4 8.5 8.5 0 1 0 20 14.5z"],
  monitor: ["M3 5h18v11H3z", "M9 20h6", "M12 16v4"],
  shield: ["M12 3 4.5 6v6c0 4.4 3.2 7.8 7.5 9 4.3-1.2 7.5-4.6 7.5-9V6z", "M8.8 12l2.2 2.2 4.4-4.4"],
  quote: ["M5 6h5v5H7c0 2 1 3.2 3 4l-1.5 2C5.5 15.5 5 13.4 5 11z", "M14 6h5v5h-3c0 2 1 3.2 3 4l-1.5 2c-3-1.5-3.5-3.6-3.5-6z"],
  copy: ["M8 8h11v11H8z", "M5 16V5h11"],
  "arrow-up": ["M12 19V5", "M6 11l6-6 6 6"],
  "arrow-down": ["M12 5v14", "M6 13l6 6 6-6"],
  external: ["M14 4h6v6", "M20 4 10 14", "M18 14v5H5V6h5"],
  clock: ["M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z", "M12 7v5l3 2"],
  spark: ["M4 17l3-5 3 2 4-7 3 4 3-6"],
  code: ["m8 7-5 5 5 5", "m16 7 5 5-5 5", "m14 4-4 16"],
  workflow: ["M3 4h6v6H3z", "M15 14h6v6h-6z", "M9 7h5a4 4 0 0 1 4 4v3", "m15 11 3 3 3-3"],
  database: ["M20 6c0 2-3.6 3-8 3S4 8 4 6s3.6-3 8-3 8 1 8 3Z", "M4 6v12c0 2 3.6 3 8 3s8-1 8-3V6", "M4 12c0 2 3.6 3 8 3s8-1 8-3"],
  github: ["M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"],
  briefcase: ["M3 7h18v14H3z", "M8 7V3h8v4", "M3 12a20 20 0 0 0 18 0", "M12 11v4"],
};

export interface IconProps extends Omit<SVGProps<SVGSVGElement>, "name"> {
  name: IconName;
  size?: number;
}

export function Icon({ name, size = 16, ...rest }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {PATHS[name].map((d) => (
        <path key={d} d={d} />
      ))}
    </svg>
  );
}
