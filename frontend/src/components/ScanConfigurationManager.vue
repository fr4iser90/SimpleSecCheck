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
            <div class="form-group">
              <label for="config-codebase-path-or-url">Codebase-Pfad oder -URL (optional):</label>
              <input type="text" id="config-codebase-path-or-url" v-model="configForm.codebase_path_or_url" placeholder="z.B. /pfad/zur/codebase oder git@github.com:user/repo.git">
            </div>
            <div class="form-group">
              <label for="config-web-app-url">Web-Anwendungs-URL (optional):</label>
              <input type="text" id="config-web-app-url" v-model="configForm.web_app_url" placeholder="z.B. https://example.com">
            </div>
            <small>Geben Sie hier die spezifischen Ziele für diese Konfiguration ein. Diese überschreiben ggf. die vom Projekt geerbten Standardziele.</small>
          </div>

          <!-- New Tool Configuration Section -->
          <fieldset class="tool-config-fieldset">
            <legend>Tool Configurations</legend>

            <!-- Semgrep -->
            <div class="tool-config-group">
              <label class="tool-enable-label">
                <input type="checkbox" v-model="configForm.tools.semgrep.enabled">
                Enable Semgrep
              </label>
              <div v-if="configForm.tools.semgrep.enabled" class="tool-options">
                <label for="semgrep-rulesets">Semgrep Rulesets (kommagetrennt):</label>
                <input type="text" id="semgrep-rulesets" v-model="configForm.tools.semgrep.rulesets" placeholder="z.B. p/ci,r/generic">
                <small>Standard: community-recommended (oft 'p/ci' oder leer lassen für Standard)</small>
              </div>
            </div>

            <!-- Trivy -->
            <div class="tool-config-group">
              <label class="tool-enable-label">
                <input type="checkbox" v-model="configForm.tools.trivy.enabled">
                Enable Trivy
              </label>
              <div v-if="configForm.tools.trivy.enabled" class="tool-options">
                <label for="trivy-scan-type">Trivy Scan Type:</label>
                <select id="trivy-scan-type" v-model="configForm.tools.trivy.scanType">
                  <option value="fs">Filesystem</option>
                  <option value="image">Image</option>
                  <option value="repo">Repository</option>
                  <option value="vuln">Vulnerability Database</option> <!-- Selten direkt hier konfiguriert -->
                </select>
                <label>Severity Levels (kommagetrennt):</label>
                <input type="text" v-model="configForm.tools.trivy.severity" placeholder="UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL">
                <small>Standard: HIGH,CRITICAL</small>
                 <label>
                  <input type="checkbox" v-model="configForm.tools.trivy.ignoreUnfixed">
                  Ignore Unfixed Vulnerabilities
                </label>
              </div>
            </div>

            <!-- ZAP (Placeholder for now) -->
            <div class="tool-config-group">
              <label class="tool-enable-label">
                <input type="checkbox" v-model="configForm.tools.zap.enabled" disabled>
                Enable ZAP (Konfiguration folgt)
              </label>
            </div>

          </fieldset>
          <!-- End of New Tool Configuration Section -->

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

const API_CONFIGURATIONS_URL = '/api/v1/core/scan-configurations/';

