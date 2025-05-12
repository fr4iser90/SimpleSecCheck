<template>
  <div class="project-configurations">
    <h3>Scan Configurations for Project: {{ project ? project.name : 'Loading...' }}</h3>
    
    <div v-if="isLoadingProject || isLoadingConfigurations" class="loading-message">Loading configuration data...</div>
    <div v-if="projectLoadError" class="error-message">Error loading project details: {{ projectLoadError }}</div>
    <div v-if="configurationsLoadError" class="error-message">Error loading configurations: {{ configurationsLoadError }}</div>

    <div v-if="project && !isLoadingProject">
      <div class="actions mb-3">
        <button v-if="canCreateConfiguration" @click="showCreateModal = true" class="btn btn-primary">
          Create New Scan Configuration
        </button>
        <p v-else-if="selectedProjectUserRole !== null" class="text-muted">
          Your role ({{ selectedProjectUserRole }}) does not permit creating new scan configurations for this project. (Requires Developer or higher).
        </p>
      </div>

      <div v-if="configurations.length === 0 && !isLoadingConfigurations" class="info-message">
        No scan configurations found for this project.
      </div>

      <ul v-else class="list-group">
        <li v-for="config in configurations" :key="config.id" class="list-group-item d-flex justify-content-between align-items-center">
          <div>
            <strong>{{ config.name }}</strong>
            <small class="text-muted d-block">ID: {{ config.id }}</small>
            <small class="d-block">{{ config.description || 'No description' }}</small>
            <span v-if="config.has_predefined_targets" class="badge badge-info mt-1">Uses Predefined Targets</span>
          </div>
          <div class="config-actions">
            <button v-if="canManageConfiguration(config)" @click="editConfiguration(config)" class="btn btn-sm btn-warning mr-2">Edit</button>
            <button v-if="canManageConfiguration(config)" @click="confirmDeleteConfiguration(config)" class="btn btn-sm btn-danger">Delete</button>
            <span v-else-if="selectedProjectUserRole !== null" class="text-muted small">
              Role ({{ selectedProjectUserRole }}) insufficient to manage. (Requires Manager or higher).
            </span>
          </div>
        </li>
      </ul>
    </div>

    <!-- Modals for Create/Edit -->
    <ConfigurationFormModal
      v-if="showCreateModal || (showEditModal && editingConfig)"
      :initial-config="editingConfig"
      :project-id="projectId"
      :is-editing="showEditModal"
      @close="closeModal"
      @save="handleSaveConfiguration"
    />

    <!-- Delete Confirmation Modal (Simplified) -->
    <div v-if="showDeleteConfirmModal && deletingConfig" class="modal-backdrop">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Confirm Deletion</h5>
            <button type="button" class="close" @click="showDeleteConfirmModal = false">&times;</button>
          </div>
          <div class="modal-body">
            <p>Are you sure you want to delete scan configuration "<strong>{{ deletingConfig.name }}</strong>" (ID: {{ deletingConfig.id }})?</p>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showDeleteConfirmModal = false">Cancel</button>
            <button type="button" class="btn btn-danger" @click="executeDeleteConfiguration">Delete</button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
import api from '../services/api'; // Use the new api service
import ConfigurationFormModal from './ConfigurationFormModal.vue';

export default {
  name: 'ProjectConfigurations',
  components: {
    ConfigurationFormModal,
  },
  props: {
    projectId: {
      type: [Number, String],
      required: true,
    },
    currentUser: { // Expected: { id: Number, username: String, ... }
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      project: null,
      isLoadingProject: false,
      projectLoadError: null,
      
      configurations: [],
      isLoadingConfigurations: false,
      configurationsLoadError: null,
      
      selectedProjectUserRole: null, // 'owner', 'manager', 'developer', 'viewer', or null

      showCreateModal: false,
      showEditModal: false,
      editingConfig: null, // Config object being edited

      showDeleteConfirmModal: false,
      deletingConfig: null, // Config object to be deleted
    };
  },
  computed: {
    canCreateConfiguration() {
      if (!this.project || !this.currentUser || !this.selectedProjectUserRole) return false;
      return ['owner', 'manager', 'developer'].includes(this.selectedProjectUserRole);
    },
  },
  watch: {
    projectId: {
      immediate: true,
      handler(newId) {
        if (newId) {
          this.fetchProjectDetails();
          this.fetchConfigurations();
        } else {
          this.project = null;
          this.configurations = [];
          this.selectedProjectUserRole = null;
        }
      },
    },
  },
  methods: {
    async fetchProjectDetails() {
      if (!this.projectId) return;
      this.isLoadingProject = true;
      this.projectLoadError = null;
      try {
        // const response = await axios.get(`/api/core/projects/${this.projectId}/`);
        this.project = await api.getProject(this.projectId);
        this.determineUserRoleForProject();
      } catch (error) {
        console.error(`Error fetching project ${this.projectId} details:`, error);
        this.projectLoadError = error.response?.data?.detail || 'Failed to load project details.';
        this.project = null;
        this.selectedProjectUserRole = null;
      } finally {
        this.isLoadingProject = false;
      }
    },
    determineUserRoleForProject() {
      if (!this.project || !this.currentUser || !this.currentUser.id) {
        this.selectedProjectUserRole = null;
        return;
      }
      if (this.project.owner && this.project.owner.id === this.currentUser.id) {
        this.selectedProjectUserRole = 'owner';
        return;
      }
      if (this.project.project_memberships && this.project.project_memberships.length > 0) {
        const membership = this.project.project_memberships.find(
          m => m.user.id === this.currentUser.id
        );
        if (membership) {
          this.selectedProjectUserRole = membership.role;
          return;
        }
      }
      this.selectedProjectUserRole = null; // User is not owner or member
    },
    async fetchConfigurations() {
      if (!this.projectId) return;
      this.isLoadingConfigurations = true;
      this.configurationsLoadError = null;
      try {
        // const response = await axios.get(`/api/core/scan-configurations/?project=${this.projectId}`);
        const data = await api.getScanConfigurations(this.projectId);
        this.configurations = data.results || data; // Adapt based on API response structure (assuming pagination for .results)
      } catch (error) {
        console.error(`Error fetching configurations for project ${this.projectId}:`, error);
        this.configurationsLoadError = error.response?.data?.detail || 'Failed to load configurations.';
        this.configurations = [];
      } finally {
        this.isLoadingConfigurations = false;
      }
    },
    canManageConfiguration(config) { 
      if (!this.project || !this.currentUser || !this.selectedProjectUserRole) return false;
      return ['owner', 'manager'].includes(this.selectedProjectUserRole);
    },
    editConfiguration(config) {
      this.editingConfig = { ...config };
      this.showEditModal = true;
      this.showCreateModal = false;
    },
    confirmDeleteConfiguration(config) {
      this.deletingConfig = config;
      this.showDeleteConfirmModal = true;
    },
    async executeDeleteConfiguration() {
      if (!this.deletingConfig) return;
      try {
        // await axios.delete(`/api/core/scan-configurations/${this.deletingConfig.id}/`);
        await api.deleteScanConfiguration(this.deletingConfig.id);
        this.configurations = this.configurations.filter(c => c.id !== this.deletingConfig.id);
        // Optionally, show a success message
        alert('Configuration deleted successfully.');
      } catch (error) {
        console.error(`Error deleting configuration ${this.deletingConfig.id}:`, error);
        alert(`Failed to delete configuration: ${error.response?.data?.detail || error.message}`);
      } finally {
        this.showDeleteConfirmModal = false;
        this.deletingConfig = null;
      }
    },
    closeModal() {
      this.showCreateModal = false;
      this.showEditModal = false;
      this.editingConfig = null;
    },
    handleSaveConfiguration(savedConfig) {
      this.fetchConfigurations(); // Re-fetch to get the latest list
      this.closeModal();
    },
  },
  mounted() {
    // Data fetching is triggered by watch on projectId
  }
};
</script>

