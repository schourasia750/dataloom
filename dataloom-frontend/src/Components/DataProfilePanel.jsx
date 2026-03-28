import PropTypes from "prop-types";
import DtypeBadge from "./common/DtypeBadge";

const statCardBase =
  "rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm shadow-slate-200/60";

function formatMetric(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }

  if (typeof value === "number") {
    return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2);
  }

  return String(value);
}

export default function DataProfilePanel({ profile }) {
  if (!profile?.summary || !Array.isArray(profile.columns) || profile.columns.length === 0) {
    return null;
  }

  const { row_count, column_count, missing_cells, duplicate_rows } = profile.summary;

  return (
    <section className="px-8 pt-6">
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-50 shadow-sm shadow-slate-200/70">
        <div className="border-b border-slate-200 bg-white px-6 py-5">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-sky-600">
            Automatic Profile
          </p>
          <div className="mt-2 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="text-2xl font-semibold text-slate-900">Understand the dataset fast</h2>
              <p className="text-sm text-slate-600">
                Column names, types, missing data, uniqueness, and numeric ranges are ready as
                soon as the file loads.
              </p>
            </div>
          </div>
        </div>

        <div className="grid gap-3 border-b border-slate-200 bg-slate-100/80 px-6 py-4 md:grid-cols-4">
          <div className={statCardBase}>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Rows</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{formatMetric(row_count)}</p>
          </div>
          <div className={statCardBase}>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Columns</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">
              {formatMetric(column_count)}
            </p>
          </div>
          <div className={statCardBase}>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Missing Cells
            </p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">
              {formatMetric(missing_cells)}
            </p>
          </div>
          <div className={statCardBase}>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Duplicate Rows
            </p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">
              {formatMetric(duplicate_rows)}
            </p>
          </div>
        </div>

        <div className="grid gap-4 px-6 py-5 lg:grid-cols-2">
          {profile.columns.map((column) => (
            <article
              key={column.name}
              className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm shadow-slate-200/50"
            >
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-base font-semibold text-slate-900">{column.name}</h3>
                <DtypeBadge dtype={column.data_type} />
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">Missing</p>
                  <p className="mt-1 text-sm font-medium text-slate-900">
                    {formatMetric(column.missing_count)} ({formatMetric(column.missing_percent)}%)
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">Unique</p>
                  <p className="mt-1 text-sm font-medium text-slate-900">
                    {formatMetric(column.unique_count)} ({formatMetric(column.unique_percent)}%)
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">Non-null</p>
                  <p className="mt-1 text-sm font-medium text-slate-900">
                    {formatMetric(column.non_null_count)}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">Mean</p>
                  <p className="mt-1 text-sm font-medium text-slate-900">
                    {formatMetric(column.mean)}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">Min</p>
                  <p className="mt-1 text-sm font-medium text-slate-900">
                    {formatMetric(column.min)}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-slate-500">Max</p>
                  <p className="mt-1 text-sm font-medium text-slate-900">
                    {formatMetric(column.max)}
                  </p>
                </div>
              </div>

              <div className="mt-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">Sample values</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {column.sample_values?.length ? (
                    column.sample_values.map((value, index) => (
                      <span
                        key={`${column.name}-${index}`}
                        className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700"
                      >
                        {formatMetric(value)}
                      </span>
                    ))
                  ) : (
                    <span className="text-sm text-slate-500">No non-null sample values</span>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

DataProfilePanel.propTypes = {
  profile: PropTypes.shape({
    summary: PropTypes.shape({
      row_count: PropTypes.number,
      column_count: PropTypes.number,
      missing_cells: PropTypes.number,
      duplicate_rows: PropTypes.number,
    }),
    columns: PropTypes.arrayOf(
      PropTypes.shape({
        name: PropTypes.string.isRequired,
        data_type: PropTypes.string,
        non_null_count: PropTypes.number,
        missing_count: PropTypes.number,
        missing_percent: PropTypes.number,
        unique_count: PropTypes.number,
        unique_percent: PropTypes.number,
        sample_values: PropTypes.arrayOf(
          PropTypes.oneOfType([PropTypes.string, PropTypes.number, PropTypes.bool]),
        ),
        mean: PropTypes.number,
        min: PropTypes.oneOfType([PropTypes.string, PropTypes.number, PropTypes.bool]),
        max: PropTypes.oneOfType([PropTypes.string, PropTypes.number, PropTypes.bool]),
      }),
    ),
  }),
};
