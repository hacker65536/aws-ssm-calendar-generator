"""Logging and monitoring configuration module.

Task 8.2 Implementation: ログとモニタリング機能の追加
- 適切なレベルでの構造化ログを実装
- パフォーマンス監視とメトリクスを追加
- デバッグモードと詳細出力を実装
"""

import logging
import logging.handlers
import json
import os
import sys
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import traceback
import psutil
import functools
from contextlib import contextmanager


class LogLevel(Enum):
    """ログレベル"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class LogFormat(Enum):
    """ログフォーマット"""
    SIMPLE = "simple"
    DETAILED = "detailed"
    JSON = "json"
    STRUCTURED = "structured"


@dataclass
class PerformanceMetric:
    """パフォーマンスメトリクス"""
    operation: str
    start_time: float
    end_time: float
    duration: float
    memory_before: float
    memory_after: float
    memory_delta: float
    cpu_percent: float
    thread_id: int
    success: bool
    error_message: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)


@dataclass
class SystemMetrics:
    """システムメトリクス"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    active_threads: int
    process_id: int
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class StructuredFormatter(logging.Formatter):
    """構造化ログフォーマッター"""
    
    def __init__(self, format_type: LogFormat = LogFormat.STRUCTURED):
        super().__init__()
        self.format_type = format_type
    
    def format(self, record: logging.LogRecord) -> str:
        """ログレコードをフォーマット"""
        
        # 基本情報
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread_id': record.thread,
            'thread_name': record.threadName,
            'process_id': record.process
        }
        
        # 追加コンテキスト情報
        if hasattr(record, 'error_context'):
            log_data['error_context'] = record.error_context
        
        if hasattr(record, 'performance_metric'):
            log_data['performance_metric'] = record.performance_metric
        
        if hasattr(record, 'system_metrics'):
            log_data['system_metrics'] = record.system_metrics
        
        if hasattr(record, 'operation'):
            log_data['operation'] = record.operation
        
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        
        # 例外情報
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # フォーマット別出力
        if self.format_type == LogFormat.JSON:
            return json.dumps(log_data, ensure_ascii=False, default=str)
        elif self.format_type == LogFormat.SIMPLE:
            return f"{log_data['timestamp']} [{log_data['level']}] {log_data['message']}"
        elif self.format_type == LogFormat.DETAILED:
            return (f"{log_data['timestamp']} [{log_data['level']}] "
                   f"{log_data['logger']}:{log_data['function']}:{log_data['line']} "
                   f"- {log_data['message']}")
        else:  # STRUCTURED
            return json.dumps(log_data, ensure_ascii=False, default=str, indent=2)


