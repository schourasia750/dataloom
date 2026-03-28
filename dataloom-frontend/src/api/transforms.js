/**
 * API functions for project transformation operations.
 * @module api/transforms
 */
import client from "./client";

/**
 * Apply a transformation (filter, sort, add/delete row/column, pivot, etc).
 * @param {string} projectId - The project ID.
 * @param {Object} transformationInput - The transformation parameters including operation_type.
 * @returns {Promise<Object>} Transformation result with updated rows and columns.
 */
export const transformProject = async (projectId, transformationInput) => {
  const response = await client.post(`/projects/${projectId}/transform`, transformationInput);
  return response.data;
};

export const getPipelines = async (projectId) => {
  const response = await client.get(`/projects/${projectId}/pipelines`);
  return response.data;
};

export const createPipeline = async (projectId, pipelineInput) => {
  const response = await client.post(`/projects/${projectId}/pipelines`, pipelineInput);
  return response.data;
};

export const applyPipeline = async (projectId, pipelineId) => {
  const response = await client.post(`/projects/${projectId}/pipelines/${pipelineId}/apply`);
  return response.data;
};
