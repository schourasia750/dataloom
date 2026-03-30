const MAX_CATEGORY_BARS = 12;

const DATE_TYPE_PATTERN = /(date|time)/i;
const NUMERIC_TYPE_PATTERN = /(int|float|double|number|decimal)/i;

const isNil = (value) => value === null || value === undefined || value === "";

const toFiniteNumber = (value) => {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }

  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : null;
  }

  return null;
};

const toTimestamp = (value) => {
  if (value instanceof Date) {
    const time = value.getTime();
    return Number.isNaN(time) ? null : time;
  }

  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }

  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const parsed = Date.parse(trimmed);
    return Number.isNaN(parsed) ? null : parsed;
  }

  return null;
};

function getColumnValues(rows, columnIndex) {
  return rows.map((row) => row[columnIndex]);
}

function inferNumericColumn(dtype, values) {
  if (dtype && NUMERIC_TYPE_PATTERN.test(dtype)) return true;
  const valid = values.map(toFiniteNumber).filter((value) => value !== null);
  return valid.length >= Math.max(2, Math.ceil(values.length * 0.6));
}

function inferTemporalColumn(dtype, values) {
  if (dtype && DATE_TYPE_PATTERN.test(dtype)) return true;
  const valid = values.map(toTimestamp).filter((value) => value !== null);
  return valid.length >= Math.max(2, Math.ceil(values.length * 0.6));
}

export function getVisualizationMetadata(columns, rows, dtypes = {}) {
  return columns.map((column, index) => {
    const values = getColumnValues(rows, index);
    const dtype = dtypes[column] || "";
    const isNumeric = inferNumericColumn(dtype, values);
    const isTemporal = inferTemporalColumn(dtype, values);

    return {
      column,
      index,
      dtype,
      isNumeric,
      isTemporal,
      isCategorical: !isTemporal,
    };
  });
}

export function getVisualizationDefaults(columns, rows, dtypes = {}) {
  const metadata = getVisualizationMetadata(columns, rows, dtypes);
  const numericColumns = metadata.filter((item) => item.isNumeric).map((item) => item.column);
  const temporalColumns = metadata.filter((item) => item.isTemporal).map((item) => item.column);
  const categoricalColumns = metadata
    .filter((item) => !item.isNumeric && !item.isTemporal)
    .map((item) => item.column);

  return {
    histogram: {
      valueColumn: numericColumns[0] || columns[0] || "",
    },
    bar: {
      categoryColumn: categoricalColumns[0] || columns[0] || "",
      valueColumn: numericColumns[0] || "",
    },
    scatter: {
      xColumn: numericColumns[0] || columns[0] || "",
      yColumn: numericColumns[1] || numericColumns[0] || columns[1] || columns[0] || "",
    },
    timeSeries: {
      timeColumn: temporalColumns[0] || columns[0] || "",
      valueColumn: numericColumns[0] || columns[1] || columns[0] || "",
    },
    options: {
      numericColumns,
      temporalColumns,
      categoricalColumns,
      metadata,
    },
  };
}

export function buildHistogramData(columns, rows, valueColumn, binCount = 10) {
  const columnIndex = columns.indexOf(valueColumn);
  if (columnIndex === -1) {
    return { points: [], domain: [0, 0], error: "Select a numeric column for the histogram." };
  }

  const values = getColumnValues(rows, columnIndex).map(toFiniteNumber).filter((value) => value !== null);
  if (values.length < 2) {
    return { points: [], domain: [0, 0], error: "Histogram needs at least two numeric values." };
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) {
    return {
      points: [{ label: String(min), count: values.length, start: min, end: max }],
      domain: [min, max],
      error: null,
    };
  }

  const bins = Math.max(5, Math.min(binCount, Math.ceil(Math.sqrt(values.length))));
  const width = (max - min) / bins;
  const counts = new Array(bins).fill(0);

  values.forEach((value) => {
    const rawIndex = Math.floor((value - min) / width);
    const index = Math.min(rawIndex, bins - 1);
    counts[index] += 1;
  });

  const points = counts.map((count, index) => {
    const start = min + index * width;
    const end = start + width;
    return {
      label: `${start.toFixed(1)}-${end.toFixed(1)}`,
      count,
      start,
      end,
    };
  });

  return { points, domain: [min, max], error: null };
}

export function buildBarChartData(columns, rows, categoryColumn, valueColumn = "") {
  const categoryIndex = columns.indexOf(categoryColumn);
  if (categoryIndex === -1) {
    return { points: [], error: "Select a category column for the bar chart." };
  }

  const buckets = new Map();

  rows.forEach((row) => {
    const rawCategory = row[categoryIndex];
    if (isNil(rawCategory)) return;
    const category = String(rawCategory);
    const existing = buckets.get(category) || { label: category, value: 0, samples: 0 };

    if (valueColumn) {
      const valueIndex = columns.indexOf(valueColumn);
      const numericValue = toFiniteNumber(row[valueIndex]);
      if (numericValue === null) return;
      existing.value += numericValue;
      existing.samples += 1;
    } else {
      existing.value += 1;
      existing.samples += 1;
    }

    buckets.set(category, existing);
  });

  const points = [...buckets.values()]
    .sort((a, b) => b.value - a.value)
    .slice(0, MAX_CATEGORY_BARS);

  if (points.length === 0) {
    return { points: [], error: "Bar chart needs category data and at least one matching row." };
  }

  return { points, error: null };
}

export function buildScatterData(columns, rows, xColumn, yColumn) {
  const xIndex = columns.indexOf(xColumn);
  const yIndex = columns.indexOf(yColumn);

  if (xIndex === -1 || yIndex === -1) {
    return { points: [], error: "Select numeric X and Y columns for the scatter plot." };
  }

  const points = rows
    .map((row) => ({
      x: toFiniteNumber(row[xIndex]),
      y: toFiniteNumber(row[yIndex]),
    }))
    .filter((point) => point.x !== null && point.y !== null);

  if (points.length < 2) {
    return { points: [], error: "Scatter plot needs at least two numeric rows." };
  }

  return { points, error: null };
}

export function buildTimeSeriesData(columns, rows, timeColumn, valueColumn) {
  const timeIndex = columns.indexOf(timeColumn);
  const valueIndex = columns.indexOf(valueColumn);

  if (timeIndex === -1 || valueIndex === -1) {
    return { points: [], error: "Select a time column and a numeric value column." };
  }

  const buckets = new Map();

  rows.forEach((row) => {
    const timestamp = toTimestamp(row[timeIndex]);
    const value = toFiniteNumber(row[valueIndex]);
    if (timestamp === null || value === null) return;

    const key = new Date(timestamp).toISOString();
    buckets.set(key, (buckets.get(key) || 0) + value);
  });

  const points = [...buckets.entries()]
    .map(([isoTime, value]) => ({
      label: new Date(isoTime).toLocaleDateString(),
      time: new Date(isoTime).getTime(),
      value,
    }))
    .sort((a, b) => a.time - b.time);

  if (points.length < 2) {
    return { points: [], error: "Time series needs at least two dated numeric rows." };
  }

  return { points, error: null };
}
