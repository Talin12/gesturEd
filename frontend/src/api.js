import axios from 'axios';

const api = axios.create({
    baseURL: '/api', // CHANGED: Vite will now route this to localhost:8000/api
    withCredentials: true, 
});

export default api;