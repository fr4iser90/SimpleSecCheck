<template>
  <div class="login-form">
    <h2>User Login</h2>
    <form @submit.prevent="handleLogin">
      <div class="form-group">
        <label for="login-email">Email or Username:</label>
        <input type="text" id="login-email" v-model="formData.email" required ref="loginEmailInput" />
      </div>
      <div class="form-group">
        <label for="login-password">Password:</label>
        <input type="password" id="login-password" v-model="formData.password" required ref="loginPasswordInput" />
      </div>
      <button type="submit" :disabled="isLoading">{{ isLoading ? 'Logging in...' : 'Login' }}</button>
    </form>
    <div v-if="message" :class="{'success-message': isSuccess, 'error-message': !isSuccess}">
      {{ message }}
    </div>
  </div>
</template>

<script>
import axios from 'axios';

const AUTH_API_URL = '/api/v1/auth';

export default {
  name: 'LoginForm',
  data() {
    return {
      formData: {
        email: '',
        password: ''
      },
      isLoading: false,
      message: '',
      isSuccess: false
    };
  },
  methods: {
    async handleLogin() {
      this.isLoading = true;
      this.message = '';
      this.isSuccess = false;

      // --- DIAGNOSTIC LOGS ---
      const emailFromRef = this.$refs.loginEmailInput?.value;
      const passwordFromRef = this.$refs.loginPasswordInput?.value;
      console.log('Values from refs:', { email: emailFromRef, password: passwordFromRef });
      console.log('Values from formData before creating payload:', { email: this.formData.email, password: this.formData.password });
      // --- END DIAGNOSTIC LOGS ---

      try {
        const payload = {
          email: this.formData.email,
          password: this.formData.password
        };
        console.log('Sending login payload:', payload);
        const response = await axios.post(`${AUTH_API_URL}/login/`, payload);
        const token = response.data.key;
        if (token) {
          localStorage.setItem('authToken', token);
          axios.defaults.headers.common['Authorization'] = `Token ${token}`;
          this.message = 'Login successful!';
          this.isSuccess = true;
          this.$emit('loggedIn');
        } else {
          this.message = 'Login successful, but token not found in response.';
          this.isSuccess = false;
          console.warn('Token not found in login response:', response.data);
        }
        console.log('Login response:', response.data);
      } catch (error) {
        this.isSuccess = false;
        if (error.response && error.response.data) {
          let errorMessages = [];
          if (error.response.data.non_field_errors) {
            errorMessages.push(error.response.data.non_field_errors.join(', '));
          }
          for (const key in error.response.data) {
            if (key !== 'non_field_errors' && Array.isArray(error.response.data[key])) {
              errorMessages.push(`${key}: ${error.response.data[key].join(', ')}`);
            }
          }
          this.message = errorMessages.length > 0 ? errorMessages.join('; ') : 'Login failed. Please check your credentials.';
        } else {
          this.message = 'An unexpected error occurred during login.';
        }
        console.error('Login error:', error.response ? error.response.data : error);
      } finally {
        this.isLoading = false;
      }
    }
  }
};
</script>

<style scoped>
.login-form {
  max-width: 400px;
  margin: 20px auto;
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 8px;
  background-color: #fff;
}
.form-group {
  margin-bottom: 15px;
}
.form-group label {
  display: block;
  margin-bottom: 5px;
}
.form-group input {
  width: calc(100% - 22px);
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
}
button {
  padding: 10px 15px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
button:disabled {
  background-color: #ccc;
}
.success-message {
  margin-top: 15px;
  padding: 10px;
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
  border-radius: 4px;
}
.error-message {
  margin-top: 15px;
  padding: 10px;
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
  border-radius: 4px;
}
</style> 