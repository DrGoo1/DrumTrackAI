declare module 'lucide-react' {
  import * as React from 'react';

  export type LucideProps = React.SVGProps<SVGSVGElement> & {
    size?: string | number;
    absoluteStrokeWidth?: boolean;
  };

  export type LucideIcon = React.FC<LucideProps>;

  export const Activity: LucideIcon;
  export const ArrowRight: LucideIcon;
  export const ClipboardList: LucideIcon;
  export const Gauge: LucideIcon;
  export const Headphones: LucideIcon;
  export const RefreshCcw: LucideIcon;
  export const Save: LucideIcon;
  export const Sparkles: LucideIcon;
  export const Users: LucideIcon;
}
