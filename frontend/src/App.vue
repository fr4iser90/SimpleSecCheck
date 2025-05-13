<script>
import HelloWorld from './components/HelloWorld.vue'
import ScanRunner from './components/ScanRunner.vue'
import RegistrationForm from './components/RegistrationForm.vue'
import LoginForm from './components/LoginForm.vue'
import UserProfileDisplay from './components/UserProfileDisplay.vue'
import ApiKeyManager from './components/ApiKeyManager.vue'
import ScanJobList from './components/ScanJobList.vue'
import ScanConfigurationManager from './components/ScanConfigurationManager.vue'
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
    ScanConfigurationManager
  },
  data() {
    return {
      isLoggedIn: false,
      currentProjectIdForConfigManager: null,
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
    },
    handleSessionExpired() {
      this.handleLogout(true);
    },
    handleProjectSelectedForConfigManager(projectId) {
      this.currentProjectIdForConfigManager = projectId;
    },
    async createDefaultProject() {
      try {
        const response = await axios.post('/api/v1/core/projects/', { name: 'Default Project' });
        console.log('Default project created:', response.data);
        alert('Default Project created successfully! The project list will refresh.');
        // Refresh the project list in ScanRunner, assuming ScanRunner component has a ref and a method to fetch projects
        if (this.$refs.scanRunner && typeof this.$refs.scanRunner.fetchProjects === 'function') {
          this.$refs.scanRunner.fetchProjects();
        } else {
          console.warn('ScanRunner component or fetchProjects method not available.');
          // Optionally, emit an event that a parent component or global state manager can listen to
          // this.$root.$emit('projectListShouldRefresh'); // Example if using root instance as event bus
        }
      } catch (error) {
        console.error('Failed to create default project:', error);
        if (error.response && error.response.data && error.response.data.name && error.response.data.name[0].includes('project with this name already exists')) {
          alert('Failed to create default project: A project with the name "Default Project" already exists.');
        } else {
          alert('Failed to create default project: Request failed with status code ' + (error.response ? error.response.status : 'unknown'));
        }
      }
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
        <h2>Scan Operations</h2>
        <button @click="createDefaultProject" class="action-button create-button">Create Default Project</button>
        <ScanRunner 
            ref="scanRunner" 
            :isLoggedIn="isLoggedIn" 
            @session-expired="handleSessionExpired"
            @project-selected="handleProjectSelectedForConfigManager" 
        />
        <hr class="separator" />
        <ScanConfigurationManager 
            :isLoggedIn="isLoggedIn" 
            :selectedProjectId="currentProjectIdForConfigManager"
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

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  margin-top: 60px;
}

header {
  text-align: center;
  margin-bottom: 40px;
  position: relative;
}

header img {
  width: 80px;
  height: 80px;
}

.user-status {
  position: absolute;
  top: 10px;
  right: 20px;
  display: flex;
  align-items: center;
  font-size: 0.9em;
}

.user-status span {
  margin-right: 10px;
}

.user-status button {
  padding: 5px 10px;
  background-color: #dc3545;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

main {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}

.auth-section,
.main-content {
  padding: 20px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background-color: #f9f9f9;
}

.separator {
  margin: 40px 0;
  border: 0;
  border-top: 1px solid #e9ecef;
}

main h2 {
    text-align: center;
}
</style>
