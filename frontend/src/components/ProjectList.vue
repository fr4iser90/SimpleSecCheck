<template>
  <div class="project-list-container">
    <h2>Projektübersicht</h2>
    <button @click="openCreateProjectModal" class="btn btn-primary mb-3">Neues Projekt erstellen</button>
    <div v-if="isLoading" class="loading-spinner">
      <p>Lade Projekte...</p>
      </div>
    <div v-else-if="error">
      <p class="text-danger">Fehler beim Laden der Projekte: {{ error }}</p>
    </div>
    <div v-else>
      <ul v-if="projects.length > 0" class="list-group">
        <li v-for="project in projects" :key="project.id" class="list-group-item">
          <h5>{{ project.name }}</h5>
          <p v-if="project.description">{{ project.description }}</p>
          <small>Erstellt am: {{ new Date(project.created_at).toLocaleDateString() }}</small>
          <!-- Weitere Aktionen pro Projekt (Bearbeiten, Löschen, Details) können hier später hinzugefügt werden -->
        </li>
      </ul>
      <p v-else>Noch keine Projekte vorhanden. Erstelle dein erstes Projekt!</p>
    </div>

    <!-- Modal for creating a new project -->
    <div v-if="showCreateProjectModal" class="modal">
      <div class="modal-content">
        <span class="close-button" @click="closeCreateProjectModal">&times;</span>
        <h3>Neues Projekt erstellen</h3>
        <form @submit.prevent="createNewProject">
          <div class="form-group">
            <label for="projectName">Projektname:*</label>
            <input type="text" id="projectName" v-model="newProjectName" required>
          </div>
          <div class="form-group">
            <label for="projectDescription">Beschreibung (optional):</label>
            <textarea id="projectDescription" v-model="newProjectDescription" rows="3"></textarea>
          </div>

          <!-- Docker Integration UI Start -->
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="showDockerSelection">
              Aus laufendem Docker-Container erstellen/befüllen
            </label>
          </div>

          <div v-if="showDockerSelection" class="docker-selection-section">
            <div class="form-group">
              <label for="dockerComposeProjectSelect">Docker-Compose-Projekt auswählen:</label>
              <button type="button" @click="fetchDockerComposeProjects" :disabled="isLoadingDockerComposeProjects" class="btn btn-sm btn-info mb-2">
                {{ isLoadingDockerComposeProjects ? 'Lade Docker-Projekte...' : 'Projektliste aktualisieren' }}
              </button>
              <div v-if="dockerComposeProjectsError" class="alert alert-danger">{{ dockerComposeProjectsError }}</div>
              <select id="dockerComposeProjectSelect" v-model="selectedComposeProjectName" @change="handleComposeProjectSelection" class="form-control" :disabled="isLoadingDockerComposeProjects || !dockerComposeProjects.length">
                <option :value="null" disabled>-- Bitte Docker-Compose-Projekt wählen --</option>
                <option v-for="project in dockerComposeProjects" :key="project.compose_project_name" :value="project.compose_project_name">
                  {{ project.compose_project_name }} ({{ project.containers.length }} Container)
                </option>
              </select>
              <div v-if="!isLoadingDockerComposeProjects && dockerComposeProjects.length === 0 && !dockerComposeProjectsError" class="alert alert-info">
                Keine Docker-Compose-Projekte gefunden oder Liste noch nicht geladen.
              </div>
            </div>

            <div v-if="selectedComposeProjectName && currentSelectedComposeProject && currentSelectedComposeProject.containers.length > 0" class="form-group">
              <h4>Host-Pfade für Container im Projekt '{{ selectedComposeProjectName }}':</h4>
              
              <button type="button" @click="discoverAllHostPathsForAllContainers" :disabled="isLoadingAllContainerPaths" class="btn btn-sm btn-primary mb-3">
                <span v-if="isLoadingAllContainerPaths" class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                {{ isLoadingAllContainerPaths ? 'Ermittle alle Pfade...' : 'Alle Host-Pfade automatisch erkennen' }}
              </button>

              <div class="scrollable-container-list">
                <div v-for="container in currentSelectedComposeProject.containers" :key="container.id" class="container-host-path-item">
                  <div>
                    <strong>{{ container.name }}</strong> <small>(ID: {{ container.id }}, Image: {{ container.image }})</small>
                  </div>
                  <div class="form-group">
                    <label :for="'hostPath-' + container.id" class="sr-only">Host-Pfad für {{ container.name }}</label>
                    <input type="text" 
                           :id="'hostPath-' + container.id" 
                           v-model="selectedContainerHostPaths[container.id]" 
                           placeholder="z.B. /lokaler/pfad/zum/code (optional)">
                  </div>
                  <div v-if="detectedIndividualContainerPaths[container.id] && detectedIndividualContainerPaths[container.id].length > 0" class="detected-paths-list">
                    <small>Erkannte Pfade:</small>
                    <ul>
                      <li v-for="path in detectedIndividualContainerPaths[container.id]" :key="path" @click="selectDiscoveredPath(container.id, path)">
                        {{ path }}
                      </li>
                    </ul>
                  </div>
                  <div v-if="detectedIndividualContainerPaths[container.id] && detectedIndividualContainerPaths[container.id].length === 0" class="alert alert-sm alert-warning mt-1">
                    Keine spezifischen Host-Pfade für diesen Container durch Docker-Mounts gefunden.
                  </div>
                </div>
              </div>
            </div>
             <div v-if="selectedComposeProjectName && currentSelectedComposeProject && currentSelectedComposeProject.containers.length === 0" class="alert alert-info">
                Keine Container in diesem Docker-Compose-Projekt gefunden.
            </div>
          </div>
          <!-- Docker Integration UI End -->

          <div class="form-group">
            <label for="projectCodebasePathOrUrl">Codebase-Pfad oder -URL (optional):</label>
            <input type="text" id="projectCodebasePathOrUrl" v-model="newProjectCodebasePathOrUrl" placeholder="z.B. /pfad/zur/codebase oder git@github.com:user/repo.git">
          </div>
          <div class="form-group">
            <label for="projectWebAppUrl">Web-Anwendungs-URL (optional):</label>
            <input type="url" id="projectWebAppUrl" v-model="newProjectWebAppUrl" placeholder="z.B. https://example.com">
          </div>
          <div v-if="createProjectError" class="error-message">
            {{ createProjectError }}
          </div>
          <div class="form-actions">
            <button type="button" @click="closeCreateProjectModal" :disabled="isCreatingProject" class="btn btn-secondary">Abbrechen</button>
            <button type="submit" :disabled="isCreatingProject" class="btn btn-primary">
              {{ isCreatingProject ? 'Erstelle...' : 'Erstellen' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'ProjectList',
  data() {
    return {
      projects: [],
      isLoading: false,
      error: null,
      showCreateProjectModal: false,
      newProjectName: '',
      newProjectDescription: '',
      newProjectCodebasePathOrUrl: '',
      newProjectWebAppUrl: '',
      isCreatingProject: false,
      createProjectError: null,
      // Docker Integration Data - Phase 2 (Compose Projects)
      showDockerSelection: false,
      dockerComposeProjects: [], // Will store { compose_project_name: 'name', containers: [...] }
      isLoadingDockerComposeProjects: false,
      dockerComposeProjectsError: null,
      selectedComposeProjectName: null, // Name of the selected compose project group
      selectedContainerId: null, // ID of the specific container selected within a compose project for path fetching
      selectedContainerHostPaths: {}, // New: to store host paths for multiple containers
      isLoadingAllContainerPaths: false, // NEW: For the global "discover all paths" button
      detectedIndividualContainerPaths: {}, // To store discovered paths per container
      deleteConfirmationName: '',
      projectToDelete: null,
    };
  },
  methods: {
    async fetchProjects() {
      this.isLoading = true;
      this.error = null;
      try {
        const response = await axios.get('/api/v1/core/projects/');
        this.projects = response.data.results; // Assuming paginated response
         if (!response.data.results && Array.isArray(response.data)) {
            this.projects = response.data; // Handle non-paginated response
        }
        console.log('Projects fetched:', this.projects);
        this.$emit('project-list-updated', this.projects); // Emit event with projects
      } catch (err) {
        console.error('Error fetching projects:', err);
        this.error = err.message || 'Unbekannter Fehler';
        if (err.response && err.response.data) {
            this.error = JSON.stringify(err.response.data);
        }
      } finally {
        this.isLoading = false;
      }
    },
    openCreateProjectModal() {
      this.showCreateProjectModal = true;
      this.newProjectName = '';
      this.newProjectDescription = '';
      this.newProjectCodebasePathOrUrl = '';
      this.newProjectWebAppUrl = '';
      this.createProjectError = null;

      // Reset Docker selection state for Compose Projects
      this.showDockerSelection = false;
      this.dockerComposeProjects = [];
      this.isLoadingDockerComposeProjects = false;
      this.dockerComposeProjectsError = null;
      this.selectedComposeProjectName = null;
      this.selectedContainerId = null;
      this.selectedContainerHostPaths = {}; // Reset this as well
      this.isLoadingAllContainerPaths = false; // RESET global loader
      this.detectedIndividualContainerPaths = {};
    },
    closeCreateProjectModal() {
      this.showCreateProjectModal = false;
      this.newProjectName = '';
      this.newProjectDescription = '';
      this.newProjectCodebasePathOrUrl = '';
      this.newProjectWebAppUrl = '';
      this.createProjectError = null;
      this.isCreatingProject = false; // Ensure loading state is reset
    },
    async createNewProject() {
      if (!this.newProjectName.trim()) {
        this.createProjectError = 'Projektname darf nicht leer sein.';
        return;
      }
      this.isCreatingProject = true;
      this.createProjectError = null;

      try {
        const payload = {
          name: this.newProjectName,
          description: this.newProjectDescription,
          // Default values, will be overridden if Docker selection is active
          codebase_path_or_url: this.newProjectCodebasePathOrUrl.trim() || null,
          web_app_url: this.newProjectWebAppUrl.trim() || null,
        };

        if (this.showDockerSelection && this.selectedComposeProjectName && this.currentSelectedComposeProject) {
          payload.selected_compose_project_name = this.selectedComposeProjectName;
          payload.container_targets = this.currentSelectedComposeProject.containers.map(container => ({
            id: container.id,
            name: container.name,
            image: container.image, // Ensure your container objects have 'image'
            host_code_path: this.selectedContainerHostPaths[container.id] || null
          }));
          // Optionally, clear or ignore codebase_path_or_url and web_app_url if Docker is used
          // For now, backend logic should prioritize docker_compose_targets if present
          // payload.codebase_path_or_url = null; 
          // payload.web_app_url = null;
        } else {
          // Ensure these are explicitly set if not using Docker, 
          // or rely on the initial object population. Redundant for clarity here.
          payload.codebase_path_or_url = this.newProjectCodebasePathOrUrl.trim() || null;
          payload.web_app_url = this.newProjectWebAppUrl.trim() || null;
        }
        
        await axios.post('/api/v1/core/projects/', payload);
        await this.fetchProjects(); // Reloads the list and emits the event
        this.closeCreateProjectModal();
      } catch (err) {
        console.error('Error creating project:', err.response || err.message || err);
        if (err.response && err.response.data) {
          if (typeof err.response.data === 'string') {
            this.createProjectError = err.response.data;
          } else {
            let messages = [];
            for (const key in err.response.data) {
              // Make sure it's an array of messages for the key
              const fieldErrors = Array.isArray(err.response.data[key]) ? err.response.data[key].join(', ') : err.response.data[key];
              messages.push(`${key.charAt(0).toUpperCase() + key.slice(1)}: ${fieldErrors}`);
            }
            this.createProjectError = messages.join('; ');
          }
        } else {
          this.createProjectError = 'An unknown error occurred while creating the project.';
        }
      } finally {
        this.isCreatingProject = false;
      }
    },
    
    // Docker Integration Methods - Phase 2 (Compose Projects)
    async fetchDockerComposeProjects() {
      this.isLoadingDockerComposeProjects = true;
      this.dockerComposeProjectsError = null;
      this.dockerComposeProjects = [];
      this.selectedComposeProjectName = null;
      this.selectedContainerId = null;
      this.selectedContainerHostPaths = {}; // Reset/initialize for the new project
      try {
        console.log("Fetching docker compose projects...");
        const response = await axios.get('/api/v1/core/docker/compose-projects/');
        if (response.data && Array.isArray(response.data)) {
            this.dockerComposeProjects = response.data;
            if (this.dockerComposeProjects.length === 0) {
                this.dockerComposeProjectsError = "Keine Docker-Compose-Projekte gefunden."; // Or a more neutral message
            }
        } else {
            this.dockerComposeProjectsError = 'Unerwartete Antwort vom Server beim Laden der Docker-Compose-Projekte.';
        }
      } catch (err) {
        console.error('Error fetching docker compose projects:', err);
        this.dockerComposeProjectsError = 'Fehler beim Laden der Docker-Compose-Projekte.';
        if (err.response && err.response.data && err.response.data.error) {
          this.dockerComposeProjectsError = err.response.data.error;
        } else if (err.message) {
            this.dockerComposeProjectsError = err.message;
        }
      } finally {
        this.isLoadingDockerComposeProjects = false;
      }
    },
    handleComposeProjectSelection() {
      this.selectedContainerHostPaths = {}; // Reset/initialize for the new project
      this.newProjectCodebasePathOrUrl = ''; // Reset, as paths are now per-container

      if (this.currentSelectedComposeProject && this.currentSelectedComposeProject.containers) {
        this.currentSelectedComposeProject.containers.forEach(container => {
          this.selectedContainerHostPaths[container.id] = ''; 
          this.detectedIndividualContainerPaths[container.id] = null; 
        });
      }
    },
    handleDockerSelectionChange() {
      if (!this.showDockerSelection) {
        this.selectedComposeProjectName = '';
        this.newProjectName = ''; 
        this.newProjectCodebasePathOrUrl = '';
        this.selectedContainerHostPaths = {}; 
        this.isLoadingAllContainerPaths = false; // RESET global loader
        this.detectedIndividualContainerPaths = {};
      } else {
        this.fetchDockerComposeProjects();
      }
    },
    async discoverAllHostPathsForAllContainers() {
      if (!this.currentSelectedComposeProject || !this.currentSelectedComposeProject.containers) return;

      this.isLoadingAllContainerPaths = true;
      // Reset detected paths for all relevant containers before starting new discovery
      this.currentSelectedComposeProject.containers.forEach(container => {
        this.detectedIndividualContainerPaths[container.id] = null;
      });

      const pathPromises = this.currentSelectedComposeProject.containers.map(async (container) => {
        try {
          const response = await axios.get(`/api/v1/core/docker/containers/${container.id}/paths/`);
          if (response.data && Array.isArray(response.data)) {
            this.detectedIndividualContainerPaths[container.id] = response.data;
            if (response.data.length === 1) {
              this.selectedContainerHostPaths[container.id] = response.data[0];
            }
          } else {
            this.detectedIndividualContainerPaths[container.id] = []; // No paths found or unexpected format
            console.warn("Discover all host paths: Unexpected response format for container", container.id, response.data);
          }
        } catch (err) {
          console.error(`Error discovering host paths for container ${container.id}:`, err);
          this.detectedIndividualContainerPaths[container.id] = []; // Indicate error/no paths
        }
      });

      try {
        await Promise.all(pathPromises);
      } catch (error) {
        // This catch block might be redundant if individual errors are handled within the map, 
        // but good for a general catch-all if Promise.all itself rejects due to an unhandled promise rejection (unlikely here).
        console.error("Error during Promise.all for discoverAllHostPathsForAllContainers:", error);
      } finally {
        this.isLoadingAllContainerPaths = false;
      }
    },
    selectDiscoveredPath(containerId, path) {
      this.selectedContainerHostPaths[containerId] = path;
      // Optionally, clear the detected paths list after selection to clean up UI
      // this.detectedIndividualContainerPaths[containerId] = null; 
    },
  },
  computed: {
    currentSelectedComposeProject() {
      if (!this.selectedComposeProjectName || !this.dockerComposeProjects.length) {
        return null;
      }
      return this.dockerComposeProjects.find(p => p.compose_project_name === this.selectedComposeProjectName);
    }
  },
  watch: {
    showDockerSelection(newValue) {
      if (newValue && this.dockerComposeProjects.length === 0 && !this.isLoadingDockerComposeProjects) {
        this.fetchDockerComposeProjects();
      }
      if (!newValue) {
        // Reset selections when Docker feature is toggled off
        this.selectedComposeProjectName = null;
        this.newProjectName = ''; 
        this.newProjectCodebasePathOrUrl = '';
        this.selectedContainerHostPaths = {}; 
        this.isLoadingAllContainerPaths = false; // RESET global loader
        this.detectedIndividualContainerPaths = {};
      }
    }
  },
  created() {
    this.fetchProjects();
  },
};
</script>

<style scoped>
.project-list-container {
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  margin-bottom: 20px;
}

h2 {
  color: #333;
  margin-bottom: 20px;
}

.btn-primary {
  background-color: #007bff;
  border-color: #007bff;
  color: white;
}

.mb-3 {
  margin-bottom: 1rem !important;
}

.loading-spinner p {
  font-style: italic;
}

.text-danger {
  color: #dc3545 !important;
}

.list-group-item {
  margin-bottom: 10px;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 5px;
  background-color: #fff;
}

.list-group-item h5 {
  margin-top: 0;
  margin-bottom: 5px;
  color: #0056b3;
}

.list-group-item p {
  font-size: 0.9rem;
  color: #555;
}

.list-group-item small {
  font-size: 0.8rem;
  color: #777;
}

/* Basic Modal Styling (placeholder, can be improved with a proper modal component) */
.modal {
  position: fixed;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal-content {
  background-color: white;
  padding: 20px;
  border-radius: 5px;
  min-width: 300px;
  position: relative; /* Added for positioning the close button */
}

.close-button {
  position: absolute;
  top: 10px;
  right: 15px;
  font-size: 1.5rem;
  font-weight: bold;
  color: #aaa;
  cursor: pointer;
}

.close-button:hover {
  color: #000;
}

.form-group {
    margin-bottom: 1rem;
}

.form-group label {
    display: block;
    margin-bottom: .5rem;
}

.form-group input[type="text"],
.form-group textarea,
.form-group select {
    width: 100%;
    padding: .5rem;
    border: 1px solid #ccc;
    border-radius: 4px;
    box-sizing: border-box; /* Ensures padding doesn't add to width */
}

.form-actions {
    margin-top: 1.5rem;
    display: flex;
    justify-content: flex-end;
}

.form-actions .btn {
    margin-left: .5rem;
}

.form-control { /* Basic styling for select and input to match a bit */
  width: 100%;
  padding: .375rem .75rem;
  font-size: 1rem;
  line-height: 1.5;
  color: #495057;
  background-color: #fff;
  background-clip: padding-box;
  border: 1px solid #ced4da;
  border-radius: .25rem;
  transition: border-color .15s ease-in-out,box-shadow .15s ease-in-out;
  margin-bottom: 0.5rem; /* Add some space below */
}

/* Ensure modal inputs are full width */
.modal-content .form-group input[type=\"text\"],
.modal-content .form-group textarea,
.modal-content .form-group select {
    width: 100%; /* Ensures inputs/selects take full width of their container */
    box-sizing: border-box; /* Includes padding and border in the element's total width and height */
}

.error-message {
    color: #dc3545;
    background-color: #f8d7da;
    border: 1px solid #f5c6cb;
    padding: .75rem 1.25rem;
    margin-bottom: 1rem;
    border-radius: .25rem;
    font-size: 0.9em;
}

/* Ensure buttons in modal use some base styling if global.css isn't fully covering them */
.modal .btn {
  padding: 0.5rem 1rem;
  border-radius: 0.25rem;
  cursor: pointer;
  border: 1px solid transparent;
}

.modal .btn-primary {
  background-color: #007bff;
  border-color: #007bff;
  color: white;
}
.modal .btn-primary:disabled {
  background-color: #007bff;
  opacity: 0.65;
}

.modal .btn-secondary {
  background-color: #6c757d;
  border-color: #6c757d;
  color: white;
}
.modal .btn-secondary:disabled {
  background-color: #6c757d;
  opacity: 0.65;
}

.container-host-path-item {
  margin-bottom: 10px;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 5px;
  background-color: #fff;
}

.container-host-path-item .form-group input[type="text"] {
  flex-grow: 1;
}

.container-host-path-item .btn-outline-secondary {
    /* margin-left: 8px; */ /* Using Bootstrap's ml-2 for spacing */
    white-space: nowrap; /* Prevent button text from wrapping */
}

.alert-sm {
    padding: 0.25rem 0.5rem;
    font-size: 0.875em;
    margin-top: 5px; /* Add some space above small alerts */
}

.spinner-border-sm {
    width: 1rem;
    height: 1rem;
    border-width: 0.2em;
    vertical-align: text-bottom; /* Align spinner nicely with text */
    margin-right: 0.25rem;
}

.detected-paths-list li:last-child {
  border-bottom: none;
}
.detected-paths-list li:hover {
  background-color: #e9ecef; /* Slightly different hover for detected paths */
  color: #0056b3;
}

.scrollable-container-list {
  max-height: 300px; /* Adjust as needed, e.g., 40vh for viewport height percentage */
  overflow-y: auto;
  padding-right: 10px; /* Space for scrollbar to prevent content overlap */
  border: 1px solid #eee; /* Optional: visual cue for the scrollable area */
  border-radius: 4px; /* Optional: match other border radiuses */
  margin-top: 10px; /* Optional: space above the list */
  padding-top: 5px; /* Optional: space inside, above the first item */
  padding-left: 5px; /* Optional: space inside, to the left of items */
}
</style> 