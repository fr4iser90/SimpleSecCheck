<template>
  <div class="scan-runner">
    <h2>Trigger Sample Scan</h2>
    <div v-if="!isLoggedIn" class="info-message">Please log in to trigger scans.</div>
    
    <div v-if="isLoggedIn">
      <h3>Run a New Scan</h3>
      
      <div class="form-group">
        <label for="project-select">Select Project:</label>
        <select id="project-select" :value="selectedProjectId" @change="handleProjectSelectionChange" :disabled="isLoadingProjects || triggeringScan">
          <option :value="null" disabled>{{ isLoadingProjects ? 'Loading projects...' : (projectLoadError ? 'Error loading projects' : '-- Select a Project --') }}</option>
          <option v-for="project in projectList" :key="project.id" :value="project.id">
            {{ project.name }} (ID: {{ project.id }})
          </option>
        </select>
        <div v-if="isLoadingProjects" class="loading-inline">Loading...</div>
        <div v-if="projectLoadError" class="error-inline">{{ projectLoadError }}</div>
      </div>

      <div v-if="selectedProjectId">
        <div v-if="!canTriggerScan" class="error-message">
          You do not have sufficient permissions (Developer, Manager, or Owner) to trigger scans for the selected project: <strong>{{ selectedProject ? selectedProject.name : '' }}</strong>.
        </div>

        <div class="form-group">
          <label for="config-select">Select Scan Configuration (uses Project Default if none selected):</label>
          <select id="config-select" v-model="selectedConfigurationId" :disabled="configurationsLoading || triggeringScan || !canTriggerScan">
            <option :value="null">{{ configurationsLoading ? 'Loading configurations...' : (configurationsError ? 'Error loading configurations' : '-- Use Project Default Configuration --') }}</option>
            <option v-for="config in scanConfigurations" :key="config.id" :value="config.id">
              {{ config.name }} <span v-if="config.has_predefined_targets">(uses predefined targets)</span> (ID: {{ config.id }})
            </option>
          </select>
          <div v-if="configurationsLoading" class="loading-inline">Loading...</div>
          <div v-if="configurationsError" class="error-inline">{{ configurationsError }}</div>
           <div v-if="!configurationsLoading && !configurationsError && scanConfigurations.length === 0 && selectedProjectId" class="info-inline">
              No specific configurations found for this project. The Project Default Configuration will be used.
          </div>
        </div>

        <button @click="triggerScan" :disabled="triggeringScan || !selectedProjectId || !canTriggerScan" class="action-button">
          {{ triggeringScan ? 'Starting Scan...' : 'Trigger Scan' }}
        </button>
        <div v-if="scanTriggerError" class="error-message">{{ scanTriggerError }}</div>
      </div>

      <div v-if="initiatedJob" class="initiated-job-info">
        <h4>Scan Initiated Successfully!</h4>
        <p><strong>Job ID:</strong> {{ initiatedJob.id }}</p>
        <p><strong>Project:</strong> {{ initiatedJob.project_name }}</p>
        <p><strong>Status:</strong> <span :class="`status-${initiatedJob.status.toLowerCase()}`">{{ initiatedJob.status }}</span></p>
        <p><strong>Celery Task ID:</strong> {{ initiatedJob.celery_task_id }}</p>
        <p><strong>Configuration:</strong> {{ initiatedJob.scan_configuration_name || 'Project Default Configuration' }}</p>
        <p><strong>Targets:</strong> {{ initiatedJob.scan_configuration_name ? 'Defined by selected configuration' : 'Defined by Project Default Configuration' }}</p>
        <button @click="refreshJobStatus(initiatedJob.id)" :disabled="checkingJobStatus" class="action-button">
          {{ checkingJobStatus ? 'Refreshing...' : 'Refresh Job Status' }}
        </button>
        <div v-if="jobStatusError" class="error-message">{{ jobStatusError }}</div>
      </div>
    </div>

    <hr />

    <h2>Check Existing Scan Status</h2>
    <form @submit.prevent="checkCeleryTaskStatusManually">
      <div>
        <label for="task-id-check">Celery Task ID:</label>
        <input type="text" id="task-id-check" v.model="taskIdToCheck" placeholder="Enter Celery Task ID" required />
      </div>
      <button type="submit" :disabled="checkingStatus">
        {{ checkingStatus ? 'Checking Task...' : 'Check Celery Task Status' }}
      </button>
    </form>

    <div v-if="scanResultDetails" class="scan-result-section">
      <h3>Details for Celery Task: {{ scanResultDetails.task_id }}</h3>
      <p>Celery Status: <strong>{{ scanResultDetails.status }}</strong></p>
      <div v-if="scanResultDetails.result">
        <h4>Celery Result:</h4>
        <pre>{{ scanResultDetails.result }}</pre>
      </div>
      <div v-if="scanResultDetails.scan_job_details && typeof scanResultDetails.scan_job_details === 'object'">
        <h4>Associated Scan Job: {{ scanResultDetails.scan_job_details.id }}</h4>
        <p>Project: {{ scanResultDetails.scan_job_details.project_name }}</p>
        <p>Job Status: {{ scanResultDetails.scan_job_details.status }}</p>
        <pre>Full Job Details: {{ scanResultDetails.scan_job_details }}</pre>
      </div>
       <div v-else-if="scanResultDetails.scan_job_details">
        <p>Scan Job Details: {{ scanResultDetails.scan_job_details }}</p> 
      </div>
    </div>
    
    <div v-if="errorMessage" class="error-message">
      <p>{{ errorMessage }}</p>
    </div>
  </div>
