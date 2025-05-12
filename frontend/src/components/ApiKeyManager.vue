<template>
  <div class="api-key-manager" v-if="isLoggedIn">
    <h3>API Key Management</h3>
    <button @click="generateApiKey" :disabled="isGenerating">
      {{ isGenerating ? 'Generating...' : 'Generate New API Key' }}
    </button>

    <div v-if="newApiKey" class="new-api-key-display success-message">
      <p><strong>New API Key Generated:</strong></p>
      <p><code>{{ newApiKey.key }}</code></p>
      <p><em>Please save this key now. You will not be able to see it again.</em></p>
      <p><strong>Name:</strong> {{ newApiKey.name }} (Expires: {{ formatDate(newApiKey.expiry_date) || 'Never' }})</p> 
      <button @click="newApiKey = null">Dismiss</button>
    </div>

    <div v-if="isLoadingKeys" class="loading-message">Loading API keys...</div>
    <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>

    <div v-if="apiKeys.length > 0 && !isLoadingKeys" class="api-key-list">
      <h4>Your API Keys:</h4>
      <ul>
        <li v-for="apiKey in apiKeys" :key="apiKey.prefix">
          <strong>Name:</strong> {{ apiKey.name }}
          (Prefix: {{ apiKey.prefix }}) -
          Created: {{ formatDate(apiKey.created) }} -
          Expires: {{ formatDate(apiKey.expiry_date) || 'Never' }} -
          Revoked: {{ apiKey.revoked }}
          <button @click="revokeApiKey(apiKey.prefix)" :disabled="apiKey.revoked || isRevoking === apiKey.prefix" class="revoke-button">
            {{ isRevoking === apiKey.prefix ? 'Revoking...' : (apiKey.revoked ? 'Revoked' : 'Revoke') }}
          </button>
        </li>
      </ul>
    </div>
    <div v-else-if="!isLoadingKeys && apiKeys.length === 0 && !errorMessage" class="info-message">
      You have no API keys.
    </div>
  </div>
</template>

<script>
import axios from 'axios';

const API_KEYS_URL = '/api/core/api-keys/'; // Endpoint for APIKeyViewSet

export default {
  name: 'ApiKeyManager',
  props: {
    isLoggedIn: {
      type: Boolean,
      required: true
    }
  },
  data() {
    return {
      apiKeys: [],
      newApiKey: null,
      isLoadingKeys: false,
      isGenerating: false,
      isRevoking: null,
      errorMessage: null
    };
  },
  watch: {
    isLoggedIn: {
      immediate: true,
      handler(newValue) {
        if (newValue) {
          this.fetchApiKeys();
        } else {
          this.apiKeys = [];
          this.newApiKey = null;
          this.errorMessage = null;
          this.isLoadingKeys = false;
          this.isGenerating = false;
          this.isRevoking = null;
        }
      }
    }
  },
  methods: {
    formatDate(dateString) {
      if (!dateString) return null;
      const options = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
      return new Date(dateString).toLocaleDateString(undefined, options);
    },
    async fetchApiKeys() {
      if (!this.isLoggedIn) return;
      this.isLoadingKeys = true;
      this.errorMessage = null;
      try {
        const response = await axios.get(API_KEYS_URL);
        this.apiKeys = response.data;
      } catch (error) {
        console.error('Error fetching API keys:', error.response || error.message);
        this.errorMessage = 'Failed to load API keys.';
        if (error.response && error.response.status === 401) {
            this.$emit('session-expired');
        }
      } finally {
        this.isLoadingKeys = false;
      }
    },
    async generateApiKey() {
      if (!this.isLoggedIn) return;
      this.isGenerating = true;
      this.errorMessage = null;
      this.newApiKey = null;
      try {
        const keyName = `MyKey-${Date.now().toString().slice(-6)}`;
        const response = await axios.post(API_KEYS_URL, { name: keyName });
        this.newApiKey = response.data;
        await this.fetchApiKeys();
      } catch (error) {
        console.error('Error generating API key:', error.response || error.message);
        this.errorMessage = 'Failed to generate API key.';
        if (error.response && error.response.data) {
            let errors = [];
            for (const field in error.response.data) {
                errors.push(`${field}: ${error.response.data[field].join(', ')}`);
            }
            this.errorMessage = `Failed to generate API key: ${errors.join('; ')}`;
        } else if (error.response && error.response.status === 401) {
            this.$emit('session-expired');
        } else {
            this.errorMessage = 'Failed to generate API key. An unknown error occurred.';
        }
      } finally {
        this.isGenerating = false;
      }
    },
    async revokeApiKey(keyPrefix) {
      if (!this.isLoggedIn || !keyPrefix) return;
      if (!confirm(`Are you sure you want to revoke the API key starting with ${keyPrefix}? This action cannot be undone.`)) {
        return;
      }
      this.isRevoking = keyPrefix;
      this.errorMessage = null;
      try {
        await axios.post(`${API_KEYS_URL}${keyPrefix}/revoke/`);
        await this.fetchApiKeys(); // Refresh the list after successful revocation
      } catch (error) {
        console.error(`Error revoking API key ${keyPrefix}:`, error.response || error.message);
        this.errorMessage = `Failed to revoke API key ${keyPrefix}.`;
        if (error.response && error.response.status === 401) {
            this.$emit('session-expired');
        }
      } finally {
        this.isRevoking = null;
      }
    }
  }
};
</script>

<style scoped>
.api-key-manager {
  margin-top: 20px;
  padding: 20px;
  border: 1px solid #28a745;
  border-radius: 8px;
  background-color: #f0fff4;
}
.api-key-manager h3 {
  margin-top: 0;
  color: #155724;
}
.api-key-manager button {
  margin-bottom: 15px;
  padding: 8px 12px;
  background-color: #28a745;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}
.api-key-manager button:hover {
    background-color: #218838;
}
.api-key-manager button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}
.revoke-button {
    background-color: #dc3545 !important;
    margin-left: 10px;
}
.revoke-button:hover {
    background-color: #c82333 !important;
}
.revoke-button:disabled {
    background-color: #888 !important;
}
.new-api-key-display {
  padding: 15px;
  margin-bottom: 20px;
  border-radius: 4px;
  background-color: #d4edda; /* Match success-message style */
  border: 1px solid #c3e6cb;
  color: #155724;
}
.new-api-key-display code {
  font-weight: bold;
  font-family: monospace;
  background-color: #c3e6cb;
  padding: 3px 6px;
  border-radius: 3px;
  color: #0b2e13;
}
.new-api-key-display button {
    background-color: #007bff;
    font-size: 0.8em;
    padding: 5px 10px;
    margin-top:10px;
}
.new-api-key-display button:hover {
    background-color: #0056b3;
}
.api-key-list ul {
  list-style-type: none;
  padding: 0;
}
.api-key-list li {
  background-color: #fff;
  border: 1px solid #ddd;
  padding: 10px 15px;
  margin-bottom: 8px;
  border-radius: 4px;
  font-size: 0.9em;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap; /* Allow wrapping for smaller screens */
}
.api-key-list li > div { /* Group key info */
    flex-grow: 1;
}
.loading-message, .error-message, .info-message {
  padding: 10px;
  margin-top: 10px;
  border-radius: 4px;
  text-align: left;
}
.loading-message { background-color: #f0f0f0; color: #333; }
.error-message { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
.info-message { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
</style>
 