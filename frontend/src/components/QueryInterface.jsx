import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Loader2, Play, Download, Database, MessageSquare } from 'lucide-react';
import { apiService } from '@/lib/api';
import DataTable from './DataTable';
import { toast } from 'sonner';

const QueryInterface = () => {
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState('');
  const [tableColumns, setTableColumns] = useState([]);
  const [sqlQuery, setSqlQuery] = useState('');
  const [nlQuery, setNlQuery] = useState('');
  const [queryResult, setQueryResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('sql');

  // 加载表列表
  useEffect(() => {
    const loadTables = async () => {
      try {
        const response = await apiService.getTables();
        if (response.success) {
          setTables(response.data);
        }
      } catch (error) {
        toast.error('加载表列表失败: ' + error.message);
      }
    };
    loadTables();
  }, []);

  // 加载表结构
  useEffect(() => {
    if (selectedTable) {
      const loadColumns = async () => {
        try {
          const response = await apiService.getTableColumns(selectedTable);
          if (response.success) {
            setTableColumns(response.data);
          }
        } catch (error) {
          toast.error('加载表结构失败: ' + error.message);
        }
      };
      loadColumns();
    }
  }, [selectedTable]);

  // 执行SQL查询
  const executeSqlQuery = async () => {
    if (!sqlQuery.trim()) {
      toast.error('请输入SQL查询语句');
      return;
    }

    setLoading(true);
    try {
      const response = await apiService.executeQuery(sqlQuery);
      if (response.success) {
        setQueryResult(response.data);
        toast.success(`查询成功，返回 ${response.data.rows.length} 条记录`);
      }
    } catch (error) {
      toast.error('查询失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // 执行自然语言查询
  const executeNlQuery = async () => {
    if (!nlQuery.trim()) {
      toast.error('请输入您的问题');
      return;
    }

    setLoading(true);
    try {
      const response = await apiService.naturalLanguageQuery(nlQuery);
      if (response.success) {
        setQueryResult({
          rows: response.data.rows,
          sql: response.data.sql,
          question: response.data.question
        });
        setSqlQuery(response.data.sql); // 同步生成的SQL到SQL标签页
        toast.success(`查询成功，返回 ${response.data.rows.length} 条记录`);
      }
    } catch (error) {
      toast.error('查询失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // 导出数据
  const exportData = async (format) => {
    if (!queryResult || !queryResult.rows.length) {
      toast.error('没有数据可导出');
      return;
    }

    const query = queryResult.sql || sqlQuery;
    if (!query) {
      toast.error('没有可用的查询语句');
      return;
    }

    try {
      let response;
      const filename = `export_${Date.now()}`;
      
      if (format === 'csv') {
        response = await apiService.exportCsv(query, `${filename}.csv`);
      } else if (format === 'excel') {
        response = await apiService.exportExcel(query, `${filename}.xlsx`);
      }

      // 创建下载链接
      const url = window.URL.createObjectURL(new Blob([response]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${filename}.${format === 'csv' ? 'csv' : 'xlsx'}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast.success(`${format.toUpperCase()}文件导出成功`);
    } catch (error) {
      toast.error('导出失败: ' + error.message);
    }
  };

  // 生成示例查询
  const generateSampleQuery = () => {
    if (selectedTable) {
      setSqlQuery(`SELECT * FROM \`${selectedTable}\` LIMIT 10`);
    }
  };

  return (
    <div className="space-y-6">
      {/* 表选择器 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="w-5 h-5" />
            数据库表
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">选择表</label>
              <Select value={selectedTable} onValueChange={setSelectedTable}>
                <SelectTrigger>
                  <SelectValue placeholder="请选择一个表" />
                </SelectTrigger>
                <SelectContent>
                  {tables.map((table) => (
                    <SelectItem key={table.name} value={table.name}>
                      <div className="flex items-center justify-between w-full">
                        <span>{table.name}</span>
                        <Badge variant="secondary" className="ml-2">
                          {table.count} 条记录
                        </Badge>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button onClick={generateSampleQuery} disabled={!selectedTable}>
              生成示例查询
            </Button>
          </div>

          {/* 表结构信息 */}
          {tableColumns.length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium mb-2">表结构</h4>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                {tableColumns.map((column) => (
                  <Badge key={column.Field} variant="outline" className="text-xs">
                    {column.Field} ({column.Type})
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 查询界面 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="sql">SQL查询</TabsTrigger>
              <TabsTrigger value="nl">
                <MessageSquare className="w-4 h-4 mr-2" />
                自然语言查询
              </TabsTrigger>
            </TabsList>

            <TabsContent value="sql" className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">SQL查询语句</label>
                <Textarea
                  value={sqlQuery}
                  onChange={(e) => setSqlQuery(e.target.value)}
                  placeholder="输入您的SQL查询语句，例如: SELECT * FROM `10NC_based` LIMIT 10"
                  className="min-h-[120px] font-mono"
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={executeSqlQuery} disabled={loading}>
                  {loading ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4 mr-2" />
                  )}
                  执行查询
                </Button>
              </div>
            </TabsContent>

            <TabsContent value="nl" className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">自然语言问题</label>
                <Textarea
                  value={nlQuery}
                  onChange={(e) => setNlQuery(e.target.value)}
                  placeholder="用自然语言描述您的问题，例如: 显示所有产品的基本信息"
                  className="min-h-[120px]"
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={executeNlQuery} disabled={loading}>
                  {loading ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <MessageSquare className="w-4 h-4 mr-2" />
                  )}
                  智能查询
                </Button>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* 查询结果 */}
      {queryResult && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>查询结果</CardTitle>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => exportData('csv')}
                >
                  <Download className="w-4 h-4 mr-2" />
                  导出CSV
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => exportData('excel')}
                >
                  <Download className="w-4 h-4 mr-2" />
                  导出Excel
                </Button>
              </div>
            </div>
            {queryResult.question && (
              <p className="text-sm text-muted-foreground">
                问题: {queryResult.question}
              </p>
            )}
            {queryResult.sql && (
              <p className="text-sm text-muted-foreground font-mono bg-muted p-2 rounded">
                SQL: {queryResult.sql}
              </p>
            )}
          </CardHeader>
          <CardContent>
            <DataTable data={queryResult.rows} />
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default QueryInterface;

