"""
Query Engine 配置管理模块，支持从环境变量和 .env 文件自动加载。
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from loguru import logger


# 计算 .env 优先级：优先当前工作目录，其次项目根目录
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
CWD_ENV: Path = Path.cwd() / ".env"
ENV_FILE: str = str(CWD_ENV if CWD_ENV.exists() else (PROJECT_ROOT / ".env"))


class Settings(BaseSettings):
    """搜索智能体全局配置，支持.env和环境变量自动加载。"""
    
    # ======================= LLM 相关 =======================
    QUERY_ENGINE_API_KEY: str = Field(..., description="Query Engine LLM API密钥，用于主LLM。您可以更改每个部分LLM使用的API，🚩只要兼容OpenAI请求格式都可以，定义好KEY、BASE_URL与MODEL_NAME即可正常使用。")
    QUERY_ENGINE_BASE_URL: Optional[str] = Field(None, description="Query Engine LLM接口BaseUrl，可自定义厂商API")
    QUERY_ENGINE_MODEL_NAME: str = Field(..., description="Query Engine LLM模型名称")
    QUERY_ENGINE_PROVIDER: Optional[str] = Field(None, description="Query Engine LLM提供商（兼容字段）")
    
    # ================== 网络工具配置 ====================
    TAVILY_API_KEY: str = Field(..., description="Tavily API（申请地址：https://www.tavily.com/）API密钥，用于Tavily网络搜索")
    
    # ================== 搜索参数配置 ====================
    SEARCH_TIMEOUT: int = Field(240, description="搜索超时（秒）")
    SEARCH_CONTENT_MAX_LENGTH: int = Field(20000, description="用于提示的最长内容长度")
    MAX_REFLECTIONS: int = Field(2, description="最大反思轮数")
    MAX_PARAGRAPHS: int = Field(5, description="最大段落数")
    MAX_SEARCH_RESULTS: int = Field(20, description="最大搜索结果数")
    
    # ================== 输出配置 ====================
    OUTPUT_DIR: str = Field("reports", description="输出目录")
    SAVE_INTERMEDIATE_STATES: bool = Field(True, description="是否保存中间状态")
    
    class Config:
        env_file = ENV_FILE    # 从.env读取环境变量
        env_prefix = ""        # 环境变量前缀
        case_sensitive = False # 字段不区分大小写
        extra = "allow"        # 允许额外的字段


# 创建全局配置实例
settings = Settings()

def print_config(config: Settings):
    """打印配置信息

    :param config: Settings配置对象
    """
    message = "\n"  # 开始添加换行
    message += "=== Query Engine 配置 ===\n"
    message += f"LLM 模型: {config.QUERY_ENGINE_MODEL_NAME}\n"
    message += f"LLM Base URL: {config.QUERY_ENGINE_BASE_URL or '(默认)'}\n"
    message += f"Tavily API Key: {'已配置' if config.TAVILY_API_KEY else '未配置'}\n"
    message += f"搜索超时: {config.SEARCH_TIMEOUT} 秒\n"
    message += f"最长内容长度: {config.SEARCH_CONTENT_MAX_LENGTH}\n"
    message += f"最大反思次数: {config.MAX_REFLECTIONS}\n"
    message += f"最大段落数: {config.MAX_PARAGRAPHS}\n"
    message += f"最大搜索结果数: {config.MAX_SEARCH_RESULTS}\n"
    message += f"输出目录: {config.OUTPUT_DIR}\n"
    message += f"保存中间状态: {config.SAVE_INTERMEDIATE_STATES}\n"
    message += f"LLM API Key: {'已配置' if config.QUERY_ENGINE_API_KEY else '未配置'}\n"
    message += "========================\n"
    logger.info(message)


if __name__ == "__main__":
    print("当前配置信息：")
    print_config(settings)