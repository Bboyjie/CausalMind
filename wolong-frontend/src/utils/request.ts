import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  // baseURL: '/api/v1',
  baseURL: 'http://localhost:8000/',
  timeout: 50000
})

// Request interceptor
request.interceptors.request.use(
  config => {
    // Inject the LLM routing configuration into a custom header
    const savedConfig = localStorage.getItem('wolong_llm_config')
    if (savedConfig) {
      // Encode as Base64 to safely transmit JSON over HTTP headers
      config.headers['X-Wolong-Config'] = btoa(encodeURIComponent(savedConfig))
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// Response interceptor
request.interceptors.response.use(
  response => {
    const res = response.data
    // Mock standard response wrapper
    if (res.code !== 200) {
      ElMessage.error(res.message || 'Error occurred')
      return Promise.reject(new Error(res.message || 'Error'))
    } else {
      return res
    }
  },
  error => {
    console.error('API Error:', error)
    const errorMsg = error.response?.data?.message || error.message || 'Network Error'
    ElMessage.error(errorMsg)
    return Promise.reject(error)
  }
)

export default request