</template>

<script>
// import axios from 'axios'; // No longer direct axios
import api from '../services/api'; // Import the new api service

// const API_CORE_URL = '/api/core'; // No longer needed

export default {
  name: 'ScanRunner',
  props: {
    isLoggedIn: {
        type: Boolean,
        required: true
    },
    currentUser: Object, // Expected: { id: Number, username: String, ... }
    projects: { // Prop to receive projects from App.vue
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      selectedProject: null,
      projectList: [], // This will now be primarily populated by the prop
      isLoadingProjects: false,
      projectLoadError: null,

      scanConfigurations: [],
      selectedConfigurationId: null,
      configurationsLoading: false,
      configurationsError: null,
      
      triggeringScan: false,
      scanTriggerError: null,
      initiatedJob: null,
      
      taskIdToCheck: '',
      checkingStatus: false,
      scanResultDetails: null,
      
      errorMessage: null,
      statusPollInterval: null,

      jobStatusError: null,
      checkingJobStatus: false,
    };
  },
  computed: {
    selectedConfiguration() {
      if (!this.selectedConfigurationId) return null;
      return this.scanConfigurations.find(config => config.id === this.selectedConfigurationId);
    },
    selectedProjectId() {
      return this.selectedProject ? this.selectedProject.id : null;
    },
    userRoleInSelectedProject() {
      if (!this.selectedProject || !this.currentUser || !this.currentUser.id || !this.selectedProject.project_memberships) {
        return null;
      }
      const memberships = Array.isArray(this.selectedProject.project_memberships) ? this.selectedProject.project_memberships : [];
      const membership = memberships.find(
        m => m.user && typeof m.user.id !== 'undefined' && m.user.id === this.currentUser.id
      );

      if (membership) {
        return membership.role; 
      }
      if (this.selectedProject.owner && typeof this.selectedProject.owner.id !== 'undefined' && this.selectedProject.owner.id === this.currentUser.id) {
        return 'owner';
      }
      return null;
    },
    canTriggerScan() {
      if (!this.selectedProject || !this.isLoggedIn) {
        console.log('ScanRunner.vue: canTriggerScan check - no selectedProject or not logged in, returning false.');
        return false;
      }
      if (typeof this.selectedProject.can_trigger_scan === 'boolean') {
        console.log(`ScanRunner.vue: canTriggerScan check - using backend flag: ${this.selectedProject.can_trigger_scan}`);
        return this.selectedProject.can_trigger_scan;
      }
      
      console.log('ScanRunner.vue: canTriggerScan check - backend flag not present, using client-side role check.');
      if (!this.currentUser) {
        console.log('ScanRunner.vue: canTriggerScan fallback - no currentUser, returning false.');
        return false;
      }

      const role = this.userRoleInSelectedProject;
      console.log(`ScanRunner.vue: canTriggerScan fallback - userRoleInSelectedProject: ${role}`);
      const allowedRoles = ['owner', 'manager', 'developer'];
      const canScan = allowedRoles.includes(role);
      console.log(`ScanRunner.vue: canTriggerScan fallback - role allows scan: ${canScan}`);
      return canScan;
    }
  },
  watch: {
    isLoggedIn: {
      immediate: true,
      handler(isLoggedIn) {
        if (isLoggedIn) {
          console.log('ScanRunner.vue: isLoggedIn watcher fired, relying on projects prop.');
        } else {
          this.resetScanRunnerState();
        }
      }
    },
    projects: {
      handler(newProjects) {
        console.log('ScanRunner.vue: projects prop watcher triggered with:', JSON.parse(JSON.stringify(newProjects)));
        this.projectList = newProjects;
        this.isLoadingProjects = false;
        this.projectLoadError = null;
        console.log('ScanRunner.vue: projectList set to:', JSON.parse(JSON.stringify(this.projectList)));
        console.log('ScanRunner.vue: isLoadingProjects set to false, projectLoadError set to null');

        if (newProjects && newProjects.length > 0) {
        } else {
          this.selectedProject = null;
        }
      },
      immediate: true,
      deep: true
    },
    selectedProjectId(newProjectId, oldProjectId) {
      console.log(`ScanRunner.vue: WATCHER for selectedProjectId fired. New: ${newProjectId}, Old: ${oldProjectId}`);
      if (newProjectId !== oldProjectId) {
        this.$emit('project-selected', newProjectId);
        console.log(`ScanRunner.vue: selectedProjectId changed from ${oldProjectId} to ${newProjectId}, emitted 'project-selected'`); 
        this.selectedConfigurationId = null;
        this.scanConfigurations = [];
        this.configurationsError = null;
        this.initiatedJob = null;
        this.scanTriggerError = null;
        if (newProjectId) {
          this.fetchScanConfigurations(newProjectId);
        } else {
           this.scanConfigurations = [];
        }
      }
    },
    selectedConfigurationId(newConfigId, oldConfigId) {
        if (newConfigId !== oldConfigId) {
            this.scanTriggerError = null; 
        }
    },
  },
  created() {
  },
  methods: {
    handleProjectSelectionChange(event) {
      const projectId = parseInt(event.target.value, 10);
      if (isNaN(projectId)) {
          this.selectedProject = null;
      } else {
          this.selectedProject = this.projectList.find(p => p.id === projectId) || null;
      }
      console.log('ScanRunner.vue: handleProjectSelectionChange. New selected project object:', JSON.parse(JSON.stringify(this.selectedProject)));
    },
    async fetchProjects() {
      if (!this.isLoggedIn) {
        this.projectList = [];
        this.projectLoadError = 'User not logged in.';
        return;
      }
      this.isLoadingProjects = true;
      this.projectLoadError = null;
      try {
        const response = await api.getProjects();
        this.projectList = response.results || response;
        if (this.projectList.length === 0) {
          this.projectLoadError = 'No projects found or you don\'t have access to any.';
        }
      } catch (error) {
        console.error('Error fetching projects in ScanRunner:', error);
        this.projectLoadError = 'Failed to load projects. ' + (error.response?.data?.detail || error.message);
        this.projectList = [];
      } finally {
        this.isLoadingProjects = false;
      }
    },
    async fetchScanConfigurations(projectId) {
      if (!projectId) return;
      this.configurationsLoading = true;
      this.configurationsError = null;
      this.scanConfigurations = [];
      try {
        const data = await api.getScanConfigurations(projectId);
        this.scanConfigurations = data.results;
         if (!this.scanConfigurations || this.scanConfigurations.length === 0) {
        }
      } catch (error) {
        console.error(`Error fetching scan configurations for project ${projectId}:`, error);
        this.configurationsError = error.response?.data?.detail || 'Failed to load configurations.';
        if (error.response && error.response.status === 401) {
          this.$emit('session-expired');
        }
      } finally {
        this.configurationsLoading = false;
      }
    },
    async triggerScan() {
      if (!this.canTriggerScan) {
        this.scanTriggerError = 'You do not have sufficient permissions to trigger scans for this project.';
        console.error('ScanRunner.vue: TriggerScan called but canTriggerScan is false.');
        return;
      }

      this.triggeringScan = true;
      this.scanTriggerError = null;
      this.initiatedJob = null;
      this.clearPolling();

      const payload = {
        project: this.selectedProjectId,
        scan_configuration: this.selectedConfigurationId, // This can be null, backend handles it
      };

      console.log('ScanRunner.vue: Triggering scan with payload:', JSON.parse(JSON.stringify(payload)));

      try {
        const response = await api.createScanJob(payload); 
        this.initiatedJob = response; 
        console.log('ScanRunner.vue: Scan job created successfully:', JSON.parse(JSON.stringify(this.initiatedJob)));
        if (this.initiatedJob && this.initiatedJob.celery_task_id) {
          this.taskIdToCheck = this.initiatedJob.celery_task_id;
          this.pollCeleryTaskStatus(this.taskIdToCheck);
        } else if (this.initiatedJob) {
          console.warn('ScanRunner.vue: Scan job created, but no Celery task ID returned immediately. Status polling might not start.');
        }
      } catch (error) {
        console.error('ScanRunner.vue: Error triggering scan:', error);
        this.scanTriggerError = error.response?.data?.detail || error.response?.data?.error || error.message || 'Failed to trigger scan.';
        if (error.response?.data) {
            Object.keys(error.response.data).forEach(key => {
                console.error(`Backend validation error for ${key}: ${error.response.data[key]}`);
            });
        }
      } finally {
        this.triggeringScan = false;
      }
    },
    async checkCeleryTaskStatus(celeryTaskId) {
      if (!celeryTaskId) {
        this.errorMessage = 'Celery Task ID is required.';
        return;
      }
      this.checkingStatus = true;
      this.errorMessage = null;

      try {
        const data = await api.getCeleryTaskStatus(celeryTaskId);
        
        if (this.initiatedJob && this.initiatedJob.celery_task_id === celeryTaskId) {
            if (data.scan_job_details && typeof data.scan_job_details === 'object') {
                this.initiatedJob = { ...this.initiatedJob, ...data.scan_job_details, status: data.scan_job_details.status || this.initiatedJob.status };
            } else if (data.status) {
            }
        }
        
        if (this.taskIdToCheck === celeryTaskId && !this.statusPollInterval) {
             this.scanResultDetails = data;
        }

        const celeryStatus = data.status;
        if (celeryStatus === 'SUCCESS' || celeryStatus === 'FAILURE' || celeryStatus === 'REVOKED') {
            if (this.statusPollInterval && this.initiatedJob && this.initiatedJob.celery_task_id === celeryTaskId) {
                this.clearPolling();
            }
        }
      } catch (error) {
        console.error('Error checking Celery task status:', error);
        this.errorMessage = error.response?.data?.error || error.response?.data?.error_message || error.message || 'Failed to check task status.';
        this.clearPollingOnError(celeryTaskId);
      } finally {
        this.checkingStatus = false;
      }
    },
    checkCeleryTaskStatusManually() {
        this.scanResultDetails = null;
        this.clearPolling();
        this.checkCeleryTaskStatus(this.taskIdToCheck);
    },
    pollCeleryTaskStatus(celeryTaskId) {
      this.clearPolling();
      this.statusPollInterval = setInterval(async () => {
        if (!this.initiatedJob || this.initiatedJob.celery_task_id !== celeryTaskId) {
            this.clearPolling();
            return;
        }
        console.log(`Polling Celery task status for ${celeryTaskId}...`);
        await this.checkCeleryTaskStatus(celeryTaskId);
      }, 5000);
    },
    clearPolling() {
      if (this.statusPollInterval) {
        clearInterval(this.statusPollInterval);
        this.statusPollInterval = null;
      }
    },
    clearPollingOnError(celeryTaskIdCurrentlyPolling) {
        if (this.statusPollInterval && this.initiatedJob && this.initiatedJob.celery_task_id === celeryTaskIdCurrentlyPolling) {
            this.clearPolling();
        }
    },
    async refreshJobStatus(jobId) {
        if (!jobId) return;
        this.checkingJobStatus = true;
        this.jobStatusError = null;
        try {
            const data = await api.getScanJob(jobId);
            if (this.initiatedJob && this.initiatedJob.id === jobId) {
                this.initiatedJob = { ...this.initiatedJob, ...data }; 
            }
            if (data.celery_task_id) {
                await this.checkCeleryTaskStatus(data.celery_task_id);
            }
        } catch (error) {
            console.error(`Error refreshing job status for ${jobId}:`, error);
            this.jobStatusError = error.response?.data?.detail || 'Failed to refresh job status.';
            if (error.response && error.response.status === 401) {
                this.$emit('session-expired');
            }
        } finally {
            this.checkingJobStatus = false;
        }
    },
    resetScanRunnerState() {
      this.selectedProject = null;
      this.projectList = [];
      this.scanConfigurations = [];
      this.selectedConfigurationId = null;
      this.initiatedJob = null;
      this.scanTriggerError = null;
      this.projectLoadError = null;
      this.configurationsError = null;
      this.taskIdToCheck = '';
      this.scanResultDetails = null;
      this.errorMessage = null;
      this.clearPolling();
    },
    updateProjects(newProjects) {
      this.projectList = newProjects;
      if (this.projectList.length > 0) {
      } else {
        this.selectedProject = null;
      }
    }
  },
  beforeUnmount() {
    this.clearPolling();
  },
  emits: ['session-expired', 'project-selected']
};
</script>

