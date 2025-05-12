<template>
  <div class="scan-configuration-manager">
    <h3>Scan Configuration Management</h3>
    <div v-if="!isLoggedIn" class="info-message">Please log in to manage scan configurations.</div>
    
    <div v-if="isLoggedIn">
      <div v-if="!selectedProjectId && !showCreateForm && !editingConfiguration" class="info-message">
        Please select a project in the Scan Runner section to see its configurations or to create a new one associated with it.
      </div>

      <div v-if="selectedProjectId && !showCreateForm && !editingConfiguration">
        <h4>Configurations for Project ID: {{ selectedProjectId }}</h4>
        
        <button @click="fetchConfigurations(selectedProjectId)" :disabled="isLoading" class="action-button">
          {{ isLoading ? 'Refreshing...' : 'Refresh Configurations' }}
        </button>
        <button @click="prepareCreateForm" :disabled="isLoading" class="action-button create-button">
          Create New Configuration for Project {{ selectedProjectId }}
        </button>

        <div v-if="isLoading" class="loading-message">Loading configurations...</div>
        <div v-if="errorMessage && !isLoading" class="error-message">{{ errorMessage }}</div>

        <div v-if="configurations.length > 0 && !isLoading" class="configurations-list">
          <ul>
            <li v-for="config in configurations" :key="config.id" class="config-item">
              <div class="config-details">
                <strong>{{ config.name }}</strong> (ID: {{ config.id }})
                <p>{{ config.description || 'No description' }}</p>
                <p>Targets: {{ config.has_predefined_targets ? 'Predefined by this config' : 'Manual input needed or not set' }}</p>
                <small>Tools: {{ config.tool_configurations_json ? 'Configured' : 'Default/Not Set' }}</small>
              </div>
              <div class="config-actions">
                <button @click="prepareEditForm(config)" class="action-button edit-button">Edit</button> 
                <button @click="deleteConfiguration(config.id)" :disabled="isDeleting === config.id" class="action-button delete-button">
                  {{ isDeleting === config.id ? 'Deleting...' : 'Delete' }}
                </button> 
              </div>
            </li>
          </ul>
        </div>
        <div v-if="configurations.length === 0 && !isLoading && !errorMessage" class="info-message">
          No scan configurations found for this project.
        </div>
      </div>

      <!-- Create/Edit Form -->
      <div v-if="showCreateForm || editingConfiguration" class="form-section">
        <hr class="separator"/>
        <h4>{{ formTitle }}</h4>
        <form @submit.prevent="saveConfiguration">
          <div class="form-group">
            <label for="config-name">Name:</label>
            <input type="text" id="config-name" v-model="configForm.name" required>
          </div>
          <div class="form-group">
            <label for="config-description">Description:</label>
            <textarea id="config-description" v-model="configForm.description"></textarea>
          </div>
          <div class="form-group">
            <label for="config-has-predefined-targets">
              <input type="checkbox" id="config-has-predefined-targets" v-model="configForm.has_predefined_targets">
              This configuration defines specific targets
            </label>
          </div>
          <div class="form-group" v-if="configForm.has_predefined_targets">
            <label for="config-target-details">Target Details (JSON):</label>
            <textarea id="config-target-details" v-model="configForm.target_details_json" rows="5" placeholder='e.g., {\n  "type": "git_repo",\n  "url": "https://github.com/user/repo.git",\n  "branch": "main",\n  "include_paths": ["src/"],\n  "exclude_paths": ["tests/"]\n}'></textarea>
            <small>Specify targets if 'has_predefined_targets' is checked. Otherwise, manual input will be required during scan run.</small>
          </div>
          <div class="form-group">
            <label for="config-tool-settings">Tool Configurations (JSON):</label>
            <textarea id="config-tool-settings" v-model="configForm.tool_configurations_json" rows="5" placeholder='e.g., {\n  "bandit": { "enabled": true, "severity_level": "MEDIUM" },\n  "semgrep": { "enabled": true, "rulesets": ["p/default"] }\n}'></textarea>
            <small>Define tool-specific settings. If empty, default tool behavior will apply.</small>
          </div>
           <div v-if="formErrorMessage" class="error-message">{{ formErrorMessage }}</div>
          <div class="form-actions">
            <button type="submit" :disabled="isSaving" class="action-button save-button">
              {{ isSaving ? 'Saving...' : (editingConfiguration ? 'Update Configuration' : 'Create Configuration') }}
            </button>
            <button type="button" @click="cancelEditOrCreate" :disabled="isSaving" class="action-button cancel-button">Cancel</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

const API_CONFIGURATIONS_URL = '/api/core/scan-configurations/';

