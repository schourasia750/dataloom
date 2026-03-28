import { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { getAllProjects, getProjectDetails, transformProject } from "../../api";
import { JOIN_PROJECTS } from "../../constants/operationTypes";
import { useProjectContext } from "../../context/ProjectContext";
import { useToast } from "../../context/ToastContext";
import FormErrorAlert from "../common/FormErrorAlert";

const JOIN_TYPES = [
  { value: "inner", label: "Inner join" },
  { value: "left", label: "Left join" },
  { value: "right", label: "Right join" },
  { value: "outer", label: "Outer join" },
];

const JoinProjectForm = ({ projectId, onClose, onTransform }) => {
  const { columns } = useProjectContext();
  const { showToast } = useToast();

  const [availableProjects, setAvailableProjects] = useState([]);
  const [rightProjectId, setRightProjectId] = useState("");
  const [rightColumns, setRightColumns] = useState([]);
  const [leftOn, setLeftOn] = useState("");
  const [rightOn, setRightOn] = useState("");
  const [joinType, setJoinType] = useState("inner");
  const [suffix, setSuffix] = useState("joined");
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [loadingColumns, setLoadingColumns] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;

    const loadProjects = async () => {
      setLoadingProjects(true);
      setError(null);
      try {
        const projects = await getAllProjects();
        if (!isMounted) return;
        setAvailableProjects(projects.filter((project) => project.project_id !== projectId));
      } catch (err) {
        if (!isMounted) return;
        setError(err.response?.data?.detail || "Something went wrong. Please try again.");
      } finally {
        if (isMounted) setLoadingProjects(false);
      }
    };

    loadProjects();
    return () => {
      isMounted = false;
    };
  }, [projectId]);

  useEffect(() => {
    let isMounted = true;

    const loadRightProjectColumns = async () => {
      if (!rightProjectId) {
        setRightColumns([]);
        setRightOn("");
        return;
      }

      setLoadingColumns(true);
      setError(null);
      try {
        const project = await getProjectDetails(rightProjectId);
        if (!isMounted) return;
        setRightColumns(project.columns);
        setRightOn((prev) => (prev && project.columns.includes(prev) ? prev : ""));
      } catch (err) {
        if (!isMounted) return;
        setRightColumns([]);
        setRightOn("");
        setError(err.response?.data?.detail || "Something went wrong. Please try again.");
      } finally {
        if (isMounted) setLoadingColumns(false);
      }
    };

    loadRightProjectColumns();
    return () => {
      isMounted = false;
    };
  }, [rightProjectId]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    try {
      const response = await transformProject(projectId, {
        operation_type: JOIN_PROJECTS,
        join_projects_params: {
          right_project_id: rightProjectId,
          left_on: leftOn,
          right_on: rightOn,
          join_type: joinType,
          suffix: suffix.trim() || "joined",
        },
      });

      onTransform(response);
      showToast("Projects joined successfully.", "success");
      onClose();
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to join projects.", "error");
      setError(err.response?.data?.detail || "Something went wrong. Please try again.");
    }
  };

  return (
    <div className="p-4 border border-gray-200 rounded-lg bg-white">
      <form onSubmit={handleSubmit}>
        <h3 className="font-semibold text-gray-900 mb-2">Join Another Project</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Project to join:</label>
            <select
              value={rightProjectId}
              onChange={(e) => setRightProjectId(e.target.value)}
              className="border border-gray-300 rounded-md w-full px-3 py-2 bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none"
              required
              disabled={loadingProjects}
            >
              <option value="">
                {loadingProjects ? "Loading projects..." : "Select another project..."}
              </option>
              {availableProjects.map((project) => (
                <option key={project.project_id} value={project.project_id}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Join type:</label>
            <select
              value={joinType}
              onChange={(e) => setJoinType(e.target.value)}
              className="border border-gray-300 rounded-md w-full px-3 py-2 bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none"
            >
              {JOIN_TYPES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Current project key:</label>
            <select
              value={leftOn}
              onChange={(e) => setLeftOn(e.target.value)}
              className="border border-gray-300 rounded-md w-full px-3 py-2 bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none"
              required
            >
              <option value="">Select a column...</option>
              {columns.map((column) => (
                <option key={column} value={column}>
                  {column}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Joined project key:</label>
            <select
              value={rightOn}
              onChange={(e) => setRightOn(e.target.value)}
              className="border border-gray-300 rounded-md w-full px-3 py-2 bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none"
              required
              disabled={!rightProjectId || loadingColumns}
            >
              <option value="">
                {loadingColumns ? "Loading columns..." : "Select a column..."}
              </option>
              {rightColumns.map((column) => (
                <option key={column} value={column}>
                  {column}
                </option>
              ))}
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="block text-sm font-medium text-gray-700">Duplicate-column suffix:</label>
            <input
              type="text"
              value={suffix}
              onChange={(e) => setSuffix(e.target.value)}
              className="border border-gray-300 rounded-md w-full px-3 py-2 bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none"
              placeholder="joined"
            />
          </div>
        </div>

        <div className="flex justify-between">
          <button
            type="submit"
            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md font-medium transition-colors duration-150"
            disabled={loadingProjects || loadingColumns || availableProjects.length === 0}
          >
            Join Projects
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

JoinProjectForm.propTypes = {
  projectId: PropTypes.string.isRequired,
  onClose: PropTypes.func.isRequired,
  onTransform: PropTypes.func.isRequired,
};

export default JoinProjectForm;
