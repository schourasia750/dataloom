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

/**
 * Apply an automated quality fix.
 * @param {string} projectId - The project ID.
 * @param {Object} transformationInput - Quality fix parameters including operation_type.
 * @returns {Promise<Object>} Updated dataset plus refreshed quality assessment.
 */
export const applyQualityFix = async (projectId, transformationInput) => {
  const response = await client.post(`/projects/${projectId}/quality-fix`, transformationInput);
  return response.data;
};
