import React, { useEffect, useMemo, useState } from "react";
// Uses TailwindCSS + recharts + shadcn/ui
// Default export component for a single-file dashboard prototype (TypeScript)

import {
  PieChart,
  Pie,
  Cell,
  Tooltip as ReTooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  LineChart,
  Line,
  LabelList,
} from "recharts";

// Example shadcn components (optional) - adapt to your project setup
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const PASS_COLOR = "#10B981"; // green
const FAIL_COLOR = "#EF4444"; // red
const PALETTE = [
  "#60A5FA",
  "#7C3AED",
  "#F59E0B",
  "#06B6D4",
  "#F97316",
  "#F43F5E",
] as const;

// === Types ===

export type DeviceStatus = "Pass" | "Fail";

export interface DeviceRecord {
  id: number;
  name: string;
  region: string;
  country: string;
  productType: string;
  deviceType: string;
  status: DeviceStatus;
  /** ISO date string: YYYY-MM-DD */
  lastSeen: string;
}

export type DimensionField = "region" | "country" | "productType" | "deviceType";
export type BarCategory = "deviceType" | "productType" | "country" | "region";
export type TrendCategory = "country" | "region" | "productType" | "deviceType";
export type TrendGranularity = "daily" | "weekly" | "monthly";

interface SliceSelection {
  dim: DimensionField;
  key: string;
  status: DeviceStatus | null;
}

interface BarSelection {
  categoryValue: string;
  status: DeviceStatus | null;
}

export interface DeviceComplianceResponse {
  devices: DeviceRecord[];
}

// Sample mock dataset. In production, this will be replaced by API data.
const MOCK_DEVICES: DeviceRecord[] = (() => {
  const regions = ["EMEA", "APAC", "AMER"] as const;
  const countries = ["UK", "Germany", "India", "USA", "Canada"] as const;
  const productTypes = ["Product A", "Product B"] as const;
  const deviceTypes = ["Type1", "Type2", "Type3", "Type4"] as const;
  const rows: DeviceRecord[] = [];
  let id = 1;
  // distribute lastSeen dates across the past 120 days
  const now = Date.now();
  for (let i = 0; i < 250; i++) {
    const region = regions[Math.floor(Math.random() * regions.length)];
    const country = countries[Math.floor(Math.random() * countries.length)];
    const productType =
      productTypes[Math.floor(Math.random() * productTypes.length)];
    const deviceType =
      deviceTypes[Math.floor(Math.random() * deviceTypes.length)];
    const passed = Math.random() > 0.35; // ~65% pass
    const daysAgo = Math.floor(Math.random() * 120);
    const lastSeen = new Date(now - daysAgo * 24 * 60 * 60 * 1000)
      .toISOString()
      .slice(0, 10);
    rows.push({
      id: id++,
      name: `Device-${id}`,
      region,
      country,
      productType,
      deviceType,
      status: passed ? "Pass" : "Fail",
      lastSeen,
    });
  }
  return rows;
})();

function formatPeriod(dateObj: Date, granularity: TrendGranularity): string {
  const y = dateObj.getFullYear();
  const m = String(dateObj.getMonth() + 1).padStart(2, "0");
  const d = String(dateObj.getDate()).padStart(2, "0");
  if (granularity === "daily") return `${y}-${m}-${d}`;
  if (granularity === "monthly") return `${y}-${m}`;
  // weekly -> ISO week-ish label (YYYY-Wxx)
  const onejan = new Date(dateObj.getFullYear(), 0, 1);
  const week = Math.ceil(
    ((dateObj.getTime() - onejan.getTime()) / 86400000 + onejan.getDay() + 1) /
      7,
  );
  return `${y}-W${String(week).padStart(2, "0")}`;
}

