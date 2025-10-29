"""Error handling framework module.

Task 8.1 Implementation: エラーハンドリングフレームワークの実装
- 異なるエラータイプ用のカスタム例外クラスを作成
- エラー回復戦略とフォールバックメカニズムを追加
- ユーザーフレンドリーなエラーメッセージを実装
"""

import logging
import traceback
import sys
from typing import Dict, Any, Optional, Callable, List, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path


class ErrorSeverity(Enum):
    """エラー重要度レベル"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ErrorCategory(Enum):
    """エラーカテゴリ"""
    NETWORK = "network"
    AWS = "aws"
    DATA = "data"
    FILE_SYSTEM = "file_system"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    MEMORY = "memory"
    ENCODING = "encoding"
    PARSING = "parsing"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """エラーコンテキスト情報"""
    timestamp: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    operation: str
    user_message: str
    technical_message: str
    recovery_suggestions: List[str]
    context_data: Dict[str, Any]
    stack_trace: Optional[str] = None


class BaseApplicationError(Exception):
    """アプリケーション基底例外クラス"""
    
    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        operation: str = "",
        recovery_suggestions: Optional[List[str]] = None,
        context_data: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.severity = severity
        self.category = category
        self.operation = operation
        self.recovery_suggestions = recovery_suggestions or []
        self.context_data = context_data or {}
        self.cause = cause
        self.timestamp = datetime.now()
    
    def get_user_message(self) -> str:
        """ユーザーフレンドリーなエラーメッセージを取得"""
        return str(self)
    
    def get_technical_message(self) -> str:
        """技術的な詳細メッセージを取得"""
        technical_msg = f"{self.__class__.__name__}: {str(self)}"
        if self.cause:
            technical_msg += f" (Caused by: {type(self.cause).__name__}: {str(self.cause)})"
        return technical_msg
    
    def to_error_context(self) -> ErrorContext:
        """ErrorContextオブジェクトに変換"""
        return ErrorContext(
            timestamp=self.timestamp,
            severity=self.severity,
            category=self.category,
            operation=self.operation,
            user_message=self.get_user_message(),
            technical_message=self.get_technical_message(),
            recovery_suggestions=self.recovery_suggestions,
            context_data=self.context_data,
            stack_trace=traceback.format_exc() if sys.exc_info()[0] else None
        )


# ネットワーク関連エラー
class NetworkError(BaseApplicationError):
    """ネットワーク接続エラー"""
    
    def __init__(self, message: str, url: str = "", timeout: int = 0, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.NETWORK,
            recovery_suggestions=[
                "インターネット接続を確認してください",
                "ファイアウォール設定を確認してください",
                "しばらく時間をおいて再試行してください",
                "プロキシ設定を確認してください"
            ],
            context_data={"url": url, "timeout": timeout},
            **kwargs
        )


class ConnectionTimeoutError(NetworkError):
    """接続タイムアウトエラー"""
    
    def __init__(self, url: str, timeout: int, **kwargs):
        super().__init__(
            f"接続がタイムアウトしました: {url} (タイムアウト: {timeout}秒)",
            url=url,
            timeout=timeout,
            recovery_suggestions=[
                f"タイムアウト値を{timeout * 2}秒以上に増やしてください",
                "ネットワーク接続の安定性を確認してください",
                "サーバーの応答状況を確認してください"
            ],
            **kwargs
        )


class DNSResolutionError(NetworkError):
    """DNS解決エラー"""
    
    def __init__(self, hostname: str, **kwargs):
        super().__init__(
            f"ホスト名を解決できません: {hostname}",
            recovery_suggestions=[
                "ホスト名のスペルを確認してください",
                "DNS設定を確認してください",
                "インターネット接続を確認してください"
            ],
            context_data={"hostname": hostname},
            **kwargs
        )


# AWS関連エラー
class AWSError(BaseApplicationError):
    """AWS関連エラー"""
    
    def __init__(self, message: str, service: str = "", operation: str = "", **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.AWS,
            operation=operation,
            recovery_suggestions=[
                "AWS認証情報を確認してください",
                "IAM権限を確認してください",
                "AWSサービスの状態を確認してください"
            ],
            context_data={"service": service, "operation": operation},
            **kwargs
        )


class AWSAuthenticationError(AWSError):
    """AWS認証エラー"""
    
    def __init__(self, message: str = "AWS認証に失敗しました", **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.CRITICAL,
            recovery_suggestions=[
                "AWS認証情報（Access Key、Secret Key）を確認してください",
                "AWS CLIで 'aws configure' を実行してください",
                "IAMユーザーまたはロールの権限を確認してください",
                "MFA設定が必要な場合は、セッショントークンを確認してください"
            ],
            **kwargs
        )


class AWSPermissionError(AWSError):
    """AWS権限エラー"""
    
    def __init__(self, action: str, resource: str = "", **kwargs):
        super().__init__(
            f"AWS操作の権限がありません: {action}" + (f" on {resource}" if resource else ""),
            recovery_suggestions=[
                f"IAMポリシーで '{action}' 権限を確認してください",
                "IAMユーザーまたはロールにポリシーがアタッチされているか確認してください",
                "リソースベースのポリシーを確認してください",
                "AWS管理者に権限の付与を依頼してください"
            ],
            context_data={"action": action, "resource": resource},
            **kwargs
        )


class AWSResourceNotFoundError(AWSError):
    """AWSリソース未発見エラー"""
    
    def __init__(self, resource_type: str, resource_name: str, **kwargs):
        super().__init__(
            f"{resource_type}が見つかりません: {resource_name}",
            recovery_suggestions=[
                f"{resource_type}名のスペルを確認してください",
                f"正しいAWSリージョンを指定しているか確認してください",
                f"{resource_type}が存在するか確認してください",
                "AWS管理コンソールで確認してください"
            ],
            context_data={"resource_type": resource_type, "resource_name": resource_name},
            **kwargs
        )


# データ関連エラー
class DataError(BaseApplicationError):
    """データ関連エラー"""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.DATA,
            **kwargs
        )


class DataIntegrityError(DataError):
    """データ整合性エラー"""
    
    def __init__(self, message: str, data_source: str = "", **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            recovery_suggestions=[
                "データソースの整合性を確認してください",
                "データを再取得してください",
                "データ形式が正しいか確認してください"
            ],
            context_data={"data_source": data_source},
            **kwargs
        )


class DataValidationError(DataError):
    """データ検証エラー"""
    
    def __init__(self, field: str, value: Any, expected_format: str = "", **kwargs):
        super().__init__(
            f"データ検証エラー: {field} = {value}" + (f" (期待形式: {expected_format})" if expected_format else ""),
            recovery_suggestions=[
                f"{field}の値を確認してください",
                f"正しい形式で入力してください" + (f": {expected_format}" if expected_format else ""),
                "入力データの形式を確認してください"
            ],
            context_data={"field": field, "value": value, "expected_format": expected_format},
            **kwargs
        )


# ファイルシステム関連エラー
class FileSystemError(BaseApplicationError):
    """ファイルシステムエラー"""
    
    def __init__(self, message: str, file_path: str = "", **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.FILE_SYSTEM,
            recovery_suggestions=[
                "ファイルパスを確認してください",
                "ファイル権限を確認してください",
                "ディスク容量を確認してください"
            ],
            context_data={"file_path": file_path},
            **kwargs
        )


class FileNotFoundError(FileSystemError):
    """ファイル未発見エラー"""
    
    def __init__(self, file_path: str, **kwargs):
        super().__init__(
            f"ファイルが見つかりません: {file_path}",
            file_path=file_path,
            recovery_suggestions=[
                "ファイルパスが正しいか確認してください",
                "ファイルが存在するか確認してください",
                "相対パスではなく絶対パスを使用してください",
                "ファイルの読み取り権限があるか確認してください"
            ],
            **kwargs
        )


class FilePermissionError(FileSystemError):
    """ファイル権限エラー"""
    
    def __init__(self, file_path: str, operation: str, **kwargs):
        super().__init__(
            f"ファイル{operation}権限がありません: {file_path}",
            file_path=file_path,
            recovery_suggestions=[
                f"ファイルの{operation}権限を確認してください",
                "ファイル所有者を確認してください",
                "管理者権限で実行してください",
                f"chmod コマンドでファイル権限を変更してください"
            ],
            context_data={"operation": operation},
            **kwargs
        )


class DiskSpaceError(FileSystemError):
    """ディスク容量不足エラー"""
    
    def __init__(self, required_space: int = 0, available_space: int = 0, **kwargs):
        super().__init__(
            f"ディスク容量が不足しています (必要: {required_space}MB, 利用可能: {available_space}MB)",
            severity=ErrorSeverity.HIGH,
            recovery_suggestions=[
                "不要なファイルを削除してください",
                "別のディスクに保存してください",
                "ディスククリーンアップを実行してください"
            ],
            context_data={"required_space": required_space, "available_space": available_space},
            **kwargs
        )


# エンコーディング関連エラー
class EncodingError(BaseApplicationError):
    """文字エンコーディングエラー"""
    
    def __init__(self, message: str, encoding: str = "", **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.ENCODING,
            recovery_suggestions=[
                "ファイルの文字エンコーディングを確認してください",
                "UTF-8エンコーディングを使用してください",
                "文字エンコーディングを明示的に指定してください"
            ],
            context_data={"encoding": encoding},
            **kwargs
        )


# 設定関連エラー
class ConfigurationError(BaseApplicationError):
    """設定エラー"""
    
    def __init__(self, message: str, config_key: str = "", **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.CONFIGURATION,
            recovery_suggestions=[
                "設定ファイルを確認してください",
                "環境変数を確認してください",
                "デフォルト設定を使用してください"
            ],
            context_data={"config_key": config_key},
            **kwargs
        )


# 検証関連エラー
class ValidationError(BaseApplicationError):
    """入力検証エラー"""
    
    def __init__(self, message: str, field: str = "", value: Any = None, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.VALIDATION,
            recovery_suggestions=[
                "入力値を確認してください",
                "正しい形式で入力してください",
                "入力データの妥当性を確認してください"
            ],
            context_data={"field": field, "value": value},
            **kwargs
        )


# メモリ関連エラー
class MemoryError(BaseApplicationError):
    """メモリ関連エラー"""
    
    def __init__(self, message: str, memory_usage: float = 0.0, memory_limit: float = 0.0, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.MEMORY,
            recovery_suggestions=[
                "メモリ使用量を削減してください",
                "不要なデータをクリアしてください",
                "処理を分割してください",
                "メモリ制限を増やしてください"
            ],
            context_data={"memory_usage": memory_usage, "memory_limit": memory_limit},
            **kwargs
        )


class ErrorRecoveryStrategy:
    """エラー回復戦略クラス"""
    
    def __init__(self, name: str, handler: Callable, max_retries: int = 3, delay: float = 1.0):
        self.name = name
        self.handler = handler
        self.max_retries = max_retries
        self.delay = delay
    
    def execute(self, error: BaseApplicationError, context: Dict[str, Any]) -> bool:
        """回復戦略を実行
        
        Returns:
            True if recovery was successful, False otherwise
        """
        try:
            return self.handler(error, context)
        except Exception as e:
            logging.getLogger(__name__).error(f"Recovery strategy '{self.name}' failed: {e}")
            return False


class ErrorHandler:
    """統合エラーハンドラー"""
    
    def __init__(self, log_file: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.recovery_strategies: Dict[ErrorCategory, List[ErrorRecoveryStrategy]] = {}
        self.error_history: List[ErrorContext] = []
        self.log_file = log_file
        
        # デフォルト回復戦略を登録
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """デフォルト回復戦略を登録"""
        
        # ネットワークエラー回復戦略
        self.register_recovery_strategy(
            ErrorCategory.NETWORK,
            ErrorRecoveryStrategy(
                "retry_with_backoff",
                self._retry_with_exponential_backoff,
                max_retries=3,
                delay=1.0
            )
        )
        
        self.register_recovery_strategy(
            ErrorCategory.NETWORK,
            ErrorRecoveryStrategy(
                "use_cached_data",
                self._use_cached_data,
                max_retries=1
            )
        )
        
        # ファイルシステムエラー回復戦略
        self.register_recovery_strategy(
            ErrorCategory.FILE_SYSTEM,
            ErrorRecoveryStrategy(
                "create_directory",
                self._create_missing_directory,
                max_retries=1
            )
        )
        
        self.register_recovery_strategy(
            ErrorCategory.FILE_SYSTEM,
            ErrorRecoveryStrategy(
                "use_alternative_path",
                self._use_alternative_file_path,
                max_retries=1
            )
        )
        
        # メモリエラー回復戦略
        self.register_recovery_strategy(
            ErrorCategory.MEMORY,
            ErrorRecoveryStrategy(
                "garbage_collect",
                self._force_garbage_collection,
                max_retries=1
            )
        )
        
        # エンコーディングエラー回復戦略
        self.register_recovery_strategy(
            ErrorCategory.ENCODING,
            ErrorRecoveryStrategy(
                "try_alternative_encoding",
                self._try_alternative_encoding,
                max_retries=3
            )
        )
    
    def register_recovery_strategy(self, category: ErrorCategory, strategy: ErrorRecoveryStrategy):
        """回復戦略を登録"""
        if category not in self.recovery_strategies:
            self.recovery_strategies[category] = []
        self.recovery_strategies[category].append(strategy)
    
    def handle_error(
        self,
        error: Union[BaseApplicationError, Exception],
        context: Optional[Dict[str, Any]] = None,
        attempt_recovery: bool = True
    ) -> ErrorContext:
        """エラーを処理
        
        Args:
            error: 処理するエラー
            context: エラーコンテキスト
            attempt_recovery: 回復を試行するかどうか
            
        Returns:
            ErrorContext: エラーコンテキスト情報
        """
        context = context or {}
        
        # BaseApplicationErrorでない場合は変換
        if not isinstance(error, BaseApplicationError):
            error = self._convert_to_application_error(error)
        
        # エラーコンテキストを作成
        error_context = error.to_error_context()
        
        # エラー履歴に追加
        self.error_history.append(error_context)
        
        # ログ出力
        self._log_error(error_context)
        
        # 回復を試行
        if attempt_recovery:
            recovery_success = self._attempt_recovery(error, context)
            error_context.context_data['recovery_attempted'] = True
            error_context.context_data['recovery_success'] = recovery_success
        
        return error_context
    
    def _convert_to_application_error(self, error: Exception) -> BaseApplicationError:
        """標準例外をBaseApplicationErrorに変換"""
        error_type = type(error).__name__
        
        # 既知の例外タイプをマッピング
        if isinstance(error, (ConnectionError, TimeoutError)):
            return NetworkError(str(error), cause=error)
        elif isinstance(error, FileNotFoundError):
            return FileNotFoundError(str(error), cause=error)
        elif isinstance(error, PermissionError):
            return FilePermissionError("", "アクセス", cause=error)
        elif isinstance(error, UnicodeDecodeError):
            return EncodingError(str(error), cause=error)
        elif isinstance(error, MemoryError):
            return MemoryError(str(error), cause=error)
        else:
            return BaseApplicationError(
                str(error),
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.UNKNOWN,
                cause=error
            )
    
    def _attempt_recovery(self, error: BaseApplicationError, context: Dict[str, Any]) -> bool:
        """エラー回復を試行"""
        strategies = self.recovery_strategies.get(error.category, [])
        
        for strategy in strategies:
            self.logger.info(f"Attempting recovery strategy: {strategy.name}")
            
            if strategy.execute(error, context):
                self.logger.info(f"Recovery successful with strategy: {strategy.name}")
                return True
            else:
                self.logger.warning(f"Recovery failed with strategy: {strategy.name}")
        
        return False
    
    def _log_error(self, error_context: ErrorContext):
        """エラーをログ出力"""
        log_level = {
            ErrorSeverity.CRITICAL: logging.CRITICAL,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.INFO: logging.INFO
        }.get(error_context.severity, logging.ERROR)
        
        log_message = f"[{error_context.category.value.upper()}] {error_context.user_message}"
        
        self.logger.log(log_level, log_message, extra={
            'error_context': error_context,
            'technical_message': error_context.technical_message,
            'recovery_suggestions': error_context.recovery_suggestions
        })
        
        # ファイルログ出力
        if self.log_file:
            self._write_error_to_file(error_context)
    
    def _write_error_to_file(self, error_context: ErrorContext):
        """エラーをファイルに出力"""
        try:
            log_entry = {
                'timestamp': error_context.timestamp.isoformat(),
                'severity': error_context.severity.value,
                'category': error_context.category.value,
                'operation': error_context.operation,
                'user_message': error_context.user_message,
                'technical_message': error_context.technical_message,
                'recovery_suggestions': error_context.recovery_suggestions,
                'context_data': error_context.context_data,
                'stack_trace': error_context.stack_trace
            }
            
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False, default=str) + '\n')
                
        except Exception as e:
            self.logger.error(f"Failed to write error to file: {e}")
    
    # 回復戦略の実装
    def _retry_with_exponential_backoff(self, error: BaseApplicationError, context: Dict[str, Any]) -> bool:
        """指数バックオフでリトライ"""
        import time
        
        retry_count = context.get('retry_count', 0)
        max_retries = context.get('max_retries', 3)
        
        if retry_count >= max_retries:
            return False
        
        delay = (2 ** retry_count) * 1.0  # 指数バックオフ
        time.sleep(delay)
        
        context['retry_count'] = retry_count + 1
        return True
    
    def _use_cached_data(self, error: BaseApplicationError, context: Dict[str, Any]) -> bool:
        """キャッシュデータを使用"""
        cache_file = context.get('cache_file')
        if cache_file and os.path.exists(cache_file):
            self.logger.info("Using cached data as fallback")
            context['use_cache'] = True
            return True
        return False
    
    def _create_missing_directory(self, error: BaseApplicationError, context: Dict[str, Any]) -> bool:
        """不足ディレクトリを作成"""
        file_path = error.context_data.get('file_path', '')
        if file_path:
            try:
                directory = os.path.dirname(file_path)
                if directory:
                    os.makedirs(directory, exist_ok=True)
                    return True
            except Exception as e:
                self.logger.error(f"Failed to create directory: {e}")
        return False
    
    def _use_alternative_file_path(self, error: BaseApplicationError, context: Dict[str, Any]) -> bool:
        """代替ファイルパスを使用"""
        alternative_paths = context.get('alternative_paths', [])
        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                context['file_path'] = alt_path
                return True
        return False
    
    def _force_garbage_collection(self, error: BaseApplicationError, context: Dict[str, Any]) -> bool:
        """ガベージコレクションを強制実行"""
        import gc
        collected = gc.collect()
        self.logger.info(f"Garbage collection freed {collected} objects")
        return collected > 0
    
    def _try_alternative_encoding(self, error: BaseApplicationError, context: Dict[str, Any]) -> bool:
        """代替エンコーディングを試行"""
        alternative_encodings = ['utf-8', 'shift_jis', 'cp932', 'iso-8859-1']
        current_encoding = error.context_data.get('encoding', '')
        
        for encoding in alternative_encodings:
            if encoding != current_encoding:
                context['alternative_encoding'] = encoding
                return True
        return False
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """エラー統計を取得"""
        if not self.error_history:
            return {'total_errors': 0}
        
        # カテゴリ別統計
        category_counts = {}
        severity_counts = {}
        
        for error_context in self.error_history:
            category = error_context.category.value
            severity = error_context.severity.value
            
            category_counts[category] = category_counts.get(category, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            'total_errors': len(self.error_history),
            'category_distribution': category_counts,
            'severity_distribution': severity_counts,
            'recent_errors': [
                {
                    'timestamp': ec.timestamp.isoformat(),
                    'category': ec.category.value,
                    'severity': ec.severity.value,
                    'message': ec.user_message
                }
                for ec in self.error_history[-10:]  # 最新10件
            ]
        }
    
    def clear_error_history(self):
        """エラー履歴をクリア"""
        self.error_history.clear()
        self.logger.info("Error history cleared")


# グローバルエラーハンドラーインスタンス
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """グローバルエラーハンドラーを取得"""
    global _global_error_handler
    if _global_error_handler is None:
        # デフォルトログファイルパス
        log_dir = Path.home() / '.aws-ssm-calendar' / 'logs'
        log_file = log_dir / 'errors.jsonl'
        _global_error_handler = ErrorHandler(str(log_file))
    return _global_error_handler


def handle_error(
    error: Union[BaseApplicationError, Exception],
    context: Optional[Dict[str, Any]] = None,
    attempt_recovery: bool = True
) -> ErrorContext:
    """グローバルエラーハンドラーでエラーを処理"""
    return get_error_handler().handle_error(error, context, attempt_recovery)


def with_error_handling(
    operation_name: str = "",
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    attempt_recovery: bool = True
):
    """エラーハンドリングデコレータ"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except BaseApplicationError as e:
                if not e.operation:
                    e.operation = operation_name or func.__name__
                handle_error(e, attempt_recovery=attempt_recovery)
                raise
            except Exception as e:
                app_error = BaseApplicationError(
                    str(e),
                    category=category,
                    operation=operation_name or func.__name__,
                    cause=e
                )
                handle_error(app_error, attempt_recovery=attempt_recovery)
                raise app_error
        return wrapper
    return decorator