const initialConfigFormState = () => ({
  id: null,
  name: '',
  description: '',
  project: null, // Will be set from selectedProjectId prop
  has_predefined_targets: false,
  target_details_json: '', 
  tool_configurations_json: '' 
});

export default {
  name: 'ScanConfigurationManager',
  props: {
    isLoggedIn: {
      type: Boolean,
      required: true
    },
    selectedProjectId: {
      type: [String, Number],
      default: null
    }
  },
  data() {
    return {
      configurations: [],
      isLoading: false,
      errorMessage: null,
      formErrorMessage: null, 
      isSaving: false,
      isDeleting: null, // Stores ID of config being deleted
      showCreateForm: false,
      editingConfiguration: null, // Stores the full config object being edited for reference
      configForm: initialConfigFormState(),
    };
  },
  computed: {
    formTitle() {
      return this.editingConfiguration ? 'Edit Scan Configuration' : 'Create New Scan Configuration';
    }
  },
  watch: {
    selectedProjectId: {
      immediate: true,
      handler(newProjectId) {
        this.configurations = []; 
        this.errorMessage = null;
        this.cancelEditOrCreate(); // Also clears form and resets editing state
        if (newProjectId && this.isLoggedIn) {
          this.fetchConfigurations(newProjectId);
        } else if (!newProjectId && this.isLoggedIn){
          // this.errorMessage = "No project selected. Configurations cannot be loaded.";
          // Message is already in template
        }
      }
    },
    isLoggedIn(isLoggedInStatus) {
        if(isLoggedInStatus && this.selectedProjectId) {
            this.fetchConfigurations(this.selectedProjectId);
        } else if (!isLoggedInStatus) {
            this.configurations = [];
            this.errorMessage = null;
            this.cancelEditOrCreate();
        }
    }
  },
  methods: {
    async fetchConfigurations(projectId) {
      if (!projectId) {
        this.errorMessage = 'Cannot fetch configurations without a Project ID.';
        return;
      }
      this.isLoading = true;
      this.errorMessage = null;
      try {
        const response = await axios.get(`${API_CONFIGURATIONS_URL}?project=${projectId}`);
        this.configurations = response.data.results; 
      } catch (error) {
        console.error(`Error fetching configurations for project ${projectId}:`, error);
        this.errorMessage = 'Failed to load scan configurations.';
        if (error.response && error.response.status === 401) {
          this.$emit('session-expired');
        }
      } finally {
        this.isLoading = false;
      }
    },
    prepareCreateForm() {
        if (!this.selectedProjectId) {
            this.errorMessage = "Please select a project first to create a configuration for it.";
            return;
        }
        this.editingConfiguration = null;
        this.configForm = {
            ...initialConfigFormState(),
            project: this.selectedProjectId
        };
        this.showCreateForm = true;
        this.formErrorMessage = null;
    },
    prepareEditForm(config) {
      this.editingConfiguration = config; // Store the original config object
      this.configForm = { // Populate form with its data
        id: config.id,
        name: config.name,
        description: config.description || '',
        project: config.project, 
        has_predefined_targets: config.has_predefined_targets || false,
        target_details_json: config.target_details_json || '',
        tool_configurations_json: config.tool_configurations_json || ''
      };
      this.showCreateForm = false; // Ensure create mode is off if edit is clicked
      this.formErrorMessage = null;
    },
    async deleteConfiguration(configId) {
      if (!confirm(`Are you sure you want to delete configuration ID ${configId}? This cannot be undone.`)) {
          return;
      }
      this.isDeleting = configId;
      this.errorMessage = null;
      this.formErrorMessage = null;
      try {
        await axios.delete(`${API_CONFIGURATIONS_URL}${configId}/`);
        this.configurations = this.configurations.filter(c => c.id !== configId);
        // If the deleted config was being edited, reset form
        if (this.editingConfiguration && this.editingConfiguration.id === configId) {
            this.cancelEditOrCreate();
        }
      } catch (error) {
        console.error(`Error deleting configuration ${configId}:`, error);
        this.errorMessage = `Failed to delete configuration. ${error.response?.data?.detail || error.message}`;
         if (error.response && error.response.status === 401) {
          this.$emit('session-expired');
        }
      } finally {
          this.isDeleting = null;
      }
    },
    async saveConfiguration() {
        this.isSaving = true;
        this.formErrorMessage = null;
        // Validate JSON fields before sending if they are not empty
        let targetDetailsPayload = null;
        if (this.configForm.has_predefined_targets && this.configForm.target_details_json.trim()) {
            try {
                targetDetailsPayload = JSON.parse(this.configForm.target_details_json);
            } catch (e) {
                this.formErrorMessage = "Target Details JSON is invalid.";
                this.isSaving = false;
                return;
            }
        } else if (this.configForm.has_predefined_targets && !this.configForm.target_details_json.trim()) {
            this.formErrorMessage = "Target Details JSON cannot be empty if 'This configuration defines specific targets' is checked.";
            this.isSaving = false;
            return;
        }

        let toolConfigsPayload = null;
        if (this.configForm.tool_configurations_json.trim()) {
            try {
                toolConfigsPayload = JSON.parse(this.configForm.tool_configurations_json);
            } catch (e) {
                this.formErrorMessage = "Tool Configurations JSON is invalid.";
                this.isSaving = false;
                return;
            }
        }

        const payload = {
            ...this.configForm,
            target_details_json: targetDetailsPayload, // Send parsed JSON or null
            tool_configurations_json: toolConfigsPayload, // Send parsed JSON or null
            project: this.configForm.project || this.selectedProjectId // Ensure project is set
        };

        try {
            if (this.editingConfiguration) { // Update (PUT)
                await axios.put(`${API_CONFIGURATIONS_URL}${this.editingConfiguration.id}/`, payload);
            } else { // Create (POST)
                await axios.post(API_CONFIGURATIONS_URL, payload);
            }
            await this.fetchConfigurations(this.selectedProjectId); // Refresh list
            this.cancelEditOrCreate(); // Close form and reset
        } catch (error) {
            console.error('Error saving configuration:', error);
            this.formErrorMessage = `Failed to save configuration. ${error.response?.data?.detail || JSON.stringify(error.response?.data) || error.message}`;
            if (error.response && error.response.status === 401) {
              this.$emit('session-expired');
            }
        } finally {
            this.isSaving = false;
        }
    },
    cancelEditOrCreate() {
        this.showCreateForm = false;
        this.editingConfiguration = null;
        this.configForm = initialConfigFormState();
        this.formErrorMessage = null;
    }
  },
  emits: ['session-expired']
};
</script>

