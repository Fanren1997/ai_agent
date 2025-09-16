import csv
import pandas as pd
import tempfile
import os
from datetime import datetime

class ExportService:
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
    
    def export_to_csv(self, data, filename='export.csv'):
        """导出数据为CSV格式"""
        try:
            if not data:
                raise ValueError("没有数据可导出")
            
            # 确保文件名以.csv结尾
            if not filename.endswith('.csv'):
                filename += '.csv'
            
            # 生成临时文件路径
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(self.temp_dir, safe_filename)
            
            # 获取列名
            columns = list(data[0].keys()) if data else []
            
            # 写入CSV文件
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=columns)
                writer.writeheader()
                writer.writerows(data)
            
            return file_path
            
        except Exception as e:
            raise Exception(f"CSV导出失败: {str(e)}")
    
    def export_to_excel(self, data, filename='export.xlsx'):
        """导出数据为Excel格式"""
        try:
            if not data:
                raise ValueError("没有数据可导出")
            
            # 确保文件名以.xlsx结尾
            if not filename.endswith('.xlsx'):
                filename += '.xlsx'
            
            # 生成临时文件路径
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(self.temp_dir, safe_filename)
            
            # 转换为DataFrame
            df = pd.DataFrame(data)
            
            # 写入Excel文件
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='数据', index=False)
                
                # 获取工作表对象以进行格式设置
                worksheet = writer.sheets['数据']
                
                # 自动调整列宽
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            return file_path
            
        except Exception as e:
            raise Exception(f"Excel导出失败: {str(e)}")
    
    def export_to_json(self, data, filename='export.json'):
        """导出数据为JSON格式"""
        try:
            if not data:
                raise ValueError("没有数据可导出")
            
            # 确保文件名以.json结尾
            if not filename.endswith('.json'):
                filename += '.json'
            
            # 生成临时文件路径
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(self.temp_dir, safe_filename)
            
            # 写入JSON文件
            import json
            with open(file_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, ensure_ascii=False, indent=2, default=str)
            
            return file_path
            
        except Exception as e:
            raise Exception(f"JSON导出失败: {str(e)}")
    
    def cleanup_temp_files(self, max_age_hours=24):
        """清理临时文件"""
        try:
            import glob
            import time
            
            # 查找临时目录中的导出文件
            patterns = [
                os.path.join(self.temp_dir, '*_export.csv'),
                os.path.join(self.temp_dir, '*_export.xlsx'),
                os.path.join(self.temp_dir, '*_export.json')
            ]
            
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for pattern in patterns:
                for file_path in glob.glob(pattern):
                    try:
                        file_age = current_time - os.path.getmtime(file_path)
                        if file_age > max_age_seconds:
                            os.remove(file_path)
                            print(f"已删除过期文件: {file_path}")
                    except Exception as e:
                        print(f"删除文件失败 {file_path}: {e}")
                        
        except Exception as e:
            print(f"清理临时文件失败: {e}")

