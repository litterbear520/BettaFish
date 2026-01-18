"""
重试机制工具模块
提供通用的网络请求重试功能，增强系统健壮性
"""

import time
from functools import wraps
from typing import Callable, Any
import requests
from loguru import logger

# 配置日志
class RetryConfig:
    """重试配置类"""
    
    def __init__(
        self,
        max_retries: int = 3,
        delay: float = 1.0,
        delay_factor: float = 2.0,
        max_delay: float = 60.0,
        retry_on_exceptions: tuple = None
    ):
        """
        初始化重试配置

        Args:
            max_retries: 最大重试次数
            delay: 初始延迟秒数
            delay_factor: 退避因子（每次重试延迟翻倍）
            max_delay: 最大延迟秒数
            retry_on_exceptions: 需要重试的异常类型元组
        """
        self.max_retries = max_retries
        self.delay = delay
        self.delay_factor = delay_factor
        self.max_delay = max_delay
        
        # 默认需要重试的异常类型
        if retry_on_exceptions is None:
            self.retry_on_exceptions = (
                requests.exceptions.RequestException,
                requests.exceptions.ConnectionError,
                requests.exceptions.HTTPError,
                requests.exceptions.Timeout,
                requests.exceptions.TooManyRedirects,
                ConnectionError,
                TimeoutError,
                Exception  # OpenAI和其他API可能抛出的一般异常
            )
        else:
            self.retry_on_exceptions = retry_on_exceptions

# 默认配置
DEFAULT_RETRY_CONFIG = RetryConfig()

def with_retry(config: RetryConfig = None):
    """重试装饰器
    
    :param config: 重试配置，如果不提供则使用默认配置
    :param returns: 装饰器函数
    """
    if config is None:
        config = DEFAULT_RETRY_CONFIG
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for retry in range(config.max_retries + 1):  # +1 因为第一次不算重试
                try:
                    result = func(*args, **kwargs)
                    if retry > 0:
                        logger.info(f"函数{func.__name__}重试{retry}次后成功")
                    return result
                    
                except config.retry_on_exceptions as e:
                    if retry == config.max_retries:
                        # 最后一次尝试也失败了
                        logger.error(f"函数{func.__name__}在{config.max_retries}次重试后仍然失败")
                        logger.error(f"最终错误: {str(e)}")
                        raise e

                    # 计算延迟时间
                    delay = min(
                        config.delay * (config.delay_factor ** retry),
                        config.max_delay
                    )

                    logger.warning(f"函数{func.__name__}第{retry+1}次运行失败: {str(e)}")
                    logger.info(f"将在{delay:.1f}秒后进行第{retry+1}次尝试...")
                    
                    time.sleep(delay)
                
                except Exception as e:
                    # 不在重试列表中的异常，直接抛出
                    logger.error(f"函数 {func.__name__} 遇到不可重试的异常: {str(e)}")
                    raise e
        return wrapper
    return decorator

def retry_on_network_error(
    max_retries: int = 3,
    delay: float = 1.0,
    delay_factor: float = 2.0
):
    """
    专门用于网络错误的重试装饰器（简化版）

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟秒数
        delay_factor: 退避因子

    Returns:
        装饰器函数
    """
    config = RetryConfig(
        max_retries=max_retries,
        delay=delay,
        delay_factor=delay_factor
    )
    return with_retry(config)

class RetryableError(Exception):
    """自定义的可重试异常"""
    pass