class PerformanceMonitor:
    """パフォーマンス監視クラス"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetric] = []
        self.active_operations: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
    
    @contextmanager
    def monitor_operation(self, operation_name: str, context: Optional[Dict[str, Any]] = None):
        """操作のパフォーマンスを監視"""
        operation_id = f"{operation_name}_{threading.get_ident()}_{time.time()}"
        
        # 開始メトリクス
        start_time = time.time()
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        cpu_before = process.cpu_percent()
        
        with self.lock:
            self.active_operations[operation_id] = {
                'operation': operation_name,
                'start_time': start_time,
                'memory_before': memory_before,
                'context': context or {}
            }
        
        success = True
        error_message = None
        
        try:
            yield operation_id
        except Exception as e:
            success = False
            error_message = str(e)
            raise
        finally:
            # 終了メトリクス
            end_time = time.time()
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            cpu_after = process.cpu_percent()
            
            metric = PerformanceMetric(
                operation=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                memory_before=memory_before,
                memory_after=memory_after,
                memory_delta=memory_after - memory_before,
                cpu_percent=(cpu_before + cpu_after) / 2,
                thread_id=threading.get_ident(),
                success=success,
                error_message=error_message,
                context=context
            )
            
            with self.lock:
                self.metrics.append(metric)
                if operation_id in self.active_operations:
                    del self.active_operations[operation_id]
            
            # パフォーマンスログ出力
            self._log_performance_metric(metric)
    
    def _log_performance_metric(self, metric: PerformanceMetric):
        """パフォーマンスメトリクスをログ出力"""
        log_level = logging.INFO if metric.success else logging.WARNING
        
        message = (f"Operation '{metric.operation}' completed in {metric.duration:.3f}s "
                  f"(Memory: {metric.memory_delta:+.2f}MB, CPU: {metric.cpu_percent:.1f}%)")
        
        self.logger.log(log_level, message, extra={
            'performance_metric': metric.to_dict(),
            'operation': metric.operation
        })
    
    def get_metrics_summary(self, operation: Optional[str] = None, 
                          time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """メトリクスサマリーを取得"""
        with self.lock:
            filtered_metrics = self.metrics.copy()
        
        # フィルタリング
        if operation:
            filtered_metrics = [m for m in filtered_metrics if m.operation == operation]
        
        if time_window:
            cutoff_time = time.time() - time_window.total_seconds()
            filtered_metrics = [m for m in filtered_metrics if m.start_time >= cutoff_time]
        
        if not filtered_metrics:
            return {'total_operations': 0}
        
        # 統計計算
        durations = [m.duration for m in filtered_metrics]
        memory_deltas = [m.memory_delta for m in filtered_metrics]
        cpu_percents = [m.cpu_percent for m in filtered_metrics]
        
        success_count = sum(1 for m in filtered_metrics if m.success)
        error_count = len(filtered_metrics) - success_count
        
        return {
            'total_operations': len(filtered_metrics),
            'success_count': success_count,
            'error_count': error_count,
            'success_rate': success_count / len(filtered_metrics) * 100,
            'duration_stats': {
                'min': min(durations),
                'max': max(durations),
                'avg': sum(durations) / len(durations),
                'total': sum(durations)
            },
            'memory_stats': {
                'min_delta': min(memory_deltas),
                'max_delta': max(memory_deltas),
                'avg_delta': sum(memory_deltas) / len(memory_deltas),
                'total_delta': sum(memory_deltas)
            },
            'cpu_stats': {
                'min': min(cpu_percents),
                'max': max(cpu_percents),
                'avg': sum(cpu_percents) / len(cpu_percents)
            }
        }
    
    def clear_metrics(self, older_than: Optional[timedelta] = None):
        """メトリクスをクリア"""
        with self.lock:
            if older_than:
                cutoff_time = time.time() - older_than.total_seconds()
                self.metrics = [m for m in self.metrics if m.start_time >= cutoff_time]
            else:
                self.metrics.clear()


class SystemMonitor:
    """システム監視クラス"""
    
    def __init__(self, monitoring_interval: float = 60.0):
        self.monitoring_interval = monitoring_interval
        self.metrics_history: List[SystemMetrics] = []
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
    
    def start_monitoring(self):
        """システム監視を開始"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info(f"System monitoring started (interval: {self.monitoring_interval}s)")
    
    def stop_monitoring(self):
        """システム監視を停止"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        self.logger.info("System monitoring stopped")
    
    def _monitoring_loop(self):
        """監視ループ"""
        while self.monitoring_active:
            try:
                metrics = self._collect_system_metrics()
                
                with self.lock:
                    self.metrics_history.append(metrics)
                    
                    # 古いメトリクスを削除（24時間以上古い）
                    cutoff_time = datetime.now() - timedelta(hours=24)
                    self.metrics_history = [
                        m for m in self.metrics_history 
                        if m.timestamp >= cutoff_time
                    ]
                
                # システムメトリクスをログ出力
                self._log_system_metrics(metrics)
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"System monitoring error: {e}")
                time.sleep(self.monitoring_interval)
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """システムメトリクスを収集"""
        process = psutil.Process()
        memory_info = psutil.virtual_memory()
        disk_info = psutil.disk_usage('/')
        
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=psutil.cpu_percent(interval=1),
            memory_percent=memory_info.percent,
            memory_used_mb=memory_info.used / 1024 / 1024,
            memory_available_mb=memory_info.available / 1024 / 1024,
            disk_usage_percent=disk_info.percent,
            disk_free_gb=disk_info.free / 1024 / 1024 / 1024,
            active_threads=threading.active_count(),
            process_id=os.getpid()
        )
    
    def _log_system_metrics(self, metrics: SystemMetrics):
        """システムメトリクスをログ出力"""
        message = (f"System metrics - CPU: {metrics.cpu_percent:.1f}%, "
                  f"Memory: {metrics.memory_percent:.1f}% "
                  f"({metrics.memory_used_mb:.0f}MB used), "
                  f"Disk: {metrics.disk_usage_percent:.1f}% "
                  f"({metrics.disk_free_gb:.1f}GB free), "
                  f"Threads: {metrics.active_threads}")
        
        # 警告レベルの判定
        log_level = logging.INFO
        if (metrics.cpu_percent > 80 or 
            metrics.memory_percent > 85 or 
            metrics.disk_usage_percent > 90):
            log_level = logging.WARNING
        
        self.logger.log(log_level, message, extra={
            'system_metrics': metrics.to_dict()
        })
    
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """現在のシステムメトリクスを取得"""
        return self._collect_system_metrics()
    
    def get_metrics_history(self, time_window: Optional[timedelta] = None) -> List[SystemMetrics]:
        """メトリクス履歴を取得"""
        with self.lock:
            metrics = self.metrics_history.copy()
        
        if time_window:
            cutoff_time = datetime.now() - time_window
            metrics = [m for m in metrics if m.timestamp >= cutoff_time]
        
        return metrics


class LoggingManager:
    """ログ管理クラス"""
    
    def __init__(self, 
                 log_dir: Optional[str] = None,
                 log_level: LogLevel = LogLevel.INFO,
                 log_format: LogFormat = LogFormat.STRUCTURED,
                 enable_console: bool = True,
                 enable_file: bool = True,
                 enable_performance_monitoring: bool = True,
                 enable_system_monitoring: bool = True,
                 max_log_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5):
        
        self.log_dir = Path(log_dir) if log_dir else Path.home() / '.aws-ssm-calendar' / 'logs'
        self.log_level = log_level
        self.log_format = log_format
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.max_log_size = max_log_size
        self.backup_count = backup_count
        
        # ログディレクトリ作成
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # パフォーマンス監視
        self.performance_monitor = PerformanceMonitor() if enable_performance_monitoring else None
        
        # システム監視
        self.system_monitor = SystemMonitor() if enable_system_monitoring else None
        
        # ロガー設定
        self._setup_logging()
        
        # 監視開始
        if self.system_monitor:
            self.system_monitor.start_monitoring()
    
    def _setup_logging(self):
        """ログ設定をセットアップ"""
        # ルートロガー設定
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level.value)
        
        # 既存ハンドラーをクリア
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # フォーマッター作成
        formatter = StructuredFormatter(self.log_format)
        
        # コンソールハンドラー
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level.value)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # ファイルハンドラー
        if self.enable_file:
            # 一般ログファイル
            log_file = self.log_dir / 'application.log'
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self.max_log_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(self.log_level.value)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
            # エラー専用ログファイル
            error_file = self.log_dir / 'errors.log'
            error_handler = logging.handlers.RotatingFileHandler(
                error_file,
                maxBytes=self.max_log_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            root_logger.addHandler(error_handler)
            
            # パフォーマンス専用ログファイル
            if self.performance_monitor:
                perf_file = self.log_dir / 'performance.log'
                perf_handler = logging.handlers.RotatingFileHandler(
                    perf_file,
                    maxBytes=self.max_log_size,
                    backupCount=self.backup_count,
                    encoding='utf-8'
                )
                perf_handler.setLevel(logging.INFO)
                perf_handler.setFormatter(StructuredFormatter(LogFormat.JSON))
                
                # パフォーマンスログ用のフィルター
                perf_handler.addFilter(lambda record: hasattr(record, 'performance_metric'))
                root_logger.addHandler(perf_handler)
    
    def set_debug_mode(self, enabled: bool):
        """デバッグモードを設定"""
        new_level = LogLevel.DEBUG if enabled else LogLevel.INFO
        self.log_level = new_level
        
        # 全ハンドラーのレベルを更新
        root_logger = logging.getLogger()
        root_logger.setLevel(new_level.value)
        
        for handler in root_logger.handlers:
            if not isinstance(handler, logging.handlers.RotatingFileHandler) or 'errors.log' not in str(handler.baseFilename):
                handler.setLevel(new_level.value)
        
        logging.getLogger(__name__).info(f"Debug mode {'enabled' if enabled else 'disabled'}")
    
    def monitor_operation(self, operation_name: str, context: Optional[Dict[str, Any]] = None):
        """操作監視のコンテキストマネージャー"""
        if self.performance_monitor:
            return self.performance_monitor.monitor_operation(operation_name, context)
        else:
            return self._dummy_context_manager()
    
    @contextmanager
    def _dummy_context_manager(self):
        """ダミーコンテキストマネージャー"""
        yield None
    
    def get_performance_summary(self, operation: Optional[str] = None, 
                              time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """パフォーマンスサマリーを取得"""
        if self.performance_monitor:
            return self.performance_monitor.get_metrics_summary(operation, time_window)
        return {'performance_monitoring': 'disabled'}
    
    def get_system_metrics(self) -> Optional[SystemMetrics]:
        """現在のシステムメトリクスを取得"""
        if self.system_monitor:
            return self.system_monitor.get_current_metrics()
        return None
    
    def cleanup(self):
        """リソースをクリーンアップ"""
        if self.system_monitor:
            self.system_monitor.stop_monitoring()
        
        if self.performance_monitor:
            self.performance_monitor.clear_metrics(older_than=timedelta(hours=1))


# デコレータ関数
def log_performance(operation_name: Optional[str] = None, 
                   context: Optional[Dict[str, Any]] = None):
    """パフォーマンス監視デコレータ"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            # グローバルロギングマネージャーを取得
            logging_manager = get_logging_manager()
            
            with logging_manager.monitor_operation(op_name, context):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def log_function_call(log_args: bool = False, log_result: bool = False):
    """関数呼び出しログデコレータ"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            func_name = f"{func.__module__}.{func.__name__}"
            
            # 関数開始ログ
            log_data = {'operation': func_name}
            if log_args:
                log_data['args'] = str(args)
                log_data['kwargs'] = str(kwargs)
            
            logger.debug(f"Function call started: {func_name}", extra=log_data)
            
            try:
                result = func(*args, **kwargs)
                
                # 関数完了ログ
                success_data = {'operation': func_name, 'success': True}
                if log_result:
                    success_data['result'] = str(result)
                
                logger.debug(f"Function call completed: {func_name}", extra=success_data)
                return result
                
            except Exception as e:
                # 関数エラーログ
                error_data = {
                    'operation': func_name,
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
                
                logger.error(f"Function call failed: {func_name}", extra=error_data)
                raise
        
        return wrapper
    return decorator


# グローバルロギングマネージャー
_global_logging_manager: Optional[LoggingManager] = None


def get_logging_manager() -> LoggingManager:
    """グローバルロギングマネージャーを取得"""
    global _global_logging_manager
    if _global_logging_manager is None:
        _global_logging_manager = LoggingManager()
    return _global_logging_manager


def setup_logging(
    log_dir: Optional[str] = None,
    log_level: LogLevel = LogLevel.INFO,
    log_format: LogFormat = LogFormat.STRUCTURED,
    enable_console: bool = True,
    enable_file: bool = True,
    enable_performance_monitoring: bool = True,
    enable_system_monitoring: bool = True,
    debug_mode: bool = False
) -> LoggingManager:
    """ログ設定をセットアップ"""
    global _global_logging_manager
    
    if debug_mode:
        log_level = LogLevel.DEBUG
    
    _global_logging_manager = LoggingManager(
        log_dir=log_dir,
        log_level=log_level,
        log_format=log_format,
        enable_console=enable_console,
        enable_file=enable_file,
        enable_performance_monitoring=enable_performance_monitoring,
        enable_system_monitoring=enable_system_monitoring
    )
    
    return _global_logging_manager


def set_debug_mode(enabled: bool):
    """デバッグモードを設定"""
    logging_manager = get_logging_manager()
    logging_manager.set_debug_mode(enabled)


def cleanup_logging():
    """ログリソースをクリーンアップ"""
    global _global_logging_manager
    if _global_logging_manager:
        _global_logging_manager.cleanup()
        _global_logging_manager = None