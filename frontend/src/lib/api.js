import axios from 'axios';

// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    const message = error.response?.data?.error || error.message || '请求失败';
    return Promise.reject(new Error(message));
  }
);

// API方法
export const apiService = {
  // 获取所有表
  getTables: () => api.get('/tables'),
  
  // 获取表结构
  getTableColumns: (tableName) => api.get(`/tables/${tableName}/columns`),
  
  // 执行SQL查询
  executeQuery: (query, page = 1, pageSize = 50) => 
    api.post('/query', { query, page, page_size: pageSize }),
  
  // 自然语言查询
  naturalLanguageQuery: (question) => 
    api.post('/nl_query', { question }),
  
  // 数据分析
  analyzeData: (query, analysisType = 'summary') => 
    api.post('/analyze', { query, analysis_type: analysisType }),
  
  // 智能对话
  chat: (message, context = []) => 
    api.post('/chat', { message, context }),
  
  // 导出CSV
  exportCsv: (query, filename = 'export.csv') => 
    api.post('/export/csv', { query, filename }, { responseType: 'blob' }),
  
  // 导出Excel
  exportExcel: (query, filename = 'export.xlsx') => 
    api.post('/export/excel', { query, filename }, { responseType: 'blob' }),
  
  // 健康检查
  healthCheck: () => api.get('/health'),
};

export default api;

