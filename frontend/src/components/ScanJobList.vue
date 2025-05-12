<template>
  <div class="scan-job-list-container">
    <div v-if="!selectedJobId">
      <div class="scan-job-list" v-if="isLoggedIn">
        <h3>Past Scan Jobs</h3>
        <button @click="fetchScanJobs(1)" :disabled="isLoading">{{ isLoading ? 'Refreshing...' : 'Refresh List' }}</button>
        
        <div v-if="isLoading" class="loading-message">Loading scan jobs...</div>
        <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>

        <div v-if="scanJobs.length > 0 && !isLoading" class="job-list-items">
          <ul>
            <li v-for="job in scanJobs" :key="job.id" class="job-item">
              <div class="job-summary">
                <p><strong>Job ID:</strong> {{ job.id }} (Celery Task: {{ job.celery_task_id || 'N/A' }})</p>
                <p><strong>Project:</strong> {{ job.project_name }}</p>
                <p><strong>Initiator:</strong> {{ job.initiator_username }}</p>
                <p><strong>Status:</strong> <span :class="`status-${job.status.toLowerCase()}`">{{ job.status }}</span></p>
                <p><strong>Created:</strong> {{ formatDate(job.created_at) }}</p>
                <p v-if="job.completed_timestamp"><strong>Completed:</strong> {{ formatDate(job.completed_timestamp) }}</p>
              </div>
              <div class="job-actions">
                <button @click="viewJobDetails(job.id)">View Details</button>
              </div>
              <div class="job-results-preview" v-if="job.results && job.results.length > 0">
                <h4>Results Preview ({{ job.results.length }} tool(s)):</h4>
                <ul>
                  <li v-for="result in job.results" :key="result.id" class="result-item-preview">
                    <strong>{{ result.tool_name }}:</strong> 
                    <span v-if="result.summary_data && typeof result.summary_data.findings_count === 'number'">
                        {{ result.summary_data.findings_count }} findings
                    </span>
                    <span v-else-if="result.summary_data && typeof result.summary_data.HIGH === 'number'">
                        {{ (result.summary_data.HIGH || 0) + (result.summary_data.MEDIUM || 0) + (result.summary_data.LOW || 0) }} findings
                    </span>
                    <span v-else-if="result.findings && result.findings.length > 0">
                        {{ result.findings.length }} findings
                    </span>
                    <span v-else-if="result.error_message">Error</span>
                    <span v-else>No findings data</span>
                  </li>
                </ul>
              </div>
              <div v-else class="no-results-message">
                No results preview available for this job.
              </div>
            </li>
          </ul>
          <div v-if="pagination.totalPages > 1" class="pagination-controls">
                <button @click="fetchScanJobs(pagination.currentPage - 1)" :disabled="!pagination.previousPageUrl">Previous</button>
                <span>Page {{ pagination.currentPage }} of {{ pagination.totalPages }} ({{pagination.count}} items)</span>
                <button @click="fetchScanJobs(pagination.currentPage + 1)" :disabled="!pagination.nextPageUrl">Next</button>
            </div>
        </div>
        <div v-else-if="!isLoading && !errorMessage" class="info-message">
          No scan jobs found.
        </div>
      </div>
    </div>
    <div v-else>
      <ScanJobDetail :scanJobId="selectedJobId" @close-detail="closeJobDetails" @session-expired="handleSessionExpired" />
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import ScanJobDetail from './ScanJobDetail.vue'; // Import the new component

const API_SCAN_JOBS_URL = '/api/v1/core/scan-jobs/';

