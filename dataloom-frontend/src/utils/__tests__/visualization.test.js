import {
  buildBarChartData,
  buildHistogramData,
  buildScatterData,
  buildTimeSeriesData,
  getVisualizationDefaults,
} from "../visualization";

describe("visualization utils", () => {
  const columns = ["city", "sales", "profit", "order_date"];
  const rows = [
    ["Delhi", 10, 4, "2026-01-01"],
    ["Mumbai", 20, 6, "2026-01-02"],
    ["Delhi", 15, 8, "2026-01-02"],
    ["Pune", 8, 3, "2026-01-03"],
  ];
  const dtypes = {
    city: "object",
    sales: "int64",
    profit: "float64",
    order_date: "datetime64[ns]",
  };

  it("chooses sensible default columns by chart type", () => {
    const defaults = getVisualizationDefaults(columns, rows, dtypes);

    expect(defaults.histogram.valueColumn).toBe("sales");
    expect(defaults.bar.categoryColumn).toBe("city");
    expect(defaults.scatter.xColumn).toBe("sales");
    expect(defaults.scatter.yColumn).toBe("profit");
    expect(defaults.timeSeries.timeColumn).toBe("order_date");
    expect(defaults.timeSeries.valueColumn).toBe("sales");
  });

  it("builds histogram bins from numeric columns", () => {
    const result = buildHistogramData(columns, rows, "sales");

    expect(result.error).toBeNull();
    expect(result.points.length).toBeGreaterThanOrEqual(4);
    expect(result.points.reduce((sum, point) => sum + point.count, 0)).toBe(4);
  });

  it("aggregates bar charts by category", () => {
    const result = buildBarChartData(columns, rows, "city", "sales");

    expect(result.error).toBeNull();
    expect(result.points[0]).toMatchObject({ label: "Delhi", value: 25 });
  });

  it("builds scatter plot points from paired numeric columns", () => {
    const result = buildScatterData(columns, rows, "sales", "profit");

    expect(result.error).toBeNull();
    expect(result.points).toEqual([
      { x: 10, y: 4 },
      { x: 20, y: 6 },
      { x: 15, y: 8 },
      { x: 8, y: 3 },
    ]);
  });

  it("sorts and aggregates time series data", () => {
    const result = buildTimeSeriesData(columns, rows, "order_date", "sales");

    expect(result.error).toBeNull();
    expect(result.points).toHaveLength(3);
    expect(result.points[1].value).toBe(35);
  });
});
