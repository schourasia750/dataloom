import { useState } from "react";
import PropTypes from "prop-types";
import { transformProject } from "../../api";
import { COMPUTED_FORMULA } from "../../constants/operationTypes";
import { useToast } from "../../context/ToastContext";
import useError from "../../hooks/useError";
import FormErrorAlert from "../common/FormErrorAlert";

const ComputedFormulaForm = ({ projectId, onClose, onTransform }) => {
  const [newColumn, setNewColumn] = useState("");
  const [formula, setFormula] = useState("");
  const { showToast } = useToast();
  const { error, clearError, handleError } = useError();

  const handleSubmit = async (e) => {
    e.preventDefault();
    clearError();

    try {
      const response = await transformProject(projectId, {
        operation_type: COMPUTED_FORMULA,
        computed_formula_params: {
          new_column: newColumn,
          formula,
        },
      });

      onTransform(response);
      onClose();
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to create computed column.", "error");
      handleError(err);
    }
  };

  return (
    <div className="p-4 border border-gray-200 rounded-lg bg-white">
      <form onSubmit={handleSubmit}>
        <h3 className="font-semibold text-gray-900 mb-2">Computed Formula Column</h3>
        <p className="text-sm text-gray-500 mb-4">
          Use pandas-style expressions like <code>price * quantity</code>.
        </p>

        <div className="flex flex-wrap gap-2 mb-4">
          <div className="flex-1 min-w-[220px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">New Column</label>
            <input
              type="text"
              value={newColumn}
              onChange={(e) => setNewColumn(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 w-full bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none"
              placeholder="total_revenue"
              required
            />
          </div>

          <div className="flex-[2] min-w-[280px]">
            <label className="block text-sm font-medium text-gray-700 mb-1">Formula</label>
            <input
              type="text"
              value={formula}
              onChange={(e) => setFormula(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 w-full bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none"
              placeholder="price * quantity"
              required
            />
          </div>
        </div>

        <div className="flex justify-between">
          <button
            type="submit"
            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md font-medium transition-colors duration-150"
          >
            Create Column
          </button>

          <button
            type="button"
            onClick={onClose}
            className="bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 px-4 py-2 rounded-md font-medium transition-colors duration-150"
          >
            Cancel
          </button>
        </div>
      </form>
      <FormErrorAlert message={error} />
    </div>
  );
};

ComputedFormulaForm.propTypes = {
  projectId: PropTypes.string.isRequired,
  onClose: PropTypes.func.isRequired,
  onTransform: PropTypes.func.isRequired,
};

export default ComputedFormulaForm;
