import axios from 'axios';

const BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 300000, // 5 min for large uploads
});

// ─── Editor API ───
export const editorApi = {
  transcribeVideo: (formData) =>
    api.post('/editor/transcribe', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  startProcessing: (formData) =>
    api.post('/editor/process', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  getStatus: (jobId) => api.get(`/editor/status/${jobId}`),
  stopJob: (jobId) => api.post(`/editor/stop/${jobId}`),
  listJobs: () => api.get('/editor/jobs'),
  downloadUrl: (jobId, filename) =>
    `${BASE_URL}/editor/download/${jobId}/${filename}`,
};

// ─── Uploader API ───
export const uploaderApi = {
  // Auth
  uploadSecret: (files) => {
    const fd = new FormData();
    if (Array.isArray(files)) {
      files.forEach(file => fd.append('files', file));
    } else {
      fd.append('files', files);
    }
    return api.post('/uploader/auth/upload-secret', fd);
  },
  startAuth: () => api.get('/uploader/auth/start'),
  getAuthStatus: () => api.get('/uploader/auth/status'),
  logout: (channel_id) => api.delete(`/uploader/auth/logout?channel_id=${channel_id}`),

  // Upload
  uploadSingle: (formData) =>
    api.post('/uploader/upload/single', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  uploadBatchWithFiles: (formData) =>
    api.post('/uploader/upload/batch-with-files', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  getStatus: (jobId) => api.get(`/uploader/status/${jobId}`),

  // Info
  getPlaylists: (channel_id) => api.get(`/uploader/playlists?channel_id=${channel_id}`),
  getCategories: () => api.get('/uploader/categories'),

  // Processed Videos
  getProcessedVideos: () => api.get('/uploader/processed-videos'),
  deleteProcessedVideos: (paths) => api.post('/uploader/delete-processed-videos', { paths }),
  watchVideo: (path) => api.post('/uploader/watch-video', { path }),
};

// ─── Health ───
export const healthCheck = () => api.get('/health');

export { BASE_URL };
export default api;