const RADIAN = Math.PI / 180;
const renderPieLabel = (props: any) => {
  const { cx, cy, midAngle, innerRadius, outerRadius, percent } = props;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  const pct = (percent * 100).toFixed(0);
  if (pct === "0") return null;
  return (
    <text
      x={x}
      y={y}
      fill="#111827"
      textAnchor="middle"
      dominantBaseline="central"
      fontSize={12}
    >
      {pct}%
    </text>
  );
};

function downloadCSV(rows: DeviceRecord[], filename = "export.csv"): void {
  if (!rows || rows.length === 0) return;

  // Use a fixed, stable column set matching the Details table
  const columns: { key: keyof DeviceRecord; header: string }[] = [
    { key: "id", header: "ID" },
    { key: "name", header: "Name" },
    { key: "region", header: "Region" },
    { key: "country", header: "Country" },
    { key: "productType", header: "Product" },
    { key: "deviceType", header: "Device Type" },
    { key: "status", header: "Status" },
    { key: "lastSeen", header: "Last Seen" },
  ];

  const header = columns.map((c) => c.header).join(",");
  const body = rows.map((r) =>
    columns
      .map((c) => {
        const value = r[c.key] ?? "";
        // JSON.stringify handles escaping quotes/commas and wraps in quotes
        return JSON.stringify(value);
      })
      .join(","),
  );

  // Join lines with a proper newline string
  const csv = [header, ...body].join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// Suggested API endpoint contract (example)
// GET /api/device-compliance?from=YYYY-MM-DD&to=YYYY-MM-DD&region=EMEA&country=Canada&productType=Product%20A&deviceType=Type1
// Response body (JSON): DeviceComplianceResponse
// {
//   "devices": DeviceRecord[]
// }

export default function DeviceComplianceDashboard(): JSX.Element {
  // all devices currently loaded (initially mock data, replaced by API call)
  const [devices, setDevices] = useState<DeviceRecord[]>(MOCK_DEVICES);

  const [dimension, setDimension] = useState<DimensionField>("region"); // pie chart dimension
  const [barCategory, setBarCategory] = useState<BarCategory>("deviceType"); // categorical axis for bar chart
  const [selectedSlice, setSelectedSlice] = useState<SliceSelection | null>(
    null,
  );
  const [selectedBar, setSelectedBar] = useState<BarSelection | null>(null);
  const [filters, setFilters] = useState<{
    region: string;
    country: string;
    productType: string;
    deviceType: string;
  }>({ region: "All", country: "All", productType: "All", deviceType: "All" });

  // trend-specific state
  const [trendCategory, setTrendCategory] = useState<TrendCategory>("country");
  const [trendCategoryValue, setTrendCategoryValue] = useState<string>("All");
  const [trendMonths, setTrendMonths] = useState<number>(3);
  const [trendGranularity, setTrendGranularity] =
    useState<TrendGranularity>("daily");
  const [selectedPeriod, setSelectedPeriod] = useState<string | null>(null); // string period like '2025-11-01' or '2025-11'

  // === Example API integration ===
  // Replace the URL with your real backend endpoint.
  useEffect(() => {
    async function loadDevices() {
      try {
        const params = new URLSearchParams({
          from: "2025-01-01", // TODO: wire to UI-controlled date range
          to: new Date().toISOString().slice(0, 10),
        });
        const res = await fetch(`/api/device-compliance?${params.toString()}`);
        if (!res.ok) {
          console.error(
            "Failed to load device compliance data",
            res.statusText,
          );
          return;
        }
        const data: DeviceComplianceResponse = await res.json();
        if (Array.isArray(data.devices)) {
          setDevices(data.devices);
        }
      } catch (err) {
        console.error("Error loading device compliance data", err);
      }
    }

    // Uncomment this in real app when backend is ready
    // loadDevices();
  }, []);

  // helper to apply global filters to dataset
  const filteredDevices = useMemo(() => {
    return devices.filter((d) => {
      return (
        (filters.region === "All" || d.region === filters.region) &&
        (filters.country === "All" || d.country === filters.country) &&
        (filters.productType === "All" || d.productType === filters.productType) &&
        (filters.deviceType === "All" || d.deviceType === filters.deviceType)
      );
    });
  }, [devices, filters]);

  // Build pie data based on chosen dimension
  const pieData = useMemo(() => {
    const map = new Map<string, number>();
    for (const d of filteredDevices) {
      const key = d[dimension];
      map.set(key, (map.get(key) ?? 0) + 1);
    }
    return Array.from(map.entries()).map(([name, value], i) => ({
      name,
      value,
      color: PALETTE[i % PALETTE.length],
    }));
  }, [filteredDevices, dimension]);

  // Build stacked bar data grouped by category (deviceType default)
  const barData = useMemo(() => {
    const categories = Array.from(
      new Set(filteredDevices.map((d) => d[barCategory])),
    )
      .filter(Boolean)
      .sort();
    const result = categories.map((c) => ({
      category: String(c),
      Pass: 0,
      Fail: 0,
    }));
    const indexByCat: Record<string, number> = Object.fromEntries(
      result.map((r, i) => [r.category, i]),
    );
    for (const d of filteredDevices) {
      const cat = String(d[barCategory]);
      const idx = indexByCat[cat];
      if (idx === undefined) continue;
      if (d.status === "Pass") result[idx].Pass += 1;
      else result[idx].Fail += 1;
    }
    const withRates = result.map((r) => {
      const total = r.Pass + r.Fail;
      const passRate = total === 0 ? 0 : (r.Pass / total) * 100;
      return { ...r, total, passRate };
    });
    return withRates;
  }, [filteredDevices, barCategory]);

  // table rows to show when clicking segments
  const tableRows = useMemo(() => {
    if (selectedSlice) {
      // selectedSlice = {dim, key, status}
      return filteredDevices.filter(
        (d) =>
          d[selectedSlice.dim] === selectedSlice.key &&
          (!selectedSlice.status || d.status === selectedSlice.status),
      );
    }
    if (selectedBar) {
      // selectedBar = {categoryValue, status}
      return filteredDevices.filter(
        (d) =>
          d[barCategory] === selectedBar.categoryValue &&
          (!selectedBar.status || d.status === selectedBar.status),
      );
    }
    // if a period is selected from trend chart, show those rows
    if (selectedPeriod) {
      return filteredDevices.filter((d) => {
        if (
          trendCategoryValue !== "All" &&
          d[trendCategory] !== trendCategoryValue
        )
          return false;
        const dt = new Date(`${d.lastSeen}T00:00:00Z`);
        const per = formatPeriod(dt, trendGranularity);
        return per === selectedPeriod;
      });
    }
    return [];
  }, [
    selectedSlice,
    selectedBar,
    filteredDevices,
    barCategory,
    selectedPeriod,
    trendCategory,
    trendCategoryValue,
    trendGranularity,
  ]);

  const clearSelection = (): void => {
    setSelectedSlice(null);
    setSelectedBar(null);
    setSelectedPeriod(null);
  };

  // handlers
  const onPieClick = (data: any, _index: number): void => {
    if (!data) return;
    if (selectedSlice && selectedSlice.key === data.name && !selectedSlice.status) {
      setSelectedSlice(null);
    } else {
      setSelectedSlice({ dim: dimension, key: data.name, status: null });
      setSelectedBar(null);
      setSelectedPeriod(null);
    }
  };

  // TREND DATA: build timeseries for selected category/value
  const trendOptions: TrendCategory[] = [
    "country",
    "region",
    "productType",
    "deviceType",
  ];

  const trendCategoryValues = useMemo(() => {
    const values = Array.from(new Set(devices.map((d) => d[trendCategory]))).sort();
    return ["All", ...values];
  }, [devices, trendCategory]);

  const trendSeries = useMemo(() => {
    // compute window start date
    const now = new Date();
    const start = new Date();
    start.setUTCDate(start.getUTCDate() - Math.max(1, trendMonths * 30)); // approx months -> days

    // filter devices by global filters and by category selection
    const pool = filteredDevices.filter((d) => {
      if (
        trendCategoryValue !== "All" &&
        d[trendCategory] !== trendCategoryValue
      )
        return false;
      const dt = new Date(`${d.lastSeen}T00:00:00Z`);
      return dt >= start && dt <= now;
    });

    const map = new Map<
      string,
      { Pass: number; Fail: number; total: number; period: string }
    >();

    // iterate periods from start to now depending on granularity
    const current = new Date(start);
    while (current <= now) {
      const period = formatPeriod(current, trendGranularity);
      if (!map.has(period)) {
        map.set(period, { Pass: 0, Fail: 0, total: 0, period });
      }
      if (trendGranularity === "daily")
        current.setUTCDate(current.getUTCDate() + 1);
      else if (trendGranularity === "weekly")
        current.setUTCDate(current.getUTCDate() + 7);
      else current.setUTCMonth(current.getUTCMonth() + 1);
    }

    for (const d of pool) {
      const dt = new Date(`${d.lastSeen}T00:00:00Z`);
      const period = formatPeriod(dt, trendGranularity);
      if (!map.has(period)) {
        map.set(period, { Pass: 0, Fail: 0, total: 0, period });
      }
      const entry = map.get(period)!;
      if (d.status === "Pass") entry.Pass += 1;
      else entry.Fail += 1;
      entry.total += 1;
    }

    // convert to array and compute pass rate
    const arr = Array.from(map.values())
      .sort((a, b) => (a.period > b.period ? 1 : -1))
      .map((e) => ({
        period: e.period,
        passCount: e.Pass,
        failCount: e.Fail,
        total: e.total,
        passRate: e.total === 0 ? 0 : (e.Pass / e.total) * 100,
      }));

    return arr;
  }, [
    filteredDevices,
    trendCategory,
    trendCategoryValue,
    trendMonths,
    trendGranularity,
  ]);

  // when user clicks a point (period) on the trend chart, show detailed records
  const handlePointClick = (data: any): void => {
    // Recharts may call this with various shapes; be defensive
    const period =
      data?.payload?.period ??
      data?.period ??
      (Array.isArray(data?.activePayload)
        ? data.activePayload[0]?.payload?.period
        : undefined);

    if (!period) return;

    setSelectedPeriod(period as string);
    setSelectedSlice(null);
    setSelectedBar(null);
  };

  // Build select options from all loaded devices
  const regions = useMemo(
    () => [
      "All",
      ...Array.from(new Set(devices.map((d) => d.region))).sort(),
    ],
    [devices],
  );
  const countries = useMemo(
    () => [
      "All",
      ...Array.from(new Set(devices.map((d) => d.country))).sort(),
    ],
    [devices],
  );
  const productTypes = useMemo(
    () => [
      "All",
      ...Array.from(new Set(devices.map((d) => d.productType))).sort(),
    ],
    [devices],
  );
  const deviceTypes = useMemo(
    () => [
      "All",
      ...Array.from(new Set(devices.map((d) => d.deviceType))).sort(),
    ],
    [devices],
  );

  const selectedRowsForDownload = useMemo(() => {
    if (!selectedPeriod) return [] as DeviceRecord[];
    return filteredDevices.filter((d) => {
      if (
        trendCategoryValue !== "All" &&
        d[trendCategory] !== trendCategoryValue
      )
        return false;
      const per = formatPeriod(
        new Date(`${d.lastSeen}T00:00:00Z`),
        trendGranularity,
      );
      return per === selectedPeriod;
    });
  }, [
    selectedPeriod,
    filteredDevices,
    trendCategory,
    trendCategoryValue,
    trendGranularity,
  ]);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Device Compliance Dashboard</h1>
        <div className="flex gap-2 items-center">
          <label className="text-sm">Dimension</label>
          <select
            className="p-2 rounded border"
            value={dimension}
            onChange={(e) => {
              setDimension(e.target.value as DimensionField);
              clearSelection();
            }}
          >
            <option value="region">Region</option>
            <option value="country">Country</option>
            <option value="productType">Product Type</option>
            <option value="deviceType">Device Type</option>
          </select>
        </div>
      </div>

      {/* Filters row */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex gap-3 items-center">
              <div>
                <label className="block text-xs">Region</label>
                <select
                  className="p-2 rounded border"
                  value={filters.region}
                  onChange={(e) =>
                    setFilters((s) => ({ ...s, region: e.target.value }))
                  }
                >
                  {regions.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs">Country</label>
                <select
                  className="p-2 rounded border"
                  value={filters.country}
                  onChange={(e) =>
                    setFilters((s) => ({ ...s, country: e.target.value }))
                  }
                >
                  {countries.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs">Product</label>
                <select
                  className="p-2 rounded border"
                  value={filters.productType}
                  onChange={(e) =>
                    setFilters((s) => ({ ...s, productType: e.target.value }))
                  }
                >
                  {productTypes.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs">Device Type</label>
                <select
                  className="p-2 rounded border"
                  value={filters.deviceType}
                  onChange={(e) =>
                    setFilters((s) => ({ ...s, deviceType: e.target.value }))
                  }
                >
                  {deviceTypes.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() => {
                  setFilters({
                    region: "All",
                    country: "All",
                    productType: "All",
                    deviceType: "All",
                  });
                  clearSelection();
                }}
              >
                Reset filters
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-6">
            {/* PIE CHART */}
            <div className="h-72 bg-white rounded-lg shadow p-4">
              <h3 className="font-medium mb-2">
                Overall Summary — {dimension}
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <ReTooltip />
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={70}
                    onClick={onPieClick}
                    label={renderPieLabel}
                    labelLine={false}
                  >
                    {pieData.map((entry, index) => {
                      const isSelected =
                        selectedSlice &&
                        selectedSlice.dim === dimension &&
                        selectedSlice.key === entry.name;
                      const dimmed = selectedSlice && !isSelected;
                      return (
                        <Cell
                          key={`cell-${index}`}
                          fill={entry.color}
                          stroke={isSelected ? "#111827" : "#ffffff"}
                          strokeWidth={isSelected ? 3 : 1}
                          opacity={dimmed ? 0.4 : 1}
                          cursor="pointer"
                        />
                      );
                    })}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="mt-3 flex flex-wrap gap-2 text-sm">
                {pieData.map((p) => (
                  <div
                    key={p.name}
                    className="flex items-center gap-2 w-1/2 md:w-1/3 lg:w-1/4"
                  >
                    <div
                      style={{ width: 12, height: 12, backgroundColor: p.color }}
                    />
                    <div className="truncate">
                      {p.name} — {p.value}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* BAR CHART */}
            <div className="h-72 bg-white rounded-lg shadow p-4">
              <div className="flex items-center justify-between">
                <h3 className="font-medium">Pass/Fail by {barCategory}</h3>
                <div className="flex items-center gap-2">
                  <label className="text-sm">Group by</label>
                  <select
                    className="p-2 rounded border"
                    value={barCategory}
                    onChange={(e) => {
                      setBarCategory(e.target.value as BarCategory);
                      clearSelection();
                    }}
                  >
                    <option value="deviceType">Device Type</option>
                    <option value="productType">Product Type</option>
                    <option value="country">Country</option>
                    <option value="region">Region</option>
                  </select>
                </div>
              </div>

              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={barData}
                  margin={{ top: 20, right: 30, left: 0, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="category" />
                  <YAxis />
                  <ReTooltip />
                  <Bar
                    dataKey="Fail"
                    stackId="a"
                    name="Fail"
                    fill={FAIL_COLOR}
                    onClick={(d: any) =>
                      setSelectedBar({
                        categoryValue: d.category as string,
                        status: "Fail",
                      })
                    }
                  >
                    {barData.map((entry, index) => {
                      const isSelected =
                        selectedBar &&
                        selectedBar.categoryValue === entry.category &&
                        selectedBar.status === "Fail";
                      const dimmed = selectedBar && !isSelected;
                      return (
                        <Cell
                          key={`cell-f-${index}`}
                          fill={FAIL_COLOR}
                          stroke={isSelected ? "#111827" : undefined}
                          strokeWidth={isSelected ? 2 : 1}
                          opacity={dimmed ? 0.4 : 1}
                          cursor="pointer"
                        />
                      );
                    })}
                  </Bar>
                  <Bar
                    dataKey="Pass"
                    stackId="a"
                    name="Pass"
                    fill={PASS_COLOR}
                    onClick={(d: any) =>
                      setSelectedBar({
                        categoryValue: d.category as string,
                        status: "Pass",
                      })
                    }
                  >
                    <LabelList
                      dataKey="Pass"
                      position="insideTop"
                      formatter={(
                        _value: any,
                        _name: any,
                        props: any,
                      ) => {
                        const passRate = props?.payload?.passRate;
                        if (passRate == null) return "";
                        const pct = Math.round(passRate as number);
                        return pct ? `${pct}%` : "";
                      }}
                      fill="#ffffff"
                      fontSize={10}
                    />
                    {barData.map((entry, index) => {
                      const isSelected =
                        selectedBar &&
                        selectedBar.categoryValue === entry.category &&
                        selectedBar.status === "Pass";
                      const dimmed = selectedBar && !isSelected;
                      return (
                        <Cell
                          key={`cell-p-${index}`}
                          fill={PASS_COLOR}
                          stroke={isSelected ? "#111827" : undefined}
                          strokeWidth={isSelected ? 2 : 1}
                          opacity={dimmed ? 0.4 : 1}
                          cursor="pointer"
                        />
                      );
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <div className="mt-2 text-sm">
                <span className="inline-flex items-center mr-3">
                  <span
                    style={{
                      width: 10,
                      height: 10,
                      backgroundColor: PASS_COLOR,
                      display: "inline-block",
                      marginRight: 8,
                    }}
                  />
                  Pass
                </span>
                <span className="inline-flex items-center">
                  <span
                    style={{
                      width: 10,
                      height: 10,
                      backgroundColor: FAIL_COLOR,
                      display: "inline-block",
                      marginRight: 8,
                    }}
                  />
                  Fail
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* TREND CHART */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-4">
              <h3 className="font-medium">Trend (pass rate)</h3>

              <div>
                <label className="block text-xs">Category</label>
                <select
                  className="p-2 rounded border"
                  value={trendCategory}
                  onChange={(e) => {
                    setTrendCategory(e.target.value as TrendCategory);
                    setTrendCategoryValue("All");
                  }}
                >
                  {trendOptions.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs">Value</label>
                <select
                  className="p-2 rounded border"
                  value={trendCategoryValue}
                  onChange={(e) => {
                    setTrendCategoryValue(e.target.value);
                    setSelectedPeriod(null);
                  }}
                >
                  {trendCategoryValues.map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs">Window (months)</label>
                <select
                  className="p-2 rounded border"
                  value={trendMonths}
                  onChange={(e) => setTrendMonths(Number(e.target.value))}
                >
                  <option value={1}>1</option>
                  <option value={3}>3</option>
                  <option value={6}>6</option>
                </select>
              </div>

              <div>
                <label className="block text-xs">Granularity</label>
                <select
                  className="p-2 rounded border"
                  value={trendGranularity}
                  onChange={(e) =>
                    setTrendGranularity(e.target.value as TrendGranularity)
                  }
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className="text-sm text-slate-500">
                Click a point to view detailed rows for that period
              </div>
              <Button
                onClick={() => {
                  setTrendCategory("country");
                  setTrendCategoryValue("All");
                  setTrendMonths(3);
                  setTrendGranularity("daily");
                  setSelectedPeriod(null);
                }}
              >
                Reset
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-80 bg-white rounded-lg p-4">
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trendSeries}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" />
                <YAxis yAxisId="left" domain={[0, 100]} unit="%" />
                <ReTooltip />
                <Line
                  type="monotone"
                  dataKey="passRate"
                  stroke={PASS_COLOR}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                  onClick={handlePointClick}
                />
              </LineChart>
            </ResponsiveContainer>

            <div className="mt-4 flex items-center justify-between">
              <div>
                <div className="text-sm">
                  Selected period: <span className="font-semibold">{selectedPeriod || "—"}</span>
                </div>
                <div className="text-sm text-slate-500">
                  Showing pass rate for {trendCategory}
                  {trendCategoryValue !== "All" && (
                    <span> = {trendCategoryValue}</span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  onClick={() => {
                    if (selectedPeriod)
                      downloadCSV(
                        selectedRowsForDownload,
                        `rows_${selectedPeriod}.csv`,
                      );
                  }}
                  disabled={!selectedPeriod}
                >
                  Download rows for selected period
                </Button>
                <Button
                  onClick={() => {
                    setSelectedPeriod(null);
                  }}
                >
                  Clear period
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Details panel (table) */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-medium">Details</h3>
          <div className="flex items-center gap-2">
            {selectedSlice || selectedBar || selectedPeriod ? (
              <>
                <div className="text-sm">Showing rows for:</div>
                <div className="text-sm font-semibold flex flex-wrap gap-2">
                  {selectedSlice && (
                    <span>
                      {selectedSlice.dim} = {selectedSlice.key}
                      {selectedSlice.status && (
                        <>
                          {" "}• {selectedSlice.status}
                        </>
                      )}
                    </span>
                  )}
                  {selectedBar && (
                    <span>
                      {barCategory} = {selectedBar.categoryValue}
                      {selectedBar.status && (
                        <>
                          {" "}• {selectedBar.status}
                        </>
                      )}
                    </span>
                  )}
                  {selectedPeriod && (
                    <span>
                      {trendCategory} = {trendCategoryValue} • {selectedPeriod}
                    </span>
                  )}
                </div>
                <Button onClick={clearSelection}>Clear</Button>
                <Button
                  onClick={() => downloadCSV(tableRows, "selected_rows.csv")}
                >
                  Download selected rows
                </Button>
              </>
            ) : (
              <div className="text-sm text-slate-500">
                Click a pie slice, a pass/fail bar, or a trend point to see
                related rows
              </div>
            )}
          </div>
        </div>

        {tableRows.length === 0 ? (
          <div className="text-sm text-slate-500">No rows selected.</div>
        ) : (
          <div className="overflow-auto max-h-96">
            <table className="min-w-full table-auto text-sm">
              <thead>
                <tr className="text-left border-b">
                  <th className="p-2">ID</th>
                  <th>Name</th>
                  <th>Region</th>
                  <th>Country</th>
                  <th>Product</th>
                  <th>Device Type</th>
                  <th>Status</th>
                  <th>Last Seen</th>
                </tr>
              </thead>
              <tbody>
                {tableRows.slice(0, 500).map((r) => (
                  <tr key={r.id} className="border-b hover:bg-slate-50">
                    <td className="p-2">{r.id}</td>
                    <td>{r.name}</td>
                    <td>{r.region}</td>
                    <td>{r.country}</td>
                    <td>{r.productType}</td>
                    <td>{r.deviceType}</td>
                    <td
                      className={
                        r.status === "Pass"
                          ? "text-green-600 font-semibold"
                          : "text-red-600 font-semibold"
                      }
                    >
                      {r.status}
                    </td>
                    <td>{r.lastSeen}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="text-xs text-slate-500">
        Notes: This is a single-file prototype. Replace the mocked data and
        enable the API call in useEffect once your backend is ready. The trend
        chart groups by daily/weekly/monthly and clicking a point will show
        rows from that period which you can download as CSV.
      </div>
    </div>
  );
}
