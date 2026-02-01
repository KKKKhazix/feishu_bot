"""配置管理模块"""
import os
from pathlib import Path
from dotenv import load_dotenv

class Config:
    """应用配置类"""
    
    def __init__(self):
        # 加载 .env 文件
        app_root = Path(__file__).parent.parent
        env_path = app_root / '.env'
        if not env_path.exists():
            repo_root = app_root.parent.parent
            env_path = repo_root / '.env'
        load_dotenv(env_path)
        
        # 飞书配置
        self.feishu_app_id = os.getenv('FEISHU_APP_ID', '')
        self.feishu_app_secret = os.getenv('FEISHU_APP_SECRET', '')
        
        # 火山引擎配置
        self.volcano_access_key = os.getenv('VOLCANO_ACCESS_KEY', '')
        self.volcano_secret_key = os.getenv('VOLCANO_SECRET_KEY', '')
        
        # 豆包配置
        self.doubao_api_key = os.getenv('DOUBAO_API_KEY', '')
        self.doubao_model_id = os.getenv('DOUBAO_MODEL_ID', '')
        
        # 日志级别
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # 验证必需配置
        self._validate()
    
    def _validate(self):
        """验证必需的配置项"""
        missing = []
        if not self.feishu_app_id:
            missing.append('FEISHU_APP_ID')
        if not self.feishu_app_secret:
            missing.append('FEISHU_APP_SECRET')
        
        if missing:
            raise ValueError(f"缺少必需的配置项: {', '.join(missing)}")
    
    def __bool__(self):
        return bool(self.feishu_app_id and self.feishu_app_secret)