<style scoped>
.project-configurations {
  padding: 20px;
  background-color: #f8f9fa;
  border-radius: 5px;
}
.loading-message, .error-message, .info-message {
  padding: 10px;
  margin-bottom: 15px;
  border-radius: 4px;
}
.loading-message { background-color: #e9ecef; color: #495057; border: 1px solid #ced4da; }
.error-message { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
.info-message { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }

.list-group-item {
  margin-bottom: 10px;
  border-radius: 5px;
}
.config-actions .btn {
  margin-left: 5px; /* Spacing between buttons */
}
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1050;
}
.modal-dialog {
  background-color: white;
  padding: 20px;
  border-radius: 5px;
  min-width: 300px;
  max-width: 500px;
  box-shadow: 0 5px 15px rgba(0,0,0,0.5);
}
.modal-header, .modal-body, .modal-footer {
  padding: 1rem;
}
.modal-header {
  border-bottom: 1px solid #dee2e6;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modal-footer {
  border-top: 1px solid #dee2e6;
  display: flex;
  justify-content: flex-end;
}
.modal-footer .btn {
  margin-left: 0.5rem;
}
.close {
  border: none;
  background: none;
  font-size: 1.5rem;
  font-weight: bold;
  line-height: 1;
  opacity: 0.5;
}
.close:hover {
  opacity: 0.75;
}
.mb-3 { margin-bottom: 1rem !important; }
.mr-2 { margin-right: 0.5rem !important; }
.mt-1 { margin-top: 0.25rem !important; }
.d-block { display: block !important; }
.d-flex { display: flex !important; }
.justify-content-between { justify-content: space-between !important; }
.align-items-center { align-items: center !important; }
.text-muted { color: #6c757d !important; }

/* Basic Bootstrap-like button styling for example purposes */
.btn {
  display: inline-block;
  font-weight: 400;
  color: #212529;
  text-align: center;
  vertical-align: middle;
  cursor: pointer;
  user-select: none;
  background-color: transparent;
  border: 1px solid transparent;
  padding: 0.375rem 0.75rem;
  font-size: 1rem;
  line-height: 1.5;
  border-radius: 0.25rem;
  transition: color 0.15s ease-in-out, background-color 0.15s ease-in-out, border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
}
.btn-primary { color: #fff; background-color: #007bff; border-color: #007bff; }
.btn-primary:hover { background-color: #0056b3; border-color: #0056b3; }
.btn-warning { color: #212529; background-color: #ffc107; border-color: #ffc107; }
.btn-warning:hover { background-color: #e0a800; border-color: #e0a800; }
.btn-danger { color: #fff; background-color: #dc3545; border-color: #dc3545; }
.btn-danger:hover { background-color: #c82333; border-color: #c82333; }
.btn-secondary { color: #fff; background-color: #6c757d; border-color: #6c757d; }
.btn-secondary:hover { background-color: #545b62; border-color: #545b62; }
.btn-sm { padding: 0.25rem 0.5rem; font-size: 0.875rem; line-height: 1.5; border-radius: 0.2rem; }

.badge {
    display: inline-block;
    padding: .35em .65em;
    font-size: .75em;
    font-weight: 700;
    line-height: 1;
    color: #fff;
    text-align: center;
    white-space: nowrap;
    vertical-align: baseline;
    border-radius: .25rem;
}
.badge-info { background-color: #17a2b8; }
</style> 