export default {
  name: 'ScanJobList',
  components: {
    ScanJobDetail // Register the component
  },
  props: {
    isLoggedIn: {
      type: Boolean,
      required: true
    }
  },
  data() {
    return {
      scanJobs: [],
      isLoading: false,
      errorMessage: null,
      selectedJobId: null, // To store the ID of the job being viewed
      pagination: {
        currentPage: 1,
        totalPages: 1,
        nextPageUrl: null,
        previousPageUrl: null,
        count: 0,
        pageSize: 10 // Default, will be updated from API or config if possible
      }
    };
  },
  watch: {
    isLoggedIn: {
      immediate: true,
      handler(isLoggedIn) {
        if (isLoggedIn) {
          this.fetchScanJobs();
        } else {
          this.scanJobs = [];
          this.errorMessage = null;
          this.selectedJobId = null;
          this.resetPagination();
        }
      }
    }
  },
  methods: {
    resetPagination(){
        this.pagination = {
            currentPage: 1,
            totalPages: 1,
            nextPageUrl: null,
            previousPageUrl: null,
            count:0,
            pageSize: this.pagination.pageSize // retain configured page size
        };
    },
    formatDate(dateString) {
      if (!dateString) return 'N/A';
      try {
        return new Date(dateString).toLocaleString();
      } catch (e) {
        return dateString;
      }
    },
    async fetchScanJobs(page = 1) {
      if (!this.isLoggedIn) return;
      this.isLoading = true;
      this.errorMessage = null;
      try {
        // Adjust if your API uses a different param for page size, e.g., `size` or `limit`
        const response = await axios.get(`${API_SCAN_JOBS_URL}?page=${page}&page_size=${this.pagination.pageSize}`);
        this.scanJobs = response.data.results;
        this.pagination.count = response.data.count;
        this.pagination.nextPageUrl = response.data.next;
        this.pagination.previousPageUrl = response.data.previous;
        this.pagination.currentPage = page;
        this.pagination.totalPages = Math.ceil(response.data.count / this.pagination.pageSize);
        if (this.pagination.totalPages < page && page > 1) {
            // If current page is out of bounds after a refresh (e.g. items deleted), fetch first page
            await this.fetchScanJobs(1);
        }

      } catch (error) {
        console.error('Error fetching scan jobs:', error);
        this.errorMessage = 'Failed to load scan jobs.';
        if (error.response && error.response.status === 401) {
          this.$emit('session-expired');
        }
      } finally {
        this.isLoading = false;
      }
    },
    viewJobDetails(jobId) {
      this.selectedJobId = jobId;
    },
    closeJobDetails() {
      this.selectedJobId = null;
      // Optionally, refresh the list in case status changed, or rely on user to refresh
      // this.fetchScanJobs(this.pagination.currentPage);
    },
    handleSessionExpired() {
        this.$emit('session-expired');
    }
  },
  emits: ['session-expired']
};
</script>

<style scoped>
.scan-job-list-container {
  /* Styles for the main container if needed */
}
.scan-job-list {
  margin-top: 20px;
  padding: 20px;
  border: 1px solid #17a2b8; /* Info color */
  border-radius: 8px;
  background-color: #eefbfc;
}
.scan-job-list h3 {
  margin-top: 0;
  color: #0c5460;
  text-align: center;
}
.job-list-items ul {
  list-style-type: none;
  padding: 0;
}
.job-item {
  background-color: #fff;
  border: 1px solid #ddd;
  padding: 15px;
  margin-bottom: 15px;
  border-radius: 6px;
}
.job-summary p {
  margin: 5px 0;
  font-size: 0.95em;
}
.job-summary strong {
  color: #333;
}
.job-actions {
    margin-top: 10px;
    margin-bottom: 10px;
}
.job-actions button {
    padding: 8px 12px;
    background-color: #007bff;
    color: white;
    border:none;
    border-radius: 4px;
    cursor: pointer;
}
.job-actions button:hover {
    background-color: #0056b3;
}

.job-results-preview {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #eee;
}
.job-results-preview h4 {
  margin-top: 0;
  margin-bottom: 8px;
  font-size: 0.9em;
  color: #555;
}
.job-results-preview ul {
  list-style-type: disc;
  padding-left: 20px;
  font-size: 0.85em;
}
.result-item-preview {
    margin-bottom: 3px;
}
.no-results-message {
    font-style: italic;
    color: #777;
    font-size: 0.85em;
    margin-top:10px;
}

/* Status specific styling */
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
.loading-message { background-color: #f0f0f0; color: #333; }
.error-message { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
.info-message { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }

.pagination-controls {
    margin-top: 20px;
    text-align: center;
}
.pagination-controls button {
    margin: 0 5px;
    padding: 5px 10px;
    background-color: #6c757d;
    color:white;
    border:none;
    border-radius:4px;
}
.pagination-controls button:disabled {
    background-color: #ccc;
    cursor: not-allowed;
}
.pagination-controls button:hover:not(:disabled) {
    background-color: #5a6268;
}
.pagination-controls span {
    margin: 0 10px;
    font-size: 0.9em;
}
</style> 