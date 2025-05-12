<template>
  <div class="modal-backdrop" @click.self="close"> <!-- click.self to close only on backdrop click -->
    <div class="modal-dialog" role="document">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">{{ isEditing ? 'Edit' : 'Create' }} Scan Configuration</h5>
          <button type="button" class="close" @click="close" aria-label="Close">
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="handleSubmit">
            <div class="form-group">
              <label for="configName">Name*</label>
              <input type="text" id="configName" v-model.trim="form.name" class="form-control" required>
              <small v-if="errors.name" class="text-danger">{{ errors.name }}</small>
            </div>

            <div class="form-group">
              <label for="configDescription">Description</label>
              <textarea id="configDescription" v-model.trim="form.description" class="form-control" rows="3"></textarea>
              <small v-if="errors.description" class="text-danger">{{ errors.description }}</small>
            </div>
            
            <div class="form-group form-check">
              <input type="checkbox" id="hasPredefinedTargets" v-model="form.has_predefined_targets" class="form-check-input">
              <label class="form-check-label" for="hasPredefinedTargets">Has Predefined Targets</label>
            </div>

            <div class="form-group" v-if="form.has_predefined_targets">
              <label for="targetDetailsJson">Target Details (JSON)</label>
              <textarea id="targetDetailsJson" v-model="form.target_details_json" class="form-control" rows="4" placeholder='e.g., {\"type\": \"git_repo\", \"value\": \"https://...\"}'></textarea>
              <small v-if="errors.target_details_json" class="text-danger">{{ errors.target_details_json }}</small>
            </div>

            <div class="form-group">
              <label for="toolConfigurationsJson">Tool Configurations (JSON)*</label>
              <textarea id="toolConfigurationsJson" v-model="form.tool_configurations_json" class="form-control" rows="4" placeholder='e.g., {\"bandit\": {\"enabled\": true, \"options\": \"-r\"}}' required></textarea>
              <small v-if="errors.tool_configurations_json" class="text-danger">{{ errors.tool_configurations_json }}</small>
            </div>

            <div v-if="apiError" class="alert alert-danger mt-3">
              {{ apiError }}
            </div>

            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" @click="close">Cancel</button>
              <button type="submit" class="btn btn-primary" :disabled="isSubmitting">
                {{ isSubmitting ? 'Saving...' : (isEditing ? 'Save Changes' : 'Create Configuration') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../services/api'; // Use the new api service

export default {
  name: 'ConfigurationFormModal',
  props: {
    initialConfig: {
      type: Object,
      default: null,
    },
    projectId: {
      type: [Number, String],
      required: true,
    },
    isEditing: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      form: {
        name: '',
        description: '',
        project: this.projectId, 
        has_predefined_targets: false,
        target_details_json: '{}',
        tool_configurations_json: '{}',
      },
      errors: {},
      apiError: null,
      isSubmitting: false,
    };
  },
  watch: {
    initialConfig: {
      immediate: true,
      deep: true,
      handler(newVal) {
        if (newVal && this.isEditing) {
          this.form.name = newVal.name || '';
          this.form.description = newVal.description || '';
          this.form.has_predefined_targets = newVal.has_predefined_targets || false;
          // Ensure JSON fields are pretty-printed strings for textarea editing
          this.form.target_details_json = newVal.target_details_json ? JSON.stringify(newVal.target_details_json, null, 2) : '{}';
          this.form.tool_configurations_json = newVal.tool_configurations_json ? JSON.stringify(newVal.tool_configurations_json, null, 2) : '{}';
        } else {
          this.resetForm(); // For create mode or if initialConfig becomes null
        }
      },
    },
  },
  methods: {
    resetForm() {
      this.form.name = '';
      this.form.description = '';
      // this.form.project = this.projectId; // Project ID is set in data() and shouldn't be reset here
      this.form.has_predefined_targets = false;
      this.form.target_details_json = '{}';
      this.form.tool_configurations_json = '{}';
      this.errors = {};
      this.apiError = null;
    },
    validateJsonFields() {
      this.errors = {}; // Clear previous errors
      let isValid = true;
      try {
        if (this.form.has_predefined_targets && this.form.target_details_json.trim() !== '') {
           JSON.parse(this.form.target_details_json);
        }
      } catch (e) {
        this.errors.target_details_json = 'Invalid JSON format for Target Details.';
        isValid = false;
      }
      try {
        if (this.form.tool_configurations_json.trim() === '') {
            this.errors.tool_configurations_json = 'Tool Configurations JSON cannot be empty.';
            isValid = false;
        } else {
            JSON.parse(this.form.tool_configurations_json);
        }
      } catch (e) {
        this.errors.tool_configurations_json = 'Invalid JSON format for Tool Configurations.';
        isValid = false;
      }
      return isValid;
    },
    async handleSubmit() {
      if (!this.validateJsonFields()) {
        return;
      }
      this.isSubmitting = true;
      this.apiError = null;
      this.errors = {}; // Clear previous API field errors

      const payload = {
        name: this.form.name,
        description: this.form.description,
        project: this.projectId,
        has_predefined_targets: this.form.has_predefined_targets,
        target_details_json: (this.form.has_predefined_targets && this.form.target_details_json.trim() !== '') ? JSON.parse(this.form.target_details_json) : null,
        tool_configurations_json: JSON.parse(this.form.tool_configurations_json),
      };

      try {
        let savedData;
        if (this.isEditing && this.initialConfig) {
          // response = await axios.put(`/api/core/scan-configurations/${this.initialConfig.id}/`, payload);
          savedData = await api.updateScanConfiguration(this.initialConfig.id, payload);
        } else {
          // response = await axios.post('/api/core/scan-configurations/', payload);
          savedData = await api.createScanConfiguration(payload);
        }
        this.$emit('save', savedData); // Emit the saved/created config data
        this.close();
      } catch (error) {
        console.error('Error saving scan configuration:', error);
        if (error.response && error.response.data) {
            const errorData = error.response.data;
            if (typeof errorData === 'string') {
                 this.apiError = errorData;
            } else {
                this.apiError = errorData.detail || 'An error occurred. Please check field errors.';
                // Map field errors if available from DRF validation
                Object.keys(errorData).forEach(key => {
                    if(this.form.hasOwnProperty(key) || key === 'target_details_json' || key === 'tool_configurations_json') {
                        // Ensure errors is an object if it comes from DRF as an array of strings
                        this.errors[key] = Array.isArray(errorData[key]) ? errorData[key].join(', ') : errorData[key];
                    } else if (key !== 'detail') {
                        // For non_field_errors or other general errors not directly mapping to form fields
                        this.apiError = `${this.apiError} ${key}: ${Array.isArray(errorData[key]) ? errorData[key].join(', ') : errorData[key]}`;
                    }
                });
            }
        } else {
            this.apiError = 'An unexpected error occurred during save.';
        }
      } finally {
        this.isSubmitting = false;
      }
    },
    close() {
      this.resetForm();
      this.$emit('close');
    },
  },
  mounted() {
    // Watcher handles initial population or reset
  }
};
</script>

<style scoped>
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
  z-index: 1050; /* Ensure it's above other content */
}
.modal-dialog {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 5px 15px rgba(0,0,0,0.3);
  max-width: 600px; /* Increased max-width */
  width: 90%;
  max-height: 90vh; /* Limit height and allow scrolling */
  display: flex;
  flex-direction: column;
}
.modal-content {
    display: flex;
    flex-direction: column;
    flex-grow: 1; /* Allow content to take available space */
    overflow-y: hidden; /* Prevent double scrollbars initially */
}
.modal-header {
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modal-header .modal-title {
  margin-bottom: 0;
  font-size: 1.25rem;
}
.modal-body {
  padding: 1.5rem;
  overflow-y: auto; /* Enable scrolling for body if content overflows */
  flex-grow: 1;
}
.modal-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #e9ecef;
  display: flex;
  justify-content: flex-end;
  align-items: center;
}
.modal-footer .btn + .btn {
  margin-left: 0.5rem;
}
.close {
  border: none;
  background: none;
  font-size: 1.75rem;
  font-weight: bold;
  opacity: 0.7;
}
.close:hover {
  opacity: 1;
}
.form-group {
  margin-bottom: 1rem;
}
.form-check {
  margin-bottom: 1rem;
}
.form-control {
  display: block;
  width: 100%;
  padding: 0.375rem 0.75rem;
  font-size: 1rem;
  line-height: 1.5;
  color: #495057;
  background-color: #fff;
  background-clip: padding-box;
  border: 1px solid #ced4da;
  border-radius: 0.25rem;
  transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
}
.form-control:focus {
  color: #495057;
  background-color: #fff;
  border-color: #80bdff;
  outline: 0;
  box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}
textarea.form-control {
  min-height: 80px; /* Default min height for textareas */
}
.text-danger {
  color: #dc3545 !important;
  font-size: 0.875em;
}
.alert-danger {
    color: #721c24;
    background-color: #f8d7da;
    border-color: #f5c6cb;
    padding: .75rem 1.25rem;
    margin-bottom: 1rem;
    border: 1px solid transparent;
    border-radius: .25rem;
}
.btn-primary {
  color: #fff;
  background-color: #007bff;
  border-color: #007bff;
}
.btn-primary:hover {
  background-color: #0056b3;
}
.btn-primary:disabled {
  background-color: #007bff;
  opacity: 0.65;
}
.btn-secondary {
  color: #fff;
  background-color: #6c757d;
  border-color: #6c757d;
}
.btn-secondary:hover {
  background-color: #545b62;
}
</style> 