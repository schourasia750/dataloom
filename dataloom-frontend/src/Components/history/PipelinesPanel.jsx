import PropTypes from "prop-types";

const PipelinesPanel = ({ pipelines, onClose, onApply }) => {
  return (
    <div className="p-4 bg-white border border-gray-200 rounded-lg shadow-sm mx-auto relative group">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Saved Pipelines</h3>
          <p className="text-sm text-gray-500">Apply a previously saved transformation sequence.</p>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 font-medium transition-opacity opacity-0 group-hover:opacity-100"
          style={{
            transition: "opacity 0.3s",
            background: "transparent",
            border: "none",
            cursor: "pointer",
          }}
        >
          Close
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full bg-white rounded-lg overflow-hidden">
          <thead className="bg-gray-50">
            <tr>
              <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Name
              </th>
              <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Description
              </th>
              <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Steps
              </th>
              <th className="py-3 px-4 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                Action
              </th>
            </tr>
          </thead>
          <tbody>
            {pipelines.length > 0 ? (
              pipelines.map((pipeline) => (
                <tr
                  key={pipeline.id}
                  className="border-b border-gray-100 hover:bg-gray-50 transition-colors duration-150"
                >
                  <td className="py-3 px-4 text-sm text-gray-700">{pipeline.name}</td>
                  <td className="py-3 px-4 text-sm text-gray-500">{pipeline.description || "-"}</td>
                  <td className="py-3 px-4 text-sm text-gray-500">{pipeline.steps.length}</td>
                  <td className="py-3 px-4 text-center">
                    <button
                      onClick={() => onApply(pipeline.id)}
                      className="bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium px-3 py-1.5 rounded-md transition-colors duration-150"
                    >
                      Apply
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="4" className="py-4 px-4 text-center text-sm text-gray-500">
                  No pipelines saved yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

PipelinesPanel.propTypes = {
  pipelines: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      description: PropTypes.string,
      steps: PropTypes.arrayOf(PropTypes.object).isRequired,
    }),
  ).isRequired,
  onClose: PropTypes.func.isRequired,
  onApply: PropTypes.func.isRequired,
};

export default PipelinesPanel;
