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
      isCreatingProject: false,
      createProjectError: null,
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
      this.newProjectName = ''; // Reset form fields when opening
      this.newProjectDescription = '';
      this.createProjectError = null;
    },
    closeCreateProjectModal() {
      this.showCreateProjectModal = false;
      this.newProjectName = '';
      this.newProjectDescription = '';
      this.createProjectError = null;
      this.isCreatingProject = false; // Ensure loading state is reset
    },
    async createNewProject() {
      if (!this.newProjectName.trim()) {
        this.createProjectError = 'Project name cannot be empty.';
        return;
      }
      this.isCreatingProject = true;
      this.createProjectError = null;
      try {
        await axios.post('/api/v1/core/projects/', {
          name: this.newProjectName,
          description: this.newProjectDescription
        });
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
.form-group textarea {
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
</style> 