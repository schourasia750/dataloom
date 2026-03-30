import { useState } from "react";
import PropTypes from "prop-types";
import { getQualityAssessment, applyQualityFix } from "../../api";
import { QUALITY_FIX } from "../../constants/operationTypes";
import Toast from "../common/Toast";

const scoreTone = (score) => {
  if (score >= 85) return "text-emerald-700 bg-emerald-50 border-emerald-200";
  if (score >= 65) return "text-amber-700 bg-amber-50 border-amber-200";
  return "text-rose-700 bg-rose-50 border-rose-200";
};

const issueRows = (assessment) => {
  if (!assessment) return [];
  return [
    assessment.issues.duplicates,
    ...assessment.issues.outliers,
    ...assessment.issues.pattern_violations,
  ].filter((issue) => issue && issue.count > 0);
};

export default function QualityPanel({ projectId, onClose, onTransform }) {
  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fixingKey, setFixingKey] = useState(null);
  const [toast, setToast] = useState(null);

  const handleScan = async () => {
    setLoading(true);
    try {
      const response = await getQualityAssessment(projectId);
      setAssessment(response);
    } catch {
      setToast({ message: "Failed to assess data quality.", type: "error" });
    } finally {
      setLoading(false);
    }
  };

  const handleFix = async (issue) => {
    const key = `${issue.type}-${issue.column || "rows"}`;
    setFixingKey(key);
    try {
      const response = await applyQualityFix(projectId, {
        operation_type: QUALITY_FIX,
        quality_fix_params: issue.fix_action,
      });
      onTransform(response);
      setAssessment(response.quality_assessment);
      setToast({ message: `${issue.fix_label} applied.`, type: "success" });
    } catch {
      setToast({ message: `Failed to ${issue.fix_label.toLowerCase()}.`, type: "error" });
    } finally {
      setFixingKey(null);
    }
  };

  const issues = issueRows(assessment);

  return (
    <div className="p-4 border border-gray-200 rounded-lg bg-white shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Data Quality Assessment</h3>
          <p className="text-sm text-gray-500 mt-1">
            Detect duplicates, outliers, and pattern violations, then fix them in one click.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleScan}
            disabled={loading}
            className="px-3 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-60"
          >
            {loading ? "Scanning..." : "Run Scan"}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-2 rounded-md border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Close
          </button>
        </div>
      </div>

      {assessment && (
        <div className="mt-4 space-y-4">
          <div className="grid gap-3 md:grid-cols-[220px_1fr]">
            <div className={`rounded-xl border p-4 ${scoreTone(assessment.score)}`}>
              <div className="text-xs font-semibold uppercase tracking-[0.2em]">Composite Score</div>
              <div className="mt-2 text-4xl font-semibold">{assessment.score}</div>
              <div className="mt-2 text-sm">
                {assessment.summary.total_issues === 0
                  ? "No quality issues detected."
                  : `${assessment.summary.total_issues} detected cells or rows need attention.`}
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-gray-500">Duplicates</div>
                <div className="mt-2 text-2xl font-semibold text-gray-900">
                  {assessment.summary.duplicate_rows}
                </div>
              </div>
              <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-gray-500">Outliers</div>
                <div className="mt-2 text-2xl font-semibold text-gray-900">
                  {assessment.summary.outliers}
                </div>
              </div>
              <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-gray-500">
                  Pattern Violations
                </div>
                <div className="mt-2 text-2xl font-semibold text-gray-900">
                  {assessment.summary.pattern_violations}
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            {issues.length === 0 ? (
              <div className="rounded-xl border border-dashed border-gray-300 p-5 text-sm text-gray-500">
                Everything looks clean. Run the scan again after new edits to refresh the score.
              </div>
            ) : (
              issues.map((issue) => {
                const key = `${issue.type}-${issue.column || "rows"}`;
                return (
                  <div
                    key={key}
                    className="flex flex-col gap-3 rounded-xl border border-gray-200 p-4 md:flex-row md:items-center md:justify-between"
                  >
                    <div>
                      <div className="text-sm font-semibold text-gray-900">{issue.label}</div>
                      <div className="mt-1 text-sm text-gray-500">
                        {issue.count} affected {issue.type === "duplicates" ? "rows" : "values"}
                        {issue.column ? ` in ${issue.column}` : ""}.
                      </div>
                    </div>
                    <button
                      type="button"
                      disabled={fixingKey === key}
                      onClick={() => handleFix(issue)}
                      className="px-3 py-2 rounded-md bg-gray-900 text-white text-sm font-medium hover:bg-gray-800 disabled:opacity-60"
                    >
                      {fixingKey === key ? "Applying..." : issue.fix_label}
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {toast && (
        <div className="fixed bottom-4 right-4 z-50">
          <Toast message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />
        </div>
      )}
    </div>
  );
}

QualityPanel.propTypes = {
  projectId: PropTypes.string.isRequired,
  onClose: PropTypes.func.isRequired,
  onTransform: PropTypes.func.isRequired,
};
