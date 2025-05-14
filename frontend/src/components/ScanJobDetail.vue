<template>
  <div class="scan-job-detail" v-if="scanJobId">
    <button @click="$emit('close-detail')" class="close-button">Back to List</button>
    <h3>Scan Job Details (ID: {{ scanJobId }})</h3>

    <div v-if="isLoading" class="loading-message">Loading job details...</div>
    <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>

    <div v-if="job && !isLoading" class="job-information">
      <h4>Summary</h4>
      <p><strong>Project:</strong> {{ job.project_name }}</p>
      <p><strong>Initiator:</strong> {{ job.initiator_username }}</p>
      <p><strong>Status:</strong> <span :class="`status-${job.status.toLowerCase()}`">{{ job.status }}</span></p>
      <p><strong>Celery Task ID:</strong> {{ job.celery_task_id || 'N/A' }}</p>
      <p><strong>Created:</strong> {{ formatDate(job.created_at) }}</p>
      <p v-if="job.started_timestamp"><strong>Started:</strong> {{ formatDate(job.started_timestamp) }}</p>
      <p v-if="job.completed_timestamp"><strong>Completed:</strong> {{ formatDate(job.completed_timestamp) }}</p>
      <p v-if="job.scan_configuration_name"><strong>Configuration:</strong> {{ job.scan_configuration_name }}</p>

      <h4>Results ({{ job.results ? job.results.length : 0 }} Tool(s))</h4>
      <div v-if="job.results && job.results.length > 0" class="results-container">
        <div v-for="result in job.results" :key="result.id" class="result-item">
          <h5>Tool: {{ result.tool_name }}</h5>
          <p v-if="result.error_message" class="tool-error"><strong>Error:</strong> {{ result.error_message }}</p>
          
          <div v-if="!result.error_message">
            <p><strong>Timestamp:</strong> {{ formatDate(result.timestamp) }}</p>
            
            <div v-if="result.summary_data">
              <strong>Summary:</strong>
              <ul>
                <li v-for="(value, key) in result.summary_data" :key="key">{{ key }}: {{ value }}</li>
              </ul>
            </div>

            <div v-if="result.findings && result.findings.length > 0">
              <strong>Findings ({{ result.findings.length }}):</strong>
              <ul class="findings-list">
                <li v-for="(finding, index) in result.findings" :key="index" class="finding-item">
                  <pre>{{ finding }}</pre>
                </li>
              </ul>
            </div>
            <div v-else-if="!result.summary_data && (!result.findings || result.findings.length === 0)">
              <p>No specific findings or summary data reported by this tool.</p>
            </div>

            <details v-if="result.raw_output" class="raw-output-details">
              <summary>View Raw Output</summary>
              <pre>{{ result.raw_output }}</pre>
            </details>
          </div>
        </div>
      </div>
      <div v-else class="info-message">
        No scan results are available for this job yet, or the scan did not produce any results.
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import Chart from 'chart.js/auto';

const API_SCAN_JOBS_URL = '/api/v1/core/scan-jobs/';

export default {
  name: 'ScanJobDetail',
  props: {
    scanJobId: {
      type: [String, Number],
      required: true
    }
  },
  data() {
    return {
      job: null,
      isLoading: false,
      errorMessage: null,
    };
  },
  watch: {
    scanJobId: {
      immediate: true,
      handler(newId) {
        if (newId) {
          this.fetchJobDetails();
        } else {
          this.job = null;
          this.errorMessage = null;
        }
      }
    }
  },
  methods: {
    formatDate(dateString) {
      if (!dateString) return 'N/A';
      try {
        return new Date(dateString).toLocaleString();
      } catch (e) {
        return dateString;
      }
    },
    async fetchJobDetails() {
      if (!this.scanJobId) return;
      this.isLoading = true;
      this.errorMessage = null;
      this.job = null; 
      try {
        const response = await axios.get(`${API_SCAN_JOBS_URL}${this.scanJobId}/`);
        this.job = response.data;
      } catch (error) {
        console.error(`Error fetching scan job details for ID ${this.scanJobId}:`, error);
        this.errorMessage = 'Failed to load scan job details.';
        if (error.response && error.response.status === 401) {
          this.$emit('session-expired');
        } else if (error.response && error.response.status === 404) {
            this.errorMessage = `Scan job with ID ${this.scanJobId} not found.`;
        }
      } finally {
        this.isLoading = false;
      }
    }
  },
  emits: ['close-detail', 'session-expired']
};
</script>

<style scoped>
.scan-job-detail {
  padding: 20px;
  border: 1px solid #007bff; /* Primary color */
  border-radius: 8px;
  background-color: #f8f9fa;
  margin-top: 20px;
  position: relative;
}
.close-button {
  position: absolute;
  top: 15px;
  right: 15px;
  padding: 8px 12px;
  background-color: #6c757d;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.close-button:hover {
  background-color: #5a6268;
}

.scan-job-detail h3, .scan-job-detail h4, .scan-job-detail h5 {
  color: #0056b3;
}
.scan-job-detail h3 {
  margin-top: 0;
  text-align: center;
  margin-bottom:20px;
}
.job-information p {
  margin: 8px 0;
  font-size: 0.95em;
}
.job-information strong {
  color: #343a40;
}

.results-container {
  margin-top: 15px;
}
.result-item {
  background-color: #fff;
  border: 1px solid #dee2e6;
  padding: 15px;
  margin-bottom: 15px;
  border-radius: 6px;
}
.result-item h5 {
  margin-top: 0;
  margin-bottom: 10px;
}
.tool-error {
  color: #dc3545;
  font-weight: bold;
}
.findings-list {
  list-style-type: none;
  padding-left: 0;
}
.finding-item {
  background-color: #f8f9fa;
  border: 1px solid #e9ecef;
  padding: 10px;
  margin-bottom: 8px;
  border-radius: 4px;
  font-size: 0.9em;
}
.finding-item pre, .raw-output-details pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  background-color: #e9ecef;
  padding: 10px;
  border-radius: 4px;
  max-height: 400px;
  overflow-y: auto;
}
.raw-output-details {
  margin-top: 10px;
}
.raw-output-details summary {
  cursor: pointer;
  color: #007bff;
  margin-bottom: 5px;
}

/* Status specific styling (consistent with ScanJobList) */
.status-pending { color: #ffc107; font-weight: bold; }
.status-queued { color: #fd7e14; font-weight: bold; }
.status-running { color: #007bff; font-weight: bold; }
.status-completed { color: #28a745; font-weight: bold; }
.status-failed { color: #dc3545; font-weight: bold; }
.status-cancelled, .status-timeout { color: #6c757d; font-weight: bold; }

.loading-message, .error-message, .info-message {
  padding: 10px;
  margin-top: 10px;
  border-radius: 4px;
  text-align: center;
}
.loading-message { background-color: #e9ecef; color: #495057; }
.error-message { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
.info-message { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
</style> 