<style scoped>
.scan-configuration-manager {
  padding: 20px;
  border: 1px solid #17a2b8; /* Info color for manager section */
  border-radius: 8px;
  background-color: #f4f8f9;
  margin-top: 20px;
}
.scan-configuration-manager h3, .scan-configuration-manager h4 {
  color: #0d6efd;
  text-align: center;
  margin-bottom: 15px;
}
.action-button {
  padding: 8px 12px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.95em;
  margin-right: 10px;
  margin-bottom: 10px; /* Spacing for buttons */
}
.action-button.create-button {
    background-color: #198754; /* Green for create */
}
.action-button.edit-button {
    background-color: #ffc107;
    color: #212529;
}
.action-button.delete-button {
    background-color: #dc3545;
}
.action-button.save-button {
    background-color: #198754;
}
.action-button.cancel-button {
    background-color: #6c757d; /* Grey for cancel */
}
.action-button:disabled {
  background-color: #adb5bd;
  cursor: not-allowed;
}
.action-button:hover:not(:disabled) {
  opacity: 0.85;
}

.configurations-list ul {
  list-style-type: none;
  padding: 0;
}
.config-item {
  background-color: #fff;
  border: 1px solid #dee2e6;
  padding: 15px;
  margin-bottom: 10px;
  border-radius: 6px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.config-details strong {
  display: block;
  font-size: 1.1em;
  margin-bottom: 5px;
}
.config-details p {
    margin: 3px 0;
    font-size: 0.9em;
    color: #555;
}
.config-details small {
    font-size: 0.8em;
    color: #777;
}
.config-actions button {
  margin-left: 8px;
  padding: 6px 10px;
  font-size: 0.9em;
}
.config-actions button:disabled {
    background-color: #e9ecef;
    color: #6c757d;
    border-color: #ced4da;
}

.loading-message, .error-message, .info-message {
  padding: 10px;
  margin-top: 10px;
  border-radius: 4px;
  text-align: center;
}
.loading-message { background-color: #e9ecef; color: #495057; }
.error-message { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
.info-message { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }

.separator {
  margin: 20px 0;
  border: 0;
  border-top: 1px solid #dee2e6;
}

/* Form Specific Styles */
.form-section {
    background-color: #fff;
    padding: 20px;
    border: 1px solid #ccc;
    border-radius: 8px;
    margin-top: 20px;
}
.form-group {
  margin-bottom: 15px;
}
.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}
.form-group input[type="text"],
.form-group textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  box-sizing: border-box;
}
.form-group input[type="checkbox"] {
    margin-right: 8px;
    vertical-align: middle;
}
.form-group small {
    display: block;
    margin-top: 5px;
    font-size: 0.85em;
    color: #6c757d;
}
.form-actions {
    margin-top: 20px;
    text-align: right;
}
</style> 