<style scoped>
/* Add or modify styles as needed */
.scan-runner {
  max-width: 700px; /* Slightly wider */
  margin: 20px auto;
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 8px;
  font-family: sans-serif;
}
.form-group {
  margin-bottom: 15px;
  text-align: left;
}
.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}
.form-group input[type="text"],
.form-group select {
  width: 100%; /* Full width */
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-sizing: border-box; /* Include padding and border in element's total width and height */
}
.loading-inline, .error-inline {
    font-size: 0.9em;
    margin-top: 5px;
}
.loading-inline { color: #555; }
.error-inline { color: #d8000c; }

/* Other styles from previous version should be mostly compatible */
.scan-runner h2, .scan-runner h3 {
  color: #333;
  margin-top: 0;
  text-align: center;
}

.scan-runner button {
  padding: 10px 15px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
  margin-top: 10px; /* Add some margin for standalone buttons */
}

.scan-runner button:hover {
  background-color: #0056b3;
}

.scan-runner button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.scan-status-section, .scan-result-section {
  margin-top: 20px;
  padding: 15px;
  background-color: #f9f9f9;
  border: 1px solid #eee;
  border-radius: 4px;
  text-align: left;
}
.scan-result-section pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  background-color: #fff;
  padding: 10px;
  border: 1px solid #ddd;
  max-height: 300px; /* Limit height for large results */
  overflow-y: auto;  /* Add scroll for large results */
}

.error-message, .info-message {
  margin-top: 15px;
  padding: 10px;
  border-radius: 4px;
  text-align: left;
}
.error-message { background-color: #ffdddd; border: 1px solid #ffcccc; color: #d8000c; }
.info-message { background-color: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; }

hr {
  margin: 30px 0;
  border: 0;
  border-top: 1px solid #eee;
}

.initiated-job-info {
  background-color: #d4edda; /* Light green */
  border: 1px solid #c3e6cb;
  color: #155724;
  padding: 15px;
  margin-top: 20px;
}
.initiated-job-info h4 {
  margin-top: 0;
  color: #0f5132;
}
.initiated-job-info p {
  margin: 5px 0;
}

.action-button {
  padding: 10px 15px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
  display: block; /* Make button take full width of its container if alone */
  margin: 10px auto; /* Center button */
}
.action-button:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}
.action-button:hover:not(:disabled) {
  background-color: #0056b3;
}

.scan-status-checker {
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #dee2e6;
}

.task-status-result {
  background-color: #e2e3e5; /* Light grey */
  border: 1px solid #d6d8db;
  color: #383d41;
  padding: 15px;
  margin-top: 15px;
}
.task-status-result h4 {
  margin-top: 0;
}

.info-inline {
  color: #17a2b8;
  font-size: 0.9em;
  margin-top: 4px;
}
</style> 