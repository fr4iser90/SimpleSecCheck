import axios from 'axios';

const API_CORE_URL = '/api/v1/core';

// Utility for handling Axios responses, can be expanded (e.g., for error formatting)
const handleResponse = (response) => response.data;
const handleError = (error) => {
  // Log detailed error for debugging
  console.error('API Call Error:', error.config?.url, error.response?.status, error.response?.data);
  // Re-throw the error so components can handle it specifically if needed
  throw error;
};

const api = {
  // === Project Endpoints ===
  getProjects: () => axios.get(`${API_CORE_URL}/projects/`).then(handleResponse).catch(handleError),
  getProject: (id) => axios.get(`${API_CORE_URL}/projects/${id}/`).then(handleResponse).catch(handleError),
  // createProject, updateProject, deleteProject can be added if needed

  // === Scan Configuration Endpoints ===
  getScanConfigurations: (projectId) => {
    let url = `${API_CORE_URL}/scan-configurations/`;
    if (projectId) {
      url += `?project=${projectId}`;
    }
    return axios.get(url).then(handleResponse).catch(handleError);
  },
  getScanConfiguration: (id) => axios.get(`${API_CORE_URL}/scan-configurations/${id}/`).then(handleResponse).catch(handleError),
  createScanConfiguration: (data) => axios.post(`${API_CORE_URL}/scan-configurations/`, data).then(handleResponse).catch(handleError),
  updateScanConfiguration: (id, data) => axios.put(`${API_CORE_URL}/scan-configurations/${id}/`, data).then(handleResponse).catch(handleError),
  deleteScanConfiguration: (id) => axios.delete(`${API_CORE_URL}/scan-configurations/${id}/`).then(handleResponse).catch(handleError),

  // === Scan Execution & Status Endpoints ===
  triggerSampleScan: (payload) => {
    // Payload should be an object like { project_id, target_info, scan_configuration_id }
    // Based on ScanRunner.vue: const payload = { project_id: this.selectedProjectId, target_info: ..., scan_configuration_id: ... };
    return axios.post(`${API_CORE_URL}/scans/trigger-sample-scan/`, payload).then(handleResponse).catch(handleError);
  },
  // Note: ScanRunner.vue uses get /api/core/scans/scan-status/{taskId}/ directly for Celery task status.
  // It also uses get /api/core/scan-jobs/{jobId}/ for refreshing ScanJob.
  async getScanJob(jobId) {
    // Standardized to use apiClient and async/await
    console.log(`api.js: getScanJob called for jobId: ${jobId}`);
    try {
      const response = await axios.get(`${API_CORE_URL}/scan-jobs/${jobId}/`);
      console.log('api.js: getScanJob successful, response data:', response.data);
      return response.data;
    } catch (error) {
      console.error('api.js: Error in getScanJob:', error.response?.data || error.message);
      throw error;
    }
  },
  async getCeleryTaskStatus(taskId) {
    // Standardized to use apiClient and async/await
    console.log(`api.js: getCeleryTaskStatus called for taskId: ${taskId}`);
    try {
      const response = await axios.get(`${API_CORE_URL}/scans/scan-status/${taskId}/`);
      console.log('api.js: getCeleryTaskStatus successful, response data:', response.data);
      return response.data;
    } catch (error) {
      console.error('api.js: Error in getCeleryTaskStatus:', error.response?.data || error.message);
      throw error;
    }
  },
  getScanJobs: (projectId) => { // For ScanJobList.vue
    let url = `${API_CORE_URL}/scan-jobs/`;
    if (projectId) {
        url += `?project=${projectId}`;
    }
    return axios.get(url).then(handleResponse).catch(handleError);
  },

  // === Project Membership Endpoints ===
  getProjectMemberships: (projectId) => axios.get(`${API_CORE_URL}/project-memberships/?project=${projectId}`).then(handleResponse).catch(handleError),
  addProjectMember: (data) => axios.post(`${API_CORE_URL}/project-memberships/`, data).then(handleResponse).catch(handleError),
  updateProjectMember: (membershipId, data) => axios.patch(`${API_CORE_URL}/project-memberships/${membershipId}/`, data).then(handleResponse).catch(handleError),
  removeProjectMember: (membershipId) => axios.delete(`${API_CORE_URL}/project-memberships/${membershipId}/`).then(handleResponse).catch(handleError),

  // === User Management (Simplified) ===
  // For selecting users to add to projects. Might need a more specific/searchable endpoint in a real app.
  getUsers: () => axios.get(`${API_CORE_URL}/users/`).then(handleResponse).catch(handleError), // Assumes a /users/ endpoint exists

  // === User Profile Endpoint ===
  getUserProfile: () => axios.get(`${API_CORE_URL}/user/profile/`).then(handleResponse).catch(handleError),
  updateUserProfile: (data) => axios.patch(`${API_CORE_URL}/user/profile/`, data).then(handleResponse).catch(handleError),

  // === API Key Endpoints ===
  getApiKeys: () => axios.get(`${API_CORE_URL}/user/api-keys/`).then(handleResponse).catch(handleError),
  generateApiKey: (data) => axios.post(`${API_CORE_URL}/user/api-keys/generate/`, data).then(handleResponse).catch(handleError),
  revokeApiKey: (id) => axios.post(`${API_CORE_URL}/user/api-keys/${id}/revoke/`).then(handleResponse).catch(handleError),
  // updateApiKey (e.g. name, expiry) can be added if needed: patch/put to /user/api-keys/{id}/

  // === Security Tools (Admin only usually) ===
  getSecurityTools: () => axios.get(`${API_CORE_URL}/security-tools/`).then(handleResponse).catch(handleError),
  // Add create, update, delete for Security Tools if frontend admin functions are built

  // === Target Groups & Scan Targets (if managed directly) === 
  // getTargetGroups, createTargetGroup, etc.
  // getScanTargets, createScanTarget, etc.

  async createScanJob(payload) {
    console.log('api.js: createScanJob called with payload:', payload);
    try {
      const response = await axios.post(`${API_CORE_URL}/scan-jobs/`, payload);
      console.log('api.js: createScanJob successful, response data:', response.data);
      return response.data;
    } catch (error) {
      console.error('api.js: Error in createScanJob:', error.response?.data || error.message);
      throw error; // Re-throw to be caught by the calling component
    }
  },

};

export default api; 