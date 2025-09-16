import { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { 
  Database, 
  MessageSquare, 
  BarChart3, 
  Settings, 
  Activity,
  RefreshCw,
  AlertCircle,
  CheckCircle
} from 'lucide-react';
import { Toaster } from 'sonner';
import QueryInterface from './components/QueryInterface';
import ChatInterface from './components/ChatInterface';
import { apiService } from './lib/api';
import { toast } from 'sonner';
import './App.css';

function App() {
  const [systemStatus, setSystemStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  // 检查系统状态
  const checkSystemHealth = async () => {
    try {
      const response = await apiService.healthCheck();
      if (response.success) {
        setSystemStatus(response.data);
      }
    } catch (error) {
      console.error('系统健康检查失败:', error);
      setSystemStatus({ status: 'error', error: error.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkSystemHealth();
  }, []);

  const refreshStatus = () => {
    setLoading(true);
    checkSystemHealth();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <Toaster position="top-right" />
      
      {/* 头部 */}
      <header className="bg-white border-b shadow-sm">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <Database className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  AI智慧体数据查询系统
                </h1>
                <p className="text-sm text-gray-600">
                  智能数据查询、分析与导出平台
                </p>
              </div>
            </div>

            {/* 系统状态 */}
            <div className="flex items-center gap-4">
              {loading ? (
                <div className="flex items-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span className="text-sm">检查中...</span>
                </div>
              ) : systemStatus ? (
                <div className="flex items-center gap-2">
                  {systemStatus.status === 'healthy' ? (
                    <>
                      <CheckCircle className="w-4 h-4 text-green-500" />
                      <Badge variant="outline" className="text-green-700 border-green-200">
                        系统正常
                      </Badge>
                      <Badge variant="secondary">
                        {systemStatus.tables_count} 个表
                      </Badge>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="w-4 h-4 text-red-500" />
                      <Badge variant="destructive">
                        系统异常
                      </Badge>
                    </>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={refreshStatus}
                    className="h-8 w-8 p-0"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </Button>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </header>

      {/* 主内容 */}
      <main className="container mx-auto px-4 py-8">
        {systemStatus?.status === 'error' ? (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-red-600">
                <AlertCircle className="w-5 h-5" />
                系统连接异常
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 mb-4">
                无法连接到后端服务，请检查：
              </p>
              <ul className="list-disc list-inside space-y-1 text-sm text-gray-600 mb-4">
                <li>后端服务是否正常运行</li>
                <li>数据库连接是否正常</li>
                <li>网络连接是否正常</li>
              </ul>
              <Button onClick={refreshStatus} variant="outline">
                <RefreshCw className="w-4 h-4 mr-2" />
                重新检查
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Tabs defaultValue="query" className="space-y-6">
            <TabsList className="grid w-full grid-cols-3 lg:w-[400px]">
              <TabsTrigger value="query" className="flex items-center gap-2">
                <Database className="w-4 h-4" />
                数据查询
              </TabsTrigger>
              <TabsTrigger value="chat" className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                智能对话
              </TabsTrigger>
              <TabsTrigger value="analytics" className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4" />
                数据分析
              </TabsTrigger>
            </TabsList>

            <TabsContent value="query" className="space-y-6">
              <QueryInterface />
            </TabsContent>

            <TabsContent value="chat" className="space-y-6">
              <ChatInterface />
            </TabsContent>

            <TabsContent value="analytics" className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    数据分析
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-center py-12">
                    <Activity className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-lg font-semibold mb-2">数据分析功能</h3>
                    <p className="text-muted-foreground mb-6">
                      使用查询界面执行查询后，可以在结果页面进行数据分析
                    </p>
                    <Button onClick={() => document.querySelector('[value="query"]').click()}>
                      前往查询界面
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        )}
      </main>

      {/* 页脚 */}
      <footer className="bg-white border-t mt-16">
        <div className="container mx-auto px-4 py-6">
          <div className="text-center text-sm text-gray-600">
            <p>AI智慧体数据查询系统 - 基于AI技术的智能数据管理平台</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;