const initialConfigFormState = () => ({
  id: null,
  name: '',
  description: '',
  project: null, // Will be set from selectedProjectId prop
  has_predefined_targets: false,
  target_details_json: '', // Still needed for raw JSON if we revert, but UI will use new fields
  codebase_path_or_url: '', // New field for UI
  web_app_url: '',           // New field for UI
  tools: {
    semgrep: {
      enabled: false,
      rulesets: 'p/ci', // Standard-Regelsatz als Beispiel
    },
    trivy: {
      enabled: false,
      scanType: 'fs', // Standard Scan-Typ
      severity: 'HIGH,CRITICAL', // Standard Schweregrade
      ignoreUnfixed: false,
    },
    zap: {
      enabled: false,
      // Weitere ZAP spezifische einfache Felder hier...
    }
  }
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
    },
    selectedProject: { // New prop for the full project object
      type: Object,
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
        console.log('ScanConfigurationManager.vue: Watcher for selectedProjectId triggered. New value:', newProjectId);
        this.configurations = []; 
        this.errorMessage = null;
        this.cancelEditOrCreate(); // Also clears form and resets editing state
        if (newProjectId && this.isLoggedIn) {
          console.log('ScanConfigurationManager.vue: Valid projectId and logged in. Fetching configurations for project ID:', newProjectId);
          this.fetchConfigurations(newProjectId);
        } else if (!newProjectId && this.isLoggedIn){
          console.log('ScanConfigurationManager.vue: selectedProjectId is now null. No configurations will be fetched.');
          // this.errorMessage = "No project selected. Configurations cannot be loaded.";
          // Message is already in template
        } else {
          console.log('ScanConfigurationManager.vue: Conditions not met to fetch configurations (isLoggedIn:', this.isLoggedIn, ', newProjectId:', newProjectId, ')');
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
        
        // Pre-fill from selectedProject if available
        let initialCodebase = '';
        let initialWebAppUrl = '';
        let initialHasTargets = false;

        if (this.selectedProject) {
            initialCodebase = this.selectedProject.codebase_path_or_url || '';
            initialWebAppUrl = this.selectedProject.web_app_url || '';
            if (initialCodebase || initialWebAppUrl) {
                initialHasTargets = true;
            }
        }

        this.configForm = {
            ...initialConfigFormState(),
            project: this.selectedProjectId,
            codebase_path_or_url: initialCodebase,
            web_app_url: initialWebAppUrl,
            // Set has_predefined_targets true if project had defaults, so user sees the fields
            has_predefined_targets: initialHasTargets 
        };
        this.showCreateForm = true;
        this.formErrorMessage = null;
    },
    prepareEditForm(config) {
      console.log('Preparing edit form for config:', JSON.parse(JSON.stringify(config)));
      this.editingConfiguration = { ...config }; // Store a copy for reference, not for direct binding
      
      let codebase = '';
      let webapp = '';
      let hasTargets = false;

      if (config.target_details_json) {
        try {
          const targets = typeof config.target_details_json === 'string' ? JSON.parse(config.target_details_json) : config.target_details_json;
          if (targets) {
            codebase = targets.codebase_git || targets.codebase_local_path || '';
            webapp = targets.web_url || '';
            if (codebase || webapp) {
                hasTargets = true;
            }
          }
        } catch (e) {
          console.error('Error parsing target_details_json for editing:', e);
          this.formErrorMessage = 'Error parsing existing target details. Please check JSON format if editing manually.';
          // Keep hasTargets false, so user sees empty fields and can correct
        }
      }

      const parsedTools = this.parseToolsFromConfig(config.tool_configurations_json);

      this.configForm = {
        id: config.id,
        name: config.name || '',
        description: config.description || '',
        project: config.project, // This should be the project ID
        has_predefined_targets: config.has_predefined_targets || hasTargets, // Prefer explicit flag, fallback to parsed
        target_details_json: config.target_details_json || '', // Keep original for reference / manual edit fallback
        codebase_path_or_url: codebase,
        web_app_url: webapp,
        tools: parsedTools
      };
      this.showCreateForm = true; // Show the form which is now populated for editing
      this.formErrorMessage = null; // Clear previous form errors
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
      this.formErrorMessage = null;
      this.isSaving = true;

      let dataToSave = {
        name: this.configForm.name,
        description: this.configForm.description,
        project: this.selectedProjectId, // Ensure project ID is included
        has_predefined_targets: this.configForm.has_predefined_targets,
        tool_configurations_json: this.buildToolConfigurationsJson(), // Use helper to build this
        target_details_json: null // Default to null
      };

      if (this.configForm.has_predefined_targets) {
        const targets = {};
        if (this.configForm.codebase_path_or_url && this.configForm.codebase_path_or_url.trim()) {
          const codebaseValue = this.configForm.codebase_path_or_url.trim();
          if (codebaseValue.startsWith(('http://', 'https://', 'git@', 'ssh://'))) {
            targets['codebase_git'] = codebaseValue;
          } else {
            targets['codebase_local_path'] = codebaseValue;
          }
        }
        if (this.configForm.web_app_url && this.configForm.web_app_url.trim()) {
          targets['web_url'] = this.configForm.web_app_url.trim();
        }
        // Only set target_details_json if there are actual targets defined
        if (Object.keys(targets).length > 0) {
          dataToSave.target_details_json = JSON.stringify(targets);
        } else {
          // If fields were empty but checkbox was checked, treat as no predefined targets
          dataToSave.has_predefined_targets = false; 
        }
      } else {
         dataToSave.target_details_json = null; // Explicitly null if not has_predefined_targets
      }
      
      // If has_predefined_targets is true but no targets were actually entered, 
      // it might be better to also set has_predefined_targets to false.
      if (dataToSave.has_predefined_targets && dataToSave.target_details_json === null) {
          console.warn("has_predefined_targets was true, but no actual target details were generated. Setting has_predefined_targets to false.");
          dataToSave.has_predefined_targets = false;
      }

      try {
        let response;
        if (this.editingConfiguration && this.configForm.id) {
          // Update existing configuration
          response = await axios.put(`${API_CONFIGURATIONS_URL}${this.configForm.id}/`, dataToSave);
        } else {
          // Create new configuration
          response = await axios.post(API_CONFIGURATIONS_URL, dataToSave);
        }
        console.log('Configuration saved:', response.data);
        this.fetchConfigurations(this.selectedProjectId); // Refresh list
        this.cancelEditOrCreate(); // Close form and reset
      } catch (error) {
        console.error('Error saving configuration:', error.response || error.message || error);
        if (error.response && error.response.data) {
          let messages = [];
          for (const key in error.response.data) {
            const fieldErrors = Array.isArray(error.response.data[key]) ? error.response.data[key].join(', ') : error.response.data[key];
            messages.push(`${key.charAt(0).toUpperCase() + key.slice(1)}: ${fieldErrors}`);
          }
          this.formErrorMessage = messages.join('; ');
        } else {
          this.formErrorMessage = 'An unknown error occurred while saving the configuration.';
        }
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
        // Wenn selectedProjectId beim Cancel immer noch gesetzt ist, soll es im Formular bleiben für den nächsten "Create New"
        if(this.selectedProjectId) {
            this.configForm.project = this.selectedProjectId;
        }
        this.formErrorMessage = null;
    },
    parseToolsFromConfig(toolConfigJson) {
      const parsedTools = {
        semgrep: {
          enabled: false,
          rulesets: 'p/ci',
        },
        trivy: {
          enabled: false,
          scanType: 'fs',
          severity: 'HIGH,CRITICAL',
          ignoreUnfixed: false,
        },
        zap: {
          enabled: false,
        }
      };

      if (toolConfigJson) {
        const toolConfig = JSON.parse(toolConfigJson);
        if (toolConfig.semgrep) {
          parsedTools.semgrep.enabled = toolConfig.semgrep.enabled !== undefined ? toolConfig.semgrep.enabled : parsedTools.semgrep.enabled;
          if (Array.isArray(toolConfig.semgrep.rulesets)) {
            parsedTools.semgrep.rulesets = toolConfig.semgrep.rulesets.join(',');
          } else if (typeof toolConfig.semgrep.rulesets === 'string') {
            parsedTools.semgrep.rulesets = toolConfig.semgrep.rulesets;
          }
        }
        if (toolConfig.trivy) {
          parsedTools.trivy.enabled = toolConfig.trivy.enabled !== undefined ? toolConfig.trivy.enabled : parsedTools.trivy.enabled;
          parsedTools.trivy.scanType = toolConfig.trivy.scan_type || parsedTools.trivy.scanType;
          if (Array.isArray(toolConfig.trivy.severity)) {
            parsedTools.trivy.severity = toolConfig.trivy.severity.join(',');
          } else if (typeof toolConfig.trivy.severity === 'string') {
             parsedTools.trivy.severity = toolConfig.trivy.severity;
          }
          parsedTools.trivy.ignoreUnfixed = toolConfig.trivy.ignore_unfixed !== undefined ? toolConfig.trivy.ignore_unfixed : parsedTools.trivy.ignoreUnfixed;
        }
        // TODO: ZAP parsing if/when ZAP is added
      }

      return parsedTools;
    },
    buildToolConfigurationsJson() {
      const toolConfigurations = {};
      if (this.configForm.tools.semgrep.enabled) {
        toolConfigurations.semgrep = {
          enabled: true,
          rulesets: this.configForm.tools.semgrep.rulesets.split(',').map(s => s.trim()).filter(s => s)
        };
        if (toolConfigurations.semgrep.rulesets.length === 0) {
          // Backend erwartet vielleicht einen Default oder spezifischen Wert wenn enabled
          // Für jetzt, wenn leer, senden wir leeres Array, Backend muss damit umgehen oder wir definieren Default hier
        }
      }

      if (this.configForm.tools.trivy.enabled) {
        toolConfigurations.trivy = {
          enabled: true,
          scan_type: this.configForm.tools.trivy.scanType,
          severity: this.configForm.tools.trivy.severity.split(',').map(s => s.trim()).filter(s => s),
          ignore_unfixed: this.configForm.tools.trivy.ignoreUnfixed
        };
        if (toolConfigurations.trivy.severity.length === 0) {
          // Ähnlich wie bei Semgrep, Backend-Verhalten oder Default hier definieren
        }
      }

      // TODO: ZAP configuration building

      return Object.keys(toolConfigurations).length > 0 ? JSON.stringify(toolConfigurations) : null;
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
.form-group textarea,
.form-group select {
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

.tool-config-fieldset {
  border: 1px solid #ddd;
  padding: 15px;
  margin-bottom: 15px;
  border-radius: 4px;
}

.tool-config-fieldset legend {
  font-weight: bold;
  padding: 0 10px;
  width: auto; /* Behaves more like a natural legend */
  font-size: 1.1em;
}

.tool-config-group {
  padding: 10px;
  margin-bottom: 10px;
  border: 1px dashed #eee;
  border-radius: 3px;
}

.tool-enable-label {
  font-weight: normal;
  display: flex;
  align-items: center;
}

.tool-enable-label input[type="checkbox"] {
  margin-right: 8px;
  width: auto; /* Override global input width for checkbox */
}

.tool-options {
  margin-top: 10px;
  padding-left: 25px; /* Indent options */
}

.tool-options label {
  margin-top: 5px;
  margin-bottom: 5px;
}

.tool-options input[type="text"],
.tool-options select {
  margin-bottom: 8px;
}

.tool-options small {
  display: block;
  font-size: 0.85em;
  color: #666;
  margin-bottom: 5px;
}
</style> 