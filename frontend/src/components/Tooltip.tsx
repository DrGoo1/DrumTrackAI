import React, { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

export function Tooltip({
  content,
  children,
  maxWidthClassName = "w-72",
  placement = "bottom",
  wrapperClassName = "",
  wrapperStyle,
}: {
  content: React.ReactNode;
  children: React.ReactNode;
  maxWidthClassName?: string;
  placement?: "bottom" | "top";
  wrapperClassName?: string;
  wrapperStyle?: React.CSSProperties;
}) {
  const wrapRef = useRef<HTMLSpanElement | null>(null);
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);

  const yOffset = 6;

  const computePos = () => {
    const el = wrapRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const left = Math.max(8, Math.min(window.innerWidth - 8, r.left));
    const top = placement === "top" ? r.top - yOffset : r.bottom + yOffset;
    setPos({ left, top });
  };

  useEffect(() => {
    if (!open) return;
    computePos();
    const onScroll = () => computePos();
    const onResize = () => computePos();
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", onResize);
    };
  }, [open, placement]);

  const portalTarget = useMemo(() => {
    if (typeof document === "undefined") return null;
    return document.body;
  }, []);

  return (
    <span
      ref={wrapRef}
      className={"relative inline-flex items-center " + wrapperClassName}
      style={wrapperStyle}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {children}
      {open && pos && portalTarget
        ? createPortal(
            <span
              className={
                "pointer-events-none fixed left-0 top-0 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-[11px] text-slate-200 shadow-xl z-[9999] " +
                maxWidthClassName
              }
              style={{ transform: `translate(${Math.round(pos.left)}px, ${Math.round(pos.top)}px)` }}
            >
              {content}
            </span>,
            portalTarget
          )
        : null}
    </span>
  );
}
