import os

class Config:
    # MySQL数据库配置
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'access_user'
    MYSQL_PASSWORD = 'wvqbIcZwf5/qgm8V'
    MYSQL_DATABASE = 'access_migration_db'
    
    # OpenAI API配置
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_API_BASE = os.getenv('OPENAI_API_BASE')
    
    # Flask配置
    SECRET_KEY = 'asdf#FGSgvasgf$5$WGT'
    
    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

