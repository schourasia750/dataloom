import { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import { useProjectContext } from "../context/ProjectContext";
import {
  buildBarChartData,
  buildHistogramData,
  buildScatterData,
  buildTimeSeriesData,
  getVisualizationDefaults,
} from "../utils/visualization";

const CHART_TYPES = [
  { id: "histogram", label: "Histogram" },
  { id: "bar", label: "Bar" },
  { id: "scatter", label: "Scatter" },
  { id: "timeSeries", label: "Time Series" },
];

const withFallbackOption = (options, label) =>
  options.length > 0 ? options : [{ value: "", label }];

const SVG_WIDTH = 720;
const SVG_HEIGHT = 320;
const MARGIN = { top: 24, right: 24, bottom: 64, left: 56 };

const getPlotBounds = () => ({
  left: MARGIN.left,
  right: SVG_WIDTH - MARGIN.right,
  top: MARGIN.top,
  bottom: SVG_HEIGHT - MARGIN.bottom,
  width: SVG_WIDTH - MARGIN.left - MARGIN.right,
  height: SVG_HEIGHT - MARGIN.top - MARGIN.bottom,
});

function ChartSurface({ children }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <svg viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`} className="h-[320px] w-full">
        {children}
      </svg>
    </div>
  );
}

ChartSurface.propTypes = {
  children: PropTypes.node.isRequired,
};

function EmptyChartState({ message }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-16 text-center text-sm text-slate-500">
      {message}
    </div>
  );
}

EmptyChartState.propTypes = {
  message: PropTypes.string.isRequired,
};

function SelectField({ label, value, options, onChange }) {
  return (
    <label className="flex min-w-[180px] flex-col gap-1">
      <span className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

SelectField.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.string.isRequired,
  options: PropTypes.arrayOf(
    PropTypes.shape({
      value: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
    }),
  ).isRequired,
  onChange: PropTypes.func.isRequired,
};

function AxisFrame() {
  const bounds = getPlotBounds();
  return (
    <>
      <line
        x1={bounds.left}
        y1={bounds.bottom}
        x2={bounds.right}
        y2={bounds.bottom}
        stroke="#94a3b8"
        strokeWidth="1.5"
      />
      <line
        x1={bounds.left}
        y1={bounds.top}
        x2={bounds.left}
        y2={bounds.bottom}
        stroke="#94a3b8"
        strokeWidth="1.5"
      />
    </>
  );
}

function HistogramChart({ data }) {
  const bounds = getPlotBounds();
  const maxCount = Math.max(...data.points.map((point) => point.count), 1);
  const barWidth = bounds.width / data.points.length;

  return (
    <ChartSurface>
      <AxisFrame />
      {data.points.map((point, index) => {
        const height = (point.count / maxCount) * bounds.height;
        const x = bounds.left + index * barWidth + 4;
        const y = bounds.bottom - height;
        return (
          <g key={point.label}>
            <rect
              x={x}
              y={y}
              width={Math.max(barWidth - 8, 12)}
              height={height}
              rx="6"
              fill="#2563eb"
              opacity="0.9"
            />
            <text x={x + Math.max(barWidth - 8, 12) / 2} y={y - 8} textAnchor="middle" fontSize="11" fill="#334155">
              {point.count}
            </text>
            <text
              x={x + Math.max(barWidth - 8, 12) / 2}
              y={bounds.bottom + 18}
              textAnchor="end"
              transform={`rotate(-28 ${x + Math.max(barWidth - 8, 12) / 2} ${bounds.bottom + 18})`}
              fontSize="10"
              fill="#64748b"
            >
              {point.label}
            </text>
          </g>
        );
      })}
    </ChartSurface>
  );
}

HistogramChart.propTypes = {
  data: PropTypes.shape({
    points: PropTypes.arrayOf(
      PropTypes.shape({
        label: PropTypes.string.isRequired,
        count: PropTypes.number.isRequired,
      }),
    ).isRequired,
  }).isRequired,
};

function BarChart({ data }) {
  const bounds = getPlotBounds();
  const maxValue = Math.max(...data.points.map((point) => point.value), 1);
  const barWidth = bounds.width / data.points.length;

  return (
    <ChartSurface>
      <AxisFrame />
      {data.points.map((point, index) => {
        const height = (point.value / maxValue) * bounds.height;
        const x = bounds.left + index * barWidth + 8;
        const y = bounds.bottom - height;
        return (
          <g key={point.label}>
            <rect
              x={x}
              y={y}
              width={Math.max(barWidth - 16, 14)}
              height={height}
              rx="8"
              fill="#0f766e"
            />
            <text x={x + Math.max(barWidth - 16, 14) / 2} y={y - 8} textAnchor="middle" fontSize="11" fill="#334155">
              {Number(point.value.toFixed(2))}
            </text>
            <text
              x={x + Math.max(barWidth - 16, 14) / 2}
              y={bounds.bottom + 18}
              textAnchor="end"
              transform={`rotate(-28 ${x + Math.max(barWidth - 16, 14) / 2} ${bounds.bottom + 18})`}
              fontSize="10"
              fill="#64748b"
            >
              {point.label}
            </text>
          </g>
        );
      })}
    </ChartSurface>
  );
}

BarChart.propTypes = {
  data: PropTypes.shape({
    points: PropTypes.arrayOf(
      PropTypes.shape({
        label: PropTypes.string.isRequired,
        value: PropTypes.number.isRequired,
      }),
    ).isRequired,
  }).isRequired,
};

function ScatterChart({ data }) {
  const bounds = getPlotBounds();
  const xValues = data.points.map((point) => point.x);
  const yValues = data.points.map((point) => point.y);
  const minX = Math.min(...xValues);
  const maxX = Math.max(...xValues);
  const minY = Math.min(...yValues);
  const maxY = Math.max(...yValues);
  const spanX = maxX - minX || 1;
  const spanY = maxY - minY || 1;

  return (
    <ChartSurface>
      <AxisFrame />
      {data.points.map((point, index) => {
        const x = bounds.left + ((point.x - minX) / spanX) * bounds.width;
        const y = bounds.bottom - ((point.y - minY) / spanY) * bounds.height;
        return <circle key={`${point.x}-${point.y}-${index}`} cx={x} cy={y} r="4.5" fill="#7c3aed" opacity="0.8" />;
      })}
      <text x={bounds.left} y={bounds.top - 6} fontSize="11" fill="#64748b">
        Y max: {Number(maxY.toFixed(2))}
      </text>
      <text x={bounds.right - 4} y={bounds.bottom + 24} textAnchor="end" fontSize="11" fill="#64748b">
        X max: {Number(maxX.toFixed(2))}
      </text>
    </ChartSurface>
  );
}

ScatterChart.propTypes = {
  data: PropTypes.shape({
    points: PropTypes.arrayOf(
      PropTypes.shape({
        x: PropTypes.number.isRequired,
        y: PropTypes.number.isRequired,
      }),
    ).isRequired,
  }).isRequired,
};

function TimeSeriesChart({ data }) {
  const bounds = getPlotBounds();
  const values = data.points.map((point) => point.value);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const spanY = maxValue - minValue || 1;
  const stepX = data.points.length > 1 ? bounds.width / (data.points.length - 1) : bounds.width;

  const path = data.points
    .map((point, index) => {
      const x = bounds.left + index * stepX;
      const y = bounds.bottom - ((point.value - minValue) / spanY) * bounds.height;
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");

  return (
    <ChartSurface>
      <AxisFrame />
      <path d={path} fill="none" stroke="#ea580c" strokeWidth="3" strokeLinecap="round" />
      {data.points.map((point, index) => {
        const x = bounds.left + index * stepX;
        const y = bounds.bottom - ((point.value - minValue) / spanY) * bounds.height;
        return (
          <g key={`${point.label}-${point.time}`}>
            <circle cx={x} cy={y} r="4.5" fill="#ea580c" />
            <text
              x={x}
              y={bounds.bottom + 18}
              textAnchor="end"
              transform={`rotate(-28 ${x} ${bounds.bottom + 18})`}
              fontSize="10"
              fill="#64748b"
            >
              {point.label}
            </text>
          </g>
        );
      })}
    </ChartSurface>
  );
}

TimeSeriesChart.propTypes = {
  data: PropTypes.shape({
    points: PropTypes.arrayOf(
      PropTypes.shape({
        label: PropTypes.string.isRequired,
        time: PropTypes.number.isRequired,
        value: PropTypes.number.isRequired,
      }),
    ).isRequired,
  }).isRequired,
};

export default function DataVisualization({ viewMode, onViewModeChange }) {
  const { columns, rows, dtypes, projectName } = useProjectContext();
  const defaults = useMemo(() => getVisualizationDefaults(columns, rows, dtypes), [columns, rows, dtypes]);

  const [chartType, setChartType] = useState("histogram");
  const [histogramColumn, setHistogramColumn] = useState("");
  const [barCategoryColumn, setBarCategoryColumn] = useState("");
  const [barValueColumn, setBarValueColumn] = useState("");
  const [scatterXColumn, setScatterXColumn] = useState("");
  const [scatterYColumn, setScatterYColumn] = useState("");
  const [timeColumn, setTimeColumn] = useState("");
  const [timeValueColumn, setTimeValueColumn] = useState("");

  useEffect(() => {
    setHistogramColumn(defaults.histogram.valueColumn);
    setBarCategoryColumn(defaults.bar.categoryColumn);
    setBarValueColumn(defaults.bar.valueColumn);
    setScatterXColumn(defaults.scatter.xColumn);
    setScatterYColumn(defaults.scatter.yColumn);
    setTimeColumn(defaults.timeSeries.timeColumn);
    setTimeValueColumn(defaults.timeSeries.valueColumn);
  }, [defaults]);

  const chartData = useMemo(() => {
    switch (chartType) {
      case "histogram":
        return buildHistogramData(columns, rows, histogramColumn);
      case "bar":
        return buildBarChartData(columns, rows, barCategoryColumn, barValueColumn);
      case "scatter":
        return buildScatterData(columns, rows, scatterXColumn, scatterYColumn);
      case "timeSeries":
        return buildTimeSeriesData(columns, rows, timeColumn, timeValueColumn);
      default:
        return { points: [], error: "Unsupported chart type." };
    }
  }, [
    barCategoryColumn,
    barValueColumn,
    chartType,
    columns,
    histogramColumn,
    rows,
    scatterXColumn,
    scatterYColumn,
    timeColumn,
    timeValueColumn,
  ]);

  const numericOptions = withFallbackOption(
    defaults.options.numericColumns.map((column) => ({ value: column, label: column })),
    "No numeric columns",
  );
  const temporalOptions = withFallbackOption(
    defaults.options.temporalColumns.map((column) => ({ value: column, label: column })),
    "No time columns",
  );
  const categoryOptions = withFallbackOption(
    defaults.options.metadata.map((item) => ({ value: item.column, label: item.column })),
    "No columns available",
  );

  const barValueOptions = [{ value: "", label: "Row count" }, ...numericOptions.filter((option) => option.value)];

  const renderControls = () => {
    if (chartType === "histogram") {
      return (
        <SelectField
          label="Value"
          value={histogramColumn}
          options={numericOptions}
          onChange={setHistogramColumn}
        />
      );
    }

    if (chartType === "bar") {
      return (
        <>
          <SelectField
            label="Category"
            value={barCategoryColumn}
            options={categoryOptions}
            onChange={setBarCategoryColumn}
          />
          <SelectField label="Metric" value={barValueColumn} options={barValueOptions} onChange={setBarValueColumn} />
        </>
      );
    }

    if (chartType === "scatter") {
      return (
        <>
          <SelectField label="X Axis" value={scatterXColumn} options={numericOptions} onChange={setScatterXColumn} />
          <SelectField label="Y Axis" value={scatterYColumn} options={numericOptions} onChange={setScatterYColumn} />
        </>
      );
    }

    return (
      <>
        <SelectField label="Time" value={timeColumn} options={temporalOptions} onChange={setTimeColumn} />
        <SelectField label="Value" value={timeValueColumn} options={numericOptions} onChange={setTimeValueColumn} />
      </>
    );
  };

  const renderChart = () => {
    if (chartData.error) {
      return <EmptyChartState message={chartData.error} />;
    }

    switch (chartType) {
      case "histogram":
        return <HistogramChart data={chartData} />;
      case "bar":
        return <BarChart data={chartData} />;
      case "scatter":
        return <ScatterChart data={chartData} />;
      case "timeSeries":
        return <TimeSeriesChart data={chartData} />;
      default:
        return <EmptyChartState message="Unsupported chart type." />;
    }
  };

  if (!columns.length || !rows.length) {
    return (
      <section className="px-8 pt-4">
        <EmptyChartState message="Load a dataset with rows before creating a visualization." />
      </section>
    );
  }

  return (
    <section className="space-y-4 px-8 pt-4">
      <div className="rounded-3xl border border-slate-200 bg-gradient-to-br from-white via-slate-50 to-blue-50 p-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Visualization</p>
            <div>
              <h2 className="text-2xl font-semibold text-slate-900">Explore {projectName || "dataset"} visually</h2>
              <p className="text-sm text-slate-600">
                Switch between table and chart views, then tune the axes for quick visual checks.
              </p>
            </div>
          </div>

          <div className="inline-flex rounded-2xl border border-slate-200 bg-white p-1 shadow-sm">
            <button
              className={`rounded-xl px-4 py-2 text-sm font-medium ${viewMode === "table" ? "bg-slate-900 text-white" : "text-slate-600"}`}
              onClick={() => onViewModeChange("table")}
            >
              Table
            </button>
            <button
              className={`rounded-xl px-4 py-2 text-sm font-medium ${viewMode === "chart" ? "bg-slate-900 text-white" : "text-slate-600"}`}
              onClick={() => onViewModeChange("chart")}
            >
              Chart
            </button>
          </div>
        </div>

        <div className="mt-5 flex flex-col gap-4 lg:flex-row lg:flex-wrap lg:items-end">
          <SelectField
            label="Chart Type"
            value={chartType}
            options={CHART_TYPES.map((item) => ({ value: item.id, label: item.label }))}
            onChange={setChartType}
          />
          {renderControls()}
        </div>
      </div>

      {renderChart()}
    </section>
  );
}

DataVisualization.propTypes = {
  viewMode: PropTypes.oneOf(["table", "chart"]).isRequired,
  onViewModeChange: PropTypes.func.isRequired,
};
