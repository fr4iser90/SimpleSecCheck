import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import axios from 'axios'

// Import global styles
import './assets/global.css'

// Axios base URL (optional, if you have a common API prefix)
// axios.defaults.baseURL = 'http://localhost:8000' // Example, adjust if needed

// Create and mount the Vue application
const app = createApp(App)

// Make axios available globally on the app instance (optional, alternative to importing in each component)
// app.config.globalProperties.$axios = axios

app.mount('#app')
