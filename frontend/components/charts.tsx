"use client";
/** Recharts wrappers themed for the dark UI. */
import {
  Bar, BarChart, Cell, Funnel, FunnelChart, LabelList, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const PALETTE = ["#6366f1", "#38bdf8", "#34d399", "#f59e0b", "#f43f5e", "#a78bfa"];
const tooltipStyle = {
  contentStyle: { background: "#16161a", border: "1px solid #27272a", borderRadius: 8, fontSize: 12 },
  itemStyle: { color: "#e4e4e7" }, labelStyle: { color: "#a1a1aa" },
};

export function SimpleBar({ data, x, y, color = "#6366f1" }: {
  data: Record<string, string | number>[]; x: string; y: string; color?: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data}>
        <XAxis dataKey={x} stroke="#a1a1aa" fontSize={11} tickLine={false} axisLine={false} />
        <YAxis stroke="#a1a1aa" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
        <Tooltip {...tooltipStyle} cursor={{ fill: "#27272a55" }} />
        <Bar dataKey={y} radius={[6, 6, 0, 0]} fill={color} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function DonutChart({ data, nameKey, valueKey }: {
  data: Record<string, string | number>[]; nameKey: string; valueKey: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie data={data} dataKey={valueKey} nameKey={nameKey} innerRadius={55} outerRadius={85} paddingAngle={3}>
          {data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} stroke="none" />)}
        </Pie>
        <Tooltip {...tooltipStyle} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function LeadFunnel({ data }: { data: { stage: string; count: number }[] }) {
  const colored = data.map((d, i) => ({ ...d, fill: PALETTE[i % PALETTE.length] }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <FunnelChart>
        <Tooltip {...tooltipStyle} />
        <Funnel dataKey="count" data={colored} isAnimationActive>
          <LabelList position="right" dataKey="stage" fill="#e4e4e7" stroke="none" fontSize={12} />
        </Funnel>
      </FunnelChart>
    </ResponsiveContainer>
  );
}

export function ImpactBars({ drivers }: {
  drivers: { feature: string; impact: number; direction: string }[];
}) {
  const data = drivers.map((d) => ({ ...d, abs: Math.abs(d.impact) }));
  return (
    <ResponsiveContainer width="100%" height={Math.max(180, data.length * 34)}>
      <BarChart data={data} layout="vertical" margin={{ left: 40 }}>
        <XAxis type="number" hide />
        <YAxis type="category" dataKey="feature" width={160} stroke="#a1a1aa" fontSize={11} tickLine={false} axisLine={false} />
        <Tooltip {...tooltipStyle} cursor={{ fill: "#27272a55" }} />
        <Bar dataKey="abs" radius={[0, 6, 6, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.direction === "positive" ? "#34d399" : "#f43f5e"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
