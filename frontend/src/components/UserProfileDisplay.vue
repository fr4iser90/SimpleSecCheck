<template>
  <div class="user-profile-display" v-if="isLoggedIn && (user || isLoading || errorMessage)">
    <h3>User Profile</h3>
    <div v-if="isLoading" class="loading-message">Loading profile...</div>
    <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
    <div v-if="user && !isLoading && !errorMessage">
      <p><strong>Username:</strong> {{ user.username }}</p>
      <p><strong>Email:</strong> {{ user.email }}</p>
      <!-- Add more fields as available and needed -->
      <!-- Example: <p><strong>First Name:</strong> {{ user.first_name || 'N/A' }}</p> -->
      <!-- Example: <p><strong>Last Name:</strong> {{ user.last_name || 'N/A' }}</p> -->
    </div>
  </div>
  <div v-else-if="isLoggedIn && !user && !isLoading && !errorMessage" class="info-message">
    Could not load user profile data.
  </div>
</template>

<script>
import axios from 'axios';

const AUTH_API_URL = '/api/auth';

export default {
  name: 'UserProfileDisplay',
  props: {
    isLoggedIn: {
      type: Boolean,
      required: true
    }
  },
  data() {
    return {
      user: null,
      isLoading: false,
      errorMessage: null
    };
  },
  watch: {
    isLoggedIn: {
      immediate: true,
      handler(newValue) {
        if (newValue) {
          this.fetchUserProfile();
        } else {
          this.user = null;
          this.errorMessage = null;
          this.isLoading = false;
        }
      }
    }
  },
  methods: {
    async fetchUserProfile() {
      if (!this.isLoggedIn) return; // Don't fetch if not logged in
      this.isLoading = true;
      this.errorMessage = null;
      this.user = null; 
      try {
        const response = await axios.get(`${AUTH_API_URL}/user/`);
        this.user = response.data;
      } catch (error) {
        console.error('Error fetching user profile:', error.response || error.message);
        this.errorMessage = 'Failed to load user profile.';
        if (error.response && error.response.status === 401) {
             this.errorMessage = 'Your session may have expired. Please log in again.';
             this.$emit('session-expired'); // App.vue can listen to this to force logout
        }
      } finally {
        this.isLoading = false;
      }
    }
  }
};
</script>

<style scoped>
.user-profile-display {
  margin-top: 20px;
  padding: 20px;
  border: 1px solid #007bff;
  border-radius: 8px;
  background-color: #e7f3ff;
}
.user-profile-display h3 {
  margin-top: 0;
  color: #0056b3;
}
.loading-message, .error-message, .info-message {
  padding: 10px;
  margin-top: 10px;
  border-radius: 4px;
}
.loading-message {
  background-color: #f0f0f0;
  color: #333;
}
.error-message {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}
.info-message {
  background-color: #d1ecf1;
  color: #0c5460;
  border: 1px solid #bee5eb;
}
</style> 