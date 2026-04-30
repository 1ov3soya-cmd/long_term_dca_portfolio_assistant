"""项目自定义异常。"""


class ConfigError(Exception):
    """配置缺失、格式错误或关键约束不满足时抛出。"""


class DataProviderError(Exception):
    """数据提供层不可用或返回结构异常时抛出。"""


class CacheError(Exception):
    """本地缓存读写失败时抛出。"""


class BacktestError(Exception):
    """回测执行过程中出现关键错误时抛出。"""