def silent_retry(config: RetryConfig= None, default_return=None):
    """
    静默重试装饰器：失败后返回默认值，不抛异常

    :param config: 重试配置不提供则使用默认配置
    :param default_return: 所有重试失败后返回的默认值
    :return: 装饰器函数
    """
    if config is None:
        config = SEARCH_API_RETRY_CONFIG
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for retry in range(config.max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if retry > 0: # 第0次为正常运行，不记录日志
                        logger.info(f"非关键函数{func.__name__}重试{retry}次后成功")
                    return result

                except config.retry_on_exceptions as e:
                    if retry == config.max_retries:
                        # 最后一次尝试也失败了，返回默认值而不抛出异常
                        logger.warning(f"非关键函数{func.__name__}在{config.max_retries}次重试后仍然失败，最终错误: {str(e)}")
                        logger.info(f"返回默认值以保证系统继续运行: {default_return}")
                        return default_return
                    
                    delay = min(
                        config.delay * (config.delay_factor ** retry),
                        config.max_delay
                    )

                    logger.warning(f"非关键函数{func.__name__}第{retry+1}次运行失败: {str(e)}")
                    logger.info(f"将在{delay:.1f}秒后进行第{retry + 1}次重试...")
                    
                    time.sleep(delay)
                
                except Exception as e:
                    # 不在重试列表中的异常，返回默认值
                    logger.warning(f"非关键函数{func.__name__}遇到不可重试的异常: {str(e)}")
                    logger.info(f"返回默认值以保证系统继续运行: {default_return}")
                    return default_return
        return wrapper
    return decorator

def make_retryable_request(
    request_func: Callable,
    *args,
    max_retries: int = 5,
    **kwargs
) -> Any:
    """
    直接执行可重试的请求（不使用装饰器）
    
    Args:
        request_func: 要执行的请求函数
        *args: 传递给请求函数的位置参数
        max_retries: 最大重试次数
        **kwargs: 传递给请求函数的关键字参数
    
    Returns:
        请求函数的返回值
    """
    config = RetryConfig(max_retries=max_retries)
    
    @with_retry(config)
    def _execute():
        return request_func(*args, **kwargs)
    
    return _execute()

# 预定义一些常用的重试配置
LLM_RETRY_CONFIG = RetryConfig(
    max_retries=6,        # 保持额外重试次数
    delay=60.0,           # 首次等待至少 1 分钟
    delay_factor=2.0,     # 继续使用指数退避
    max_delay=600.0       # 单次等待最长 10 分钟
)

SEARCH_API_RETRY_CONFIG = RetryConfig(
    max_retries=5,        # 增加到5次重试
    delay=2.0,            # 增加初始延迟
    delay_factor=1.6,     # 调整退避因子
    max_delay=25.0        # 增加最大延迟
)

DB_RETRY_CONFIG = RetryConfig(
    max_retries=5,        # 增加到5次重试
    delay=1.0,            # 保持较短的数据库重试延迟
    delay_factor=1.5,
    max_delay=10.0
)


if __name__ == "__main__":
    # 测试 silent_retry 装饰器
    test_config = RetryConfig(
        max_retries=3,
        max_delay=1.0
    )

    # 测试1：模拟失败2次后成功
    call_count = 0

    @silent_retry(config=test_config, default_return="默认值")
    def test_1():
        global call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError(f"模拟连接失败 (第{call_count}次)")
        return "成功返回"

    print("=== 测试1: 重试后成功 ===")
    result = test_1()
    print(f"结果: {result}\n")

    # 测试2：模拟一直失败，返回默认值
    @silent_retry(config=test_config, default_return="默认值")
    def test_2():
        raise ConnectionError("一直失败")

    print("=== 测试2: 重试后仍失败，返回默认值 ===")
    result = test_2()
    print(f"结果: {result}\n")

    # 测试3：模拟不可重试的异常
    @silent_retry(config=test_config, default_return="默认值")
    def test_3():
        raise ValueError("不可重试的异常")

    print("=== 测试3: 不可重试的异常 ===")
    result = test_3()
    print(f"结果: {result}\n")

    # 测试 with_retry 装饰器
    print("=== 测试 with_retry 装饰器 ===")
    call_count_2 = 0

    @with_retry(config=test_config)
    def test_with_retry():
        global call_count_2
        call_count_2 += 1
        if call_count_2 < 2:
            raise ConnectionError(f"失败")
        return "with_retry 成功"

    print("测试: 失败1次后成功")
    result = test_with_retry()
    print(f"结果: {result}\n")

    # 测试 with_retry 装饰器 - 最大尝试次数都失败
    print("=== 测试 with_retry 装饰器 - 全部失败 ===")

    @with_retry(config=test_config)
    def test_with_retry_fail():
        raise ConnectionError("一直失败")

    print("测试: 最大尝试次数都失败，应该抛出异常")
    try:
        result = test_with_retry_fail()
    except ConnectionError as e:
        print(f"捕获异常: {e}")
