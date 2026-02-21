// src/api.js
import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:8000/api',
    withCredentials: true, // CRITICAL: sends Django session cookie cross-origin
});

export default api;