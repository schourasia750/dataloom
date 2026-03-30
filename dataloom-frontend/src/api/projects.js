/**
 * API functions for project CRUD operations.
 * @module api/projects
 */
import client from "./client";

/**
 * Upload a new project dataset file.
 * @param {File} file - The dataset file to upload.
 * @param {string} projectName - Name for the new project.
 * @param {string} projectDescription - Description for the new project.
 * @returns {Promise<Object>} The created project response.
 */
export const uploadProject = async (file, projectName, projectDescription) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("projectName", projectName);
  formData.append("projectDescription", projectDescription);
  const response = await client.post("/projects/upload", formData);
  return response.data;
};

/**
 * Fetch full project details including rows and columns.
 * @param {string} projectId - The project ID.
 * @returns {Promise<Object>} Project details with columns and rows.
 */
export const getProjectDetails = async (projectId) => {
  const response = await client.get(`/projects/get/${projectId}`);
  return response.data;
};

/**
 * Fetch the most recently modified projects.
 * @returns {Promise<Array>} List of recent project summaries.
 */
export const getRecentProjects = async () => {
  const response = await client.get("/projects/recent");
  return response.data;
};

/**
 * Save the current project state as a checkpoint.
 * @param {string} projectId - The project ID.
 * @param {string} commitMessage - Description of changes.
 * @returns {Promise<Object>} Updated project response.
 */
export const saveProject = async (projectId, commitMessage) => {
  const response = await client.post(
    `/projects/${projectId}/save?commit_message=${encodeURIComponent(commitMessage)}`,
  );
  return response.data;
};

/**
 * Revert project to a previous checkpoint.
 * @param {string} projectId - The project ID.
 * @param {string} checkpointId - The checkpoint ID to revert to.
 * @returns {Promise<Object>} Reverted project response.
 */
export const revertToCheckpoint = async (projectId, checkpointId) => {
  const response = await client.post(`/projects/${projectId}/revert?checkpoint_id=${checkpointId}`);
  return response.data;
};

/**
 * Extract a filename from a Content-Disposition header if present.
 * @param {string | undefined} header
 * @returns {string | null}
 */
const getFilenameFromDisposition = (header) => {
  if (!header) return null;
  const match = header.match(/filename="?([^"]+)"?/i);
  return match ? match[1] : null;
};

/**
 * Export the current working copy of a project as a downloadable file.
 * @param {string} projectId - The project ID.
 * @param {string} format - Export format.
 * @returns {Promise<{blob: Blob, filename: string | null}>} The download payload.
 */
export const exportProject = async (projectId, format = "csv") => {
  const response = await client.get(`/projects/${projectId}/export`, {
    params: { format },
    responseType: "blob",
  });
  return {
    blob: response.data,
    filename: getFilenameFromDisposition(response.headers["content-disposition"]),
  };
};

/**
 * Download a generated quality report for a project.
 * @param {string} projectId - The project ID.
 * @param {string} format - Report format.
 * @returns {Promise<{blob: Blob, filename: string | null}>} The download payload.
 */
export const downloadQualityReport = async (projectId, format = "html") => {
  const response = await client.get(`/projects/${projectId}/quality-report`, {
    params: { format },
    responseType: "blob",
  });
  return {
    blob: response.data,
    filename: getFilenameFromDisposition(response.headers["content-disposition"]),
  };
};

/**
 * Delete a project and its associated files.
 * @param {string} projectId - The project ID.
 * @returns {Promise<Object>} Success confirmation.
 */
export const deleteProject = async (projectId) => {
  const response = await client.delete(`/projects/${projectId}`);
  return response.data;
};
