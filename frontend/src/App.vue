<script>
import HelloWorld from './components/HelloWorld.vue'
import ScanRunner from './components/ScanRunner.vue'
import RegistrationForm from './components/RegistrationForm.vue'
import LoginForm from './components/LoginForm.vue'
import UserProfileDisplay from './components/UserProfileDisplay.vue'
import ApiKeyManager from './components/ApiKeyManager.vue'
import ScanJobList from './components/ScanJobList.vue'
import ScanConfigurationManager from './components/ScanConfigurationManager.vue'
import ProjectList from './components/ProjectList.vue'
import axios from 'axios';

const AUTH_API_URL = '/api/v1/auth';

export default {
  name: 'App',
  components: {
    HelloWorld,
    ScanRunner,
    RegistrationForm,
    LoginForm,
    UserProfileDisplay,
    ApiKeyManager,
    ScanJobList,
    ScanConfigurationManager,
    ProjectList
  },
  data() {
    return {
      isLoggedIn: false,
      currentProjectIdForConfigManager: null,
      selectedProjectForConfigManager: null,
      projectsForScanRunner: [],
    };
  },
  created() {
    const token = localStorage.getItem('authToken');
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Token ${token}`;
      this.isLoggedIn = true;
    }
  },
  methods: {
    onUserLoggedIn() {
      const token = localStorage.getItem('authToken');
      if (token) {
        axios.defaults.headers.common['Authorization'] = `Token ${token}`;
        this.isLoggedIn = true;
        this.currentProjectIdForConfigManager = null;
        this.selectedProjectForConfigManager = null;
        if (this.$refs.projectList) {
            this.$refs.projectList.fetchProjects();
        }
      } else {
        console.error("Login event received, but no token found in localStorage.");
        this.handleLogout(true);
      }
    },
    async handleLogout(isSessionExpired = false) {
      if (isSessionExpired) {
        console.log('Session expired, logging out.');
      }
      const token = localStorage.getItem('authToken');
      if (token && !isSessionExpired) {
        try {
          await axios.post(`${AUTH_API_URL}/logout/`, {});
          console.log('Logout successful on backend.');
        } catch (error) {
          console.error('Error during backend logout:', error.response || error.message);
        }
      }
      localStorage.removeItem('authToken');
      delete axios.defaults.headers.common['Authorization'];
      this.isLoggedIn = false;
      this.currentProjectIdForConfigManager = null;
      this.selectedProjectForConfigManager = null;
      this.projectsForScanRunner = [];
    },
    handleSessionExpired() {
      this.handleLogout(true);
    },
    handleProjectSelectedForConfigManager(projectId) {
      this.currentProjectIdForConfigManager = projectId;
      if (projectId) {
        this.selectedProjectForConfigManager = this.projectsForScanRunner.find(p => p.id === projectId) || null;
      } else {
        this.selectedProjectForConfigManager = null;
      }
      console.log('App.vue: selectedProjectForConfigManager updated:', JSON.parse(JSON.stringify(this.selectedProjectForConfigManager)));
    },
    handleProjectListUpdate(updatedProjects) {
      this.projectsForScanRunner = updatedProjects;
      console.log('App.vue: projectsForScanRunner updated by ProjectList event:', JSON.parse(JSON.stringify(updatedProjects)));
    },
    updateCurrentUser() {
      const token = localStorage.getItem('authToken');
      // ... existing code ...
    }
  }
}
</script>

<template>
  <div id="app">
    <header>
      <!-- <img alt="Vue logo" src="./assets/logo.png"> -->
      <h1>SecuLite Vue App</h1>
      <div v-if="isLoggedIn" class="user-status">
        <span>Welcome!</span>
        <button @click="handleLogout">Logout</button>
      </div>
    </header>
    <main>
      <div v-if="!isLoggedIn" class="auth-section">
        <LoginForm @loggedIn="onUserLoggedIn" />
        <hr class="separator" />
        <RegistrationForm />
      </div>
      <div v-else class="main-content">
        <UserProfileDisplay :isLoggedIn="isLoggedIn" @session-expired="handleSessionExpired" />
        <hr class="separator" />
        <ApiKeyManager :isLoggedIn="isLoggedIn" @session-expired="handleSessionExpired" />
        <hr class="separator" />
        <ProjectList @project-list-updated="handleProjectListUpdate" ref="projectList" />
        <hr class="separator" />
        <h2>Scan Operations</h2>
        <ScanRunner 
            ref="scanRunner" 
            :isLoggedIn="isLoggedIn" 
            :projects="projectsForScanRunner" 
            @session-expired="handleSessionExpired"
            @project-selected="handleProjectSelectedForConfigManager" 
        />
        <hr class="separator" />
        <ScanConfigurationManager 
            :isLoggedIn="isLoggedIn" 
            :selectedProjectId="currentProjectIdForConfigManager"
            :selectedProject="selectedProjectForConfigManager"
            @session-expired="handleSessionExpired"
        />
        <hr class="separator" />
        <ScanJobList :isLoggedIn="isLoggedIn" @session-expired="handleSessionExpired" />
        <hr class="separator" />
        <HelloWorld msg="Additional Content (Placeholder)"/>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* If App.vue has any specific scoped styles, they would remain here. */
/* For example, if #app itself needed very specific App.vue-only styling */
/* Based on current structure, likely no scoped styles needed here. */
.app-container {
  /* Example if needed */
}
</style>
