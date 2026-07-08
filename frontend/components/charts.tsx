"use client";
/** Recharts wrappers themed for the light UI. */
import {
  Bar,
  BarChart,
  Cell,
  Funnel,
  FunnelChart,
  LabelList,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const PALETTE = ["#6366f1", "#0284c7", "#059669", "#d97706", "#e11d48", "#7c3aed"];
const AXIS = "#64748b"; // slate-500
const tooltipStyle = {
  contentStyle: {
    background: "#ffffff",
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    fontSize: 12,
    boxShadow: "0 4px 12px rgba(15,23,42,0.08)",
  },
  itemStyle: { color: "#0f172a" },
  labelStyle: { color: "#475569" },
};

export function SimpleBar({
  data,
  x,
  y,
  color = "#6366f1",
}: {
  data: Record<string, string | number>[];
  x: string;
  y: string;
  color?: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data}>
        <XAxis dataKey={x} stroke={AXIS} fontSize={11} tickLine={false} axisLine={false} />
        <YAxis
          stroke={AXIS}
          fontSize={11}
          tickLine={false}
          axisLine={false}
          allowDecimals={false}
        />
        <Tooltip {...tooltipStyle} cursor={{ fill: "#f1f5f9" }} />
        <Bar dataKey={y} radius={[6, 6, 0, 0]} fill={color} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function DonutChart({
  data,
  nameKey,
  valueKey,
}: {
  data: Record<string, string | number>[];
  nameKey: string;
  valueKey: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={data}
          dataKey={valueKey}
          nameKey={nameKey}
          innerRadius={55}
          outerRadius={85}
          paddingAngle={3}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={PALETTE[i % PALETTE.length]} stroke="none" />
          ))}
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
          <LabelList position="right" dataKey="stage" fill="#334155" stroke="none" fontSize={12} />
        </Funnel>
      </FunnelChart>
    </ResponsiveContainer>
  );
}

export function ImpactBars({
  drivers,
}: {
  drivers: { feature: string; impact: number; direction: string }[];
}) {
  const data = drivers.map((d) => ({ ...d, abs: Math.abs(d.impact) }));
  return (
    <ResponsiveContainer width="100%" height={Math.max(180, data.length * 34)}>
      <BarChart data={data} layout="vertical" margin={{ left: 40 }}>
        <XAxis type="number" hide />
        <YAxis
          type="category"
          dataKey="feature"
          width={160}
          stroke={AXIS}
          fontSize={11}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip {...tooltipStyle} cursor={{ fill: "#f1f5f9" }} />
        <Bar dataKey="abs" radius={[0, 6, 6, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.direction === "positive" ? "#059669" : "#e11d48"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
