"""Japanese holidays management module.

要件1の実装: 日本祝日データ取得・管理
- 一次ソースからの取得（内閣府公式CSV）
- 文字エンコーディング変換（UTF-8）
- 当年以降フィルタリング
- キャッシュ管理（30日間有効期限）
- データインテグリティ保証

パフォーマンス最適化機能:
- 効率的なデータ構造（メモリ最適化）
- 遅延読み込み（Lazy Loading）
- メモリ使用量監視と制限
"""

import csv
import requests
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, NamedTuple, Any
import os
from pathlib import Path
import chardet
import logging
import sys
import gc
from functools import lru_cache
from dataclasses import dataclass
import tracemalloc
import weakref
import time
import hashlib
import pickle
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Union

# Import new error handling framework
from .error_handler import (
    BaseApplicationError, NetworkError, EncodingError, DataIntegrityError, 
    MemoryError as MemoryLimitError, ErrorCategory, ErrorSeverity,
    with_error_handling, handle_error, ValidationError
)
from .logging_config import log_performance, log_function_call, get_logging_manager
from .security import NetworkSecurityManager, validate_url_input

# Legacy compatibility - keep old exception names
class HolidayDataError(BaseApplicationError):
    """祝日データ関連エラー（レガシー互換性）"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.DATA,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


# 効率的なデータ構造
@dataclass(frozen=True, slots=True)
class Holiday:
    """メモリ効率的な祝日データ構造"""
    date: date
    name: str
    category: str = "national"
    
    def __hash__(self):
        return hash((self.date, self.name))


class MemoryStats(NamedTuple):
    """メモリ使用量統計"""
    current_mb: float
    peak_mb: float
    holiday_count: int
    cache_size_mb: float


class LazyHolidayLoader:
    """遅延読み込み用のホリデーローダー"""
    
    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        self._loaded = False
        self._holidays: Optional[Dict[date, Holiday]] = None
        self._weak_refs = weakref.WeakSet()
    
    def get_holidays(self) -> Dict[date, Holiday]:
        """遅延読み込みで祝日データを取得"""
        if not self._loaded:
            self._load_holidays()
        return self._holidays or {}
    
    def _load_holidays(self):
        """実際の祝日データ読み込み"""
        if self._loaded:
            return
            
        self._holidays = {}
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    next(reader)  # Skip header
                    
                    for row in reader:
                        if len(row) >= 2:
                            try:
                                holiday_date = datetime.strptime(row[0], '%Y/%m/%d').date()
                                holiday_name = row[1]
                                category = row[2] if len(row) > 2 else "national"
                                
                                holiday = Holiday(
                                    date=holiday_date,
                                    name=holiday_name,
                                    category=category
                                )
                                self._holidays[holiday_date] = holiday
                            except ValueError:
                                continue
                                
                self._loaded = True
                
            except Exception as e:
                logging.getLogger(__name__).error(f"遅延読み込み失敗: {e}")
                self._holidays = {}
                self._loaded = True
    
    def clear_cache(self):
        """メモリキャッシュをクリア"""
        self._holidays = None
        self._loaded = False
        gc.collect()


class CacheStats(NamedTuple):
    """キャッシュ統計情報"""
    l1_hits: int
    l1_misses: int
    l2_hits: int
    l2_misses: int
    l3_hits: int
    l3_misses: int
    total_size_mb: float
    invalidations: int


class MultiLayerCache:
    """多層キャッシュシステム
    
    L1: メモリキャッシュ（最高速）
    L2: ファイルキャッシュ（中速）
    L3: HTTPキャッシュ（低速）
    """
    
    def __init__(self, cache_dir: str, max_memory_mb: float = 10.0):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_memory_mb = max_memory_mb
        
        # L1: メモリキャッシュ
        self._l1_cache: Dict[str, Tuple[Any, float]] = {}  # key -> (data, timestamp)
        self._l1_lock = threading.RLock()
        
        # L2: ファイルキャッシュ
        self._l2_cache_dir = self.cache_dir / 'l2'
        self._l2_cache_dir.mkdir(exist_ok=True)
        
        # L3: HTTPキャッシュ
        self._l3_cache_dir = self.cache_dir / 'l3'
        self._l3_cache_dir.mkdir(exist_ok=True)
        
        # 統計情報
        self._stats = {
            'l1_hits': 0, 'l1_misses': 0,
            'l2_hits': 0, 'l2_misses': 0,
            'l3_hits': 0, 'l3_misses': 0,
            'invalidations': 0
        }
        
        # キャッシュ有効期限（秒）
        self.l1_ttl = 300  # 5分
        self.l2_ttl = 1800  # 30分
        self.l3_ttl = 86400 * 30  # 30日
        
        self.logger = logging.getLogger(__name__)
    
    def _generate_cache_key(self, data: Union[str, bytes, Dict]) -> str:
        """キャッシュキー生成"""
        if isinstance(data, str):
            content = data.encode('utf-8')
        elif isinstance(data, bytes):
            content = data
        else:
            content = str(data).encode('utf-8')
        
        return hashlib.sha256(content).hexdigest()[:16]
    
    def get(self, key: str) -> Optional[Any]:
        """多層キャッシュからデータ取得"""
        current_time = time.time()
        
        # L1: メモリキャッシュ
        with self._l1_lock:
            if key in self._l1_cache:
                data, timestamp = self._l1_cache[key]
                if current_time - timestamp < self.l1_ttl:
                    self._stats['l1_hits'] += 1
                    return data
                else:
                    # 期限切れ
                    del self._l1_cache[key]
        
        self._stats['l1_misses'] += 1
        
        # L2: ファイルキャッシュ
        l2_file = self._l2_cache_dir / f"{key}.pkl"
        if l2_file.exists():
            try:
                stat = l2_file.stat()
                if current_time - stat.st_mtime < self.l2_ttl:
                    with open(l2_file, 'rb') as f:
                        data = pickle.load(f)
                    
                    # L1にプロモート
                    self._promote_to_l1(key, data)
                    self._stats['l2_hits'] += 1
                    return data
                else:
                    # 期限切れファイル削除
                    l2_file.unlink()
            except Exception as e:
                self.logger.warning(f"L2キャッシュ読み込み失敗: {e}")
        
        self._stats['l2_misses'] += 1
        
        # L3: HTTPキャッシュ（祝日データ用）
        l3_file = self._l3_cache_dir / f"{key}.csv"
        if l3_file.exists():
            try:
                stat = l3_file.stat()
                if current_time - stat.st_mtime < self.l3_ttl:
                    with open(l3_file, 'r', encoding='utf-8') as f:
                        data = f.read()
                    
                    # L2とL1にプロモート
                    self._promote_to_l2(key, data)
                    self._promote_to_l1(key, data)
                    self._stats['l3_hits'] += 1
                    return data
                else:
                    # 期限切れファイル削除
                    l3_file.unlink()
            except Exception as e:
                self.logger.warning(f"L3キャッシュ読み込み失敗: {e}")
        
        self._stats['l3_misses'] += 1
        return None
    
    def put(self, key: str, data: Any, level: str = 'all'):
        """多層キャッシュにデータ保存"""
        if level in ['all', 'l1']:
            self._promote_to_l1(key, data)
        
        if level in ['all', 'l2']:
            self._promote_to_l2(key, data)
        
        if level in ['all', 'l3']:
            self._promote_to_l3(key, data)
    
    def _promote_to_l1(self, key: str, data: Any):
        """L1キャッシュにプロモート"""
        with self._l1_lock:
            # メモリ制限チェック
            if self._get_l1_size_mb() > self.max_memory_mb:
                self._evict_l1_lru()
            
            self._l1_cache[key] = (data, time.time())
    
    def _promote_to_l2(self, key: str, data: Any):
        """L2キャッシュにプロモート"""
        try:
            l2_file = self._l2_cache_dir / f"{key}.pkl"
            with open(l2_file, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            self.logger.warning(f"L2キャッシュ保存失敗: {e}")
    
    def _promote_to_l3(self, key: str, data: Any):
        """L3キャッシュにプロモート"""
        try:
            l3_file = self._l3_cache_dir / f"{key}.csv"
            if isinstance(data, str):
                with open(l3_file, 'w', encoding='utf-8') as f:
                    f.write(data)
            else:
                # バイナリデータの場合
                with open(l3_file, 'wb') as f:
                    f.write(data if isinstance(data, bytes) else str(data).encode('utf-8'))
        except Exception as e:
            self.logger.warning(f"L3キャッシュ保存失敗: {e}")
    
    def _get_l1_size_mb(self) -> float:
        """L1キャッシュサイズ取得（MB）"""
        total_size = 0
        for data, _ in self._l1_cache.values():
            total_size += sys.getsizeof(data)
        return total_size / 1024 / 1024
    
    def _evict_l1_lru(self):
        """L1キャッシュのLRU削除"""
        if not self._l1_cache:
            return
        
        # 最も古いエントリを削除
        oldest_key = min(self._l1_cache.keys(), 
                        key=lambda k: self._l1_cache[k][1])
        del self._l1_cache[oldest_key]
    
    def invalidate(self, key: str):
        """キャッシュ無効化"""
        # L1から削除
        with self._l1_lock:
            if key in self._l1_cache:
                del self._l1_cache[key]
        
        # L2から削除
        l2_file = self._l2_cache_dir / f"{key}.pkl"
        if l2_file.exists():
            l2_file.unlink()
        
        # L3から削除
        l3_file = self._l3_cache_dir / f"{key}.csv"
        if l3_file.exists():
            l3_file.unlink()
        
        self._stats['invalidations'] += 1
    
    def clear_all(self):
        """全キャッシュクリア"""
        # L1クリア
        with self._l1_lock:
            self._l1_cache.clear()
        
        # L2クリア
        for file in self._l2_cache_dir.glob("*.pkl"):
            file.unlink()
        
        # L3クリア
        for file in self._l3_cache_dir.glob("*.csv"):
            file.unlink()
        
        self._stats['invalidations'] += 1
    
    def get_stats(self) -> CacheStats:
        """キャッシュ統計取得"""
        total_size_mb = self._get_l1_size_mb()
        
        # L2サイズ
        for file in self._l2_cache_dir.glob("*.pkl"):
            total_size_mb += file.stat().st_size / 1024 / 1024
        
        # L3サイズ
        for file in self._l3_cache_dir.glob("*.csv"):
            total_size_mb += file.stat().st_size / 1024 / 1024
        
        return CacheStats(
            l1_hits=self._stats['l1_hits'],
            l1_misses=self._stats['l1_misses'],
            l2_hits=self._stats['l2_hits'],
            l2_misses=self._stats['l2_misses'],
            l3_hits=self._stats['l3_hits'],
            l3_misses=self._stats['l3_misses'],
            total_size_mb=total_size_mb,
            invalidations=self._stats['invalidations']
        )


class MemoryMonitor:
    """メモリ使用量監視クラス"""
    
    def __init__(self, memory_limit_mb: float = 50.0):
        """
        Args:
            memory_limit_mb: メモリ使用量制限（MB）
        """
        self.memory_limit_mb = memory_limit_mb
        self.peak_memory_mb = 0.0
        self._start_tracing()
    
    def _start_tracing(self):
        """メモリトレース開始"""
        if not tracemalloc.is_tracing():
            tracemalloc.start()
    
    def get_current_memory_mb(self) -> float:
        """現在のメモリ使用量を取得（MB）"""
        if tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            current_mb = current / 1024 / 1024
            peak_mb = peak / 1024 / 1024
            
            self.peak_memory_mb = max(self.peak_memory_mb, peak_mb)
            return current_mb
        else:
            # フォールバック: sys.getsizeof を使用
            return sys.getsizeof(gc.get_objects()) / 1024 / 1024
    
    def check_memory_limit(self):
        """メモリ制限チェック"""
        current_mb = self.get_current_memory_mb()
        if current_mb > self.memory_limit_mb:
            raise MemoryLimitError(
                f"メモリ使用量が制限を超過: {current_mb:.2f}MB > {self.memory_limit_mb}MB"
            )
    
    def get_memory_stats(self, holiday_count: int = 0, cache_size_mb: float = 0.0) -> MemoryStats:
        """メモリ統計を取得"""
        current_mb = self.get_current_memory_mb()
        return MemoryStats(
            current_mb=current_mb,
            peak_mb=self.peak_memory_mb,
            holiday_count=holiday_count,
            cache_size_mb=cache_size_mb
        )
    
    def optimize_memory(self):
        """メモリ最適化実行"""
        # ガベージコレクション実行
        collected = gc.collect()
        
        # メモリ統計更新
        current_mb = self.get_current_memory_mb()
        
        return {
            'collected_objects': collected,
            'current_memory_mb': current_mb,
            'peak_memory_mb': self.peak_memory_mb
        }


class JapaneseHolidays:
    """Japanese holidays management class with performance optimizations."""
    
    # 内閣府の祝日CSVファイルURL
    CABINET_OFFICE_URL = "https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv"
    
    def __init__(self, cache_file: Optional[str] = None, memory_limit_mb: float = 50.0, 
                 lazy_loading: bool = True, enable_multilayer_cache: bool = True):
        """Initialize Japanese holidays manager.
        
        要件1実装: 日本祝日データの取得・管理・キャッシュ
        パフォーマンス最適化: メモリ管理、遅延読み込み、多層キャッシュ
        
        Args:
            cache_file: Path to cache file for holidays data
            memory_limit_mb: Memory usage limit in MB
            lazy_loading: Enable lazy loading of holiday data
            enable_multilayer_cache: Enable multi-layer caching system
        """
        self.cache_file = cache_file or self._get_default_cache_path()
        self.current_year = datetime.now().year
        self.logger = logging.getLogger(__name__)
        
        # Initialize logging and monitoring
        self.logging_manager = get_logging_manager()
        
        # パフォーマンス最適化機能
        self.memory_monitor = MemoryMonitor(memory_limit_mb)
        self.lazy_loading = lazy_loading
        
        # 多層キャッシュシステム
        self.enable_multilayer_cache = enable_multilayer_cache
        if enable_multilayer_cache:
            cache_dir = Path(self.cache_file).parent
            self.multilayer_cache = MultiLayerCache(
                cache_dir=str(cache_dir),
                max_memory_mb=memory_limit_mb * 0.3  # メモリの30%をキャッシュに割り当て
            )
        else:
            self.multilayer_cache = None
        
        if lazy_loading:
            # 遅延読み込み用ローダー
            self.lazy_loader = LazyHolidayLoader(self.cache_file)
            self.holidays: Optional[Dict[date, Holiday]] = None
        else:
            # 従来の即座読み込み（後方互換性）
            self.holidays: Dict[date, Holiday] = {}
            self.lazy_loader = None
            self._load_holidays()
        
        # LRUキャッシュ用の年別データ
        self._year_cache_size = 10  # 最大10年分をキャッシュ
        
        # キャッシュ統計監視
        self._cache_access_count = 0
        self._last_cache_cleanup = time.time()
    
    def _get_default_cache_path(self) -> str:
        """Get default cache file path.
        
        Returns:
            Default cache file path
        """
        cache_dir = Path.home() / '.aws-ssm-calendar' / 'cache'
        cache_dir.mkdir(parents=True, exist_ok=True)
        return str(cache_dir / 'japanese_holidays.csv')
    
    @with_error_handling(operation_name="load_holidays", category=ErrorCategory.DATA)
    @log_performance("japanese_holidays_load")
    def _load_holidays(self):
        """祝日データの読み込み.
        
        要件1の統合フロー実装
        パフォーマンス最適化: メモリ監視付き読み込み
        """
        with self.logging_manager.monitor_operation("load_holidays"):
            try:
                # メモリ使用量チェック
                self.memory_monitor.check_memory_limit()
                
                # キャッシュ有効期限確認
                if self.is_cache_valid():
                    # キャッシュから読み込み
                    if self.load_from_cache():
                        # キャッシュから読み込んだ後も当年以降フィルタリングを適用
                        self.holidays = self.filter_current_year_onwards(self.holidays)
                        
                        # メモリ使用量再チェック
                        self.memory_monitor.check_memory_limit()
                        return
                
                # キャッシュが無効または読み込み失敗時は新規取得
                self._download_and_cache()
                
            except MemoryLimitError as e:
                handle_error(e, {"operation": "load_holidays", "memory_limit": self.memory_monitor.memory_limit_mb})
                # メモリ最適化を試行
                self.memory_monitor.optimize_memory()
                raise e
            except (NetworkError, EncodingError, DataIntegrityError) as e:
                # 要件1: 公式データ取得失敗時は処理停止
                handle_error(e, {"operation": "load_holidays", "cache_file": self.cache_file})
                raise e
    
    def load_from_cache(self) -> bool:
        """キャッシュからの読み込み.
        
        要件1: キャッシュ管理
        パフォーマンス最適化: 効率的なデータ構造使用
        
        Returns:
            True if successfully loaded from cache
        """
        try:
            if self.holidays is None:
                self.holidays = {}
            else:
                self.holidays.clear()
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                
                for row in reader:
                    if len(row) >= 2:
                        try:
                            holiday_date = datetime.strptime(row[0], '%Y/%m/%d').date()
                            holiday_name = row[1]
                            category = row[2] if len(row) > 2 else "national"
                            
                            # 効率的なHolidayオブジェクト作成
                            holiday = Holiday(
                                date=holiday_date,
                                name=holiday_name,
                                category=category
                            )
                            self.holidays[holiday_date] = holiday
                            
                            # 定期的なメモリチェック（100件ごと）
                            if len(self.holidays) % 100 == 0:
                                self.memory_monitor.check_memory_limit()
                                
                        except ValueError as e:
                            self.logger.warning(f"キャッシュ行の解析をスキップ: {e}")
                            continue
            
            self.logger.info(f"キャッシュから読み込み完了: {len(self.holidays)} 件")
            
            # 最終メモリチェック
            stats = self.memory_monitor.get_memory_stats(
                holiday_count=len(self.holidays),
                cache_size_mb=os.path.getsize(self.cache_file) / 1024 / 1024 if os.path.exists(self.cache_file) else 0
            )
            self.logger.info(f"メモリ使用量: {stats.current_mb:.2f}MB (ピーク: {stats.peak_mb:.2f}MB)")
            
            return True
            
        except MemoryLimitError as e:
            self.logger.error(f"メモリ制限によりキャッシュ読み込み中断: {e}")
            return False
        except Exception as e:
            self.logger.error(f"キャッシュ読み込み失敗: {e}")
            return False
    
    def is_cache_valid(self) -> bool:
        """キャッシュ有効期限確認.
        
        要件1: 30日間の有効期限
        
        Returns:
            True if cache is valid (within 30 days)
        """
        if not os.path.exists(self.cache_file):
            return False
        
        try:
            cache_age = datetime.now().timestamp() - os.path.getmtime(self.cache_file)
            is_valid = cache_age <= 30 * 24 * 3600  # 30 days in seconds
            
            if is_valid:
                self.logger.info("キャッシュは有効期限内です")
            else:
                self.logger.info(f"キャッシュが期限切れです（{cache_age / (24 * 3600):.1f}日経過）")
            
            return is_valid
            
        except Exception as e:
            self.logger.error(f"キャッシュ有効期限確認失敗: {e}")
            return False
    
    @with_error_handling(operation_name="fetch_official_data", category=ErrorCategory.NETWORK)
    @log_performance("fetch_official_data")
    def fetch_official_data(self) -> bytes:
        """内閣府公式CSVの取得.
        
        要件1: 一次ソースからの取得
        パフォーマンス最適化: 多層キャッシュ対応
        
        Returns:
            Raw CSV data as bytes
            
        Raises:
            NetworkError: ネットワーク接続エラー
        """
        with self.logging_manager.monitor_operation("fetch_official_data", {"url": self.CABINET_OFFICE_URL}):
            # 多層キャッシュから取得を試行
            if self.multilayer_cache:
                cache_key = self.multilayer_cache._generate_cache_key(self.CABINET_OFFICE_URL)
                cached_data = self.multilayer_cache.get(cache_key)
                
                if cached_data:
                    self.logger.info("多層キャッシュから祝日データを取得")
                    return cached_data.encode('utf-8') if isinstance(cached_data, str) else cached_data
            
            try:
                self.logger.info("内閣府公式CSVから祝日データを取得中...")
                
                # セキュリティ検証: URLの妥当性とHTTPS強制
                validated_url = validate_url_input(self.CABINET_OFFICE_URL, require_https=True)
                
                # セキュアなHTTPリクエスト実行
                response = NetworkSecurityManager.secure_request(
                    validated_url,
                    method='GET',
                    timeout=30
                )
                response.raise_for_status()
                
                # 多層キャッシュに保存
                if self.multilayer_cache:
                    cache_key = self.multilayer_cache._generate_cache_key(self.CABINET_OFFICE_URL)
                    self.multilayer_cache.put(cache_key, response.content, level='all')
                    self.logger.info("祝日データを多層キャッシュに保存")
                
                return response.content
                
            except (requests.exceptions.RequestException, ValidationError) as e:
                error = NetworkError(
                    f"内閣府公式データの取得に失敗: {e}",
                    url=self.CABINET_OFFICE_URL,
                    timeout=30,
                    operation="fetch_official_data"
                )
                handle_error(error, {"url": self.CABINET_OFFICE_URL, "timeout": 30})
                raise error
    
    def detect_encoding(self, raw_data: bytes) -> str:
        """エンコーディング自動検出.
        
        要件1: エンコーディング変換（Shift_JIS → CP932 → UTF-8の順）
        
        Args:
            raw_data: Raw CSV data
            
        Returns:
            Detected encoding name
            
        Raises:
            EncodingError: エンコーディング検出失敗
        """
        # 優先順序での検出
        priority_encodings = ['shift_jis', 'cp932', 'utf-8']
        
        for encoding in priority_encodings:
            try:
                raw_data.decode(encoding)
                self.logger.info(f"エンコーディング検出: {encoding}")
                return encoding
            except UnicodeDecodeError:
                continue
        
        # chardetによる自動検出をフォールバック
        detected = chardet.detect(raw_data)
        if detected['confidence'] > 0.8:
            self.logger.info(f"chardetによる検出: {detected['encoding']} (信頼度: {detected['confidence']})")
            return detected['encoding']
        
        raise EncodingError("文字エンコーディングの検出に失敗")
    
    def convert_to_utf8(self, raw_data: bytes, source_encoding: str) -> str:
        """UTF-8形式への変換.
        
        要件1: 文字エンコーディング変換
        
        Args:
            raw_data: Raw CSV data
            source_encoding: Source encoding
            
        Returns:
            UTF-8 decoded string
            
        Raises:
            EncodingError: 変換失敗
        """
        try:
            content = raw_data.decode(source_encoding)
            self.logger.info(f"{source_encoding} → UTF-8 変換完了")
            return content
        except UnicodeDecodeError as e:
            raise EncodingError(f"UTF-8変換に失敗 ({source_encoding}): {e}")
    
    def filter_current_year_onwards(self, holidays: Dict[date, Holiday]) -> Dict[date, Holiday]:
        """当年以降の祝日データフィルタリング.
        
        要件1: 当年以降フィルタリング
        パフォーマンス最適化: 効率的なフィルタリング
        
        Args:
            holidays: All holidays data
            
        Returns:
            Filtered holidays (current year onwards)
        """
        current_year_start = date(self.current_year, 1, 1)
        
        # メモリ効率的なフィルタリング
        filtered_holidays = {}
        filtered_count = 0
        
        for holiday_date, holiday in holidays.items():
            if holiday_date >= current_year_start:
                filtered_holidays[holiday_date] = holiday
                filtered_count += 1
                
                # 定期的なメモリチェック
                if filtered_count % 50 == 0:
                    self.memory_monitor.check_memory_limit()
        
        self.logger.info(f"当年以降フィルタ: {len(holidays)} → {len(filtered_holidays)} 件")
        
        # フィルタリング後のメモリ最適化
        if len(filtered_holidays) < len(holidays) * 0.5:  # 50%以上削減された場合
            gc.collect()
            
        return filtered_holidays
    
    def validate_data_integrity(self, holidays: Dict[date, Holiday]) -> None:
        """データ整合性の検証.
        
        要件1: データインテグリティ
        パフォーマンス最適化: 効率的な検証
        
        Args:
            holidays: Holiday data to validate
            
        Raises:
            DataIntegrityError: データ整合性エラー
        """
        if not holidays:
            raise DataIntegrityError("祝日データが空です")
        
        # 基本的な整合性チェック
        validation_count = 0
        for holiday_date, holiday in holidays.items():
            if not isinstance(holiday_date, date):
                raise DataIntegrityError(f"不正な日付形式: {holiday_date}")
            
            if not isinstance(holiday, Holiday):
                raise DataIntegrityError(f"不正な祝日オブジェクト: {type(holiday)}")
            
            if not holiday.name or not isinstance(holiday.name, str):
                raise DataIntegrityError(f"不正な祝日名: {holiday.name}")
            
            if holiday_date.year < 1948:  # 祝日法制定年
                raise DataIntegrityError(f"不正な年度: {holiday_date.year}")
            
            # 日付とオブジェクトの整合性チェック
            if holiday.date != holiday_date:
                raise DataIntegrityError(f"日付不整合: キー={holiday_date}, オブジェクト={holiday.date}")
            
            validation_count += 1
            
            # 定期的なメモリチェック（1000件ごと）
            if validation_count % 1000 == 0:
                self.memory_monitor.check_memory_limit()
        
        self.logger.info(f"データ整合性検証完了: {len(holidays)} 件")
    
    def _download_and_cache(self):
        """Download holidays from Cabinet Office and cache them.
        
        要件1の統合実装
        """
        try:
            # 1. 内閣府公式CSVの取得
            raw_data = self.fetch_official_data()
            
            # 2. エンコーディング自動検出
            source_encoding = self.detect_encoding(raw_data)
            
            # 3. UTF-8変換
            content = self.convert_to_utf8(raw_data, source_encoding)
            
            # 4. CSV解析
            all_holidays = self._parse_csv_content(content)
            
            # 5. データ整合性検証
            self.validate_data_integrity(all_holidays)
            
            # 6. 当年以降フィルタリング
            filtered_holidays = self.filter_current_year_onwards(all_holidays)
            
            # 7. メモリに保存
            self.holidays = filtered_holidays
            
            # 8. キャッシュ保存
            self.save_to_cache()
            
            self.logger.info(f"祝日データ取得完了: {len(self.holidays)} 件")
            
        except (NetworkError, EncodingError, DataIntegrityError) as e:
            self.logger.error(f"祝日データ取得失敗: {e}")
            # 要件1: 公式データ取得失敗時は処理停止
            raise e
        except Exception as e:
            self.logger.error(f"予期しないエラー: {e}")
            raise DataIntegrityError(f"祝日データ処理中にエラーが発生: {e}")
    
    def _parse_csv_content(self, content: str) -> Dict[date, Holiday]:
        """CSV内容の解析.
        
        Args:
            content: UTF-8 CSV content
            
        Returns:
            Parsed holidays data with optimized Holiday objects
        """
        holidays = {}
        lines = content.strip().split('\n')
        
        for i, line in enumerate(lines):
            if i == 0:  # Skip header
                continue
            
            parts = line.split(',')
            if len(parts) >= 2:
                try:
                    holiday_date = datetime.strptime(parts[0], '%Y/%m/%d').date()
                    holiday_name = parts[1].strip()
                    category = parts[2].strip() if len(parts) > 2 else "national"
                    
                    # 効率的なHolidayオブジェクト作成
                    holiday = Holiday(
                        date=holiday_date,
                        name=holiday_name,
                        category=category
                    )
                    holidays[holiday_date] = holiday
                    
                    # 定期的なメモリチェック（500件ごと）
                    if len(holidays) % 500 == 0:
                        self.memory_monitor.check_memory_limit()
                        
                except ValueError as e:
                    self.logger.warning(f"行 {i+1} の解析をスキップ: {e}")
                    continue
        
        return holidays
    
    def save_to_cache(self):
        """UTF-8形式でのキャッシュ保存.
        
        要件1: キャッシュ管理
        パフォーマンス最適化: 効率的な保存処理
        """
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            
            # メモリチェック
            self.memory_monitor.check_memory_limit()
            
            with open(self.cache_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['国民の祝日・休日月日', '国民の祝日・休日名称', 'カテゴリ'])
                
                # ソート済みデータの効率的な書き込み
                sorted_holidays = sorted(self.holidays.items())
                for i, (holiday_date, holiday) in enumerate(sorted_holidays):
                    writer.writerow([
                        holiday_date.strftime('%Y/%m/%d'), 
                        holiday.name,
                        holiday.category
                    ])
                    
                    # 定期的なメモリチェック（100件ごと）
                    if i % 100 == 0:
                        self.memory_monitor.check_memory_limit()
            
            # ファイル権限設定（ユーザーのみアクセス可能）
            os.chmod(self.cache_file, 0o600)
            
            # キャッシュサイズ情報
            cache_size_mb = os.path.getsize(self.cache_file) / 1024 / 1024
            self.logger.info(f"キャッシュ保存完了: {self.cache_file} ({cache_size_mb:.2f}MB)")
            
        except MemoryLimitError as e:
            self.logger.error(f"メモリ制限によりキャッシュ保存失敗: {e}")
            raise
        except Exception as e:
            self.logger.error(f"キャッシュ保存失敗: {e}")
            raise
    
    def _use_fallback_data(self):
        """Use fallback holiday data for current year."""
        current_year = datetime.now().year
        
        # Basic holidays that are fixed or calculable
        fallback_holidays = {
            f"{current_year}/1/1": "元日",
            f"{current_year}/2/11": "建国記念の日",
            f"{current_year}/4/29": "昭和の日",
            f"{current_year}/5/3": "憲法記念日",
            f"{current_year}/5/4": "みどりの日",
            f"{current_year}/5/5": "こどもの日",
            f"{current_year}/8/11": "山の日",
            f"{current_year}/11/3": "文化の日",
            f"{current_year}/11/23": "勤労感謝の日",
        }
        
        self.holidays.clear()
        for date_str, name in fallback_holidays.items():
            try:
                holiday_date = datetime.strptime(date_str, '%Y/%m/%d').date()
                self.holidays[holiday_date] = name
            except ValueError:
                continue
        
        print(f"Using fallback data with {len(self.holidays)} holidays")
    
    def _get_holidays(self) -> Dict[date, Holiday]:
        """祝日データを取得（遅延読み込み対応）"""
        # アクセス回数カウント
        self._cache_access_count += 1
        
        # 定期的なキャッシュクリーンアップ
        if self._cache_access_count % 1000 == 0:
            self._periodic_cache_cleanup()
        
        if self.lazy_loading and self.lazy_loader:
            return self.lazy_loader.get_holidays()
        else:
            return self.holidays or {}
    
    @lru_cache(maxsize=1000)
    def is_holiday(self, check_date: date) -> bool:
        """Check if a date is a Japanese holiday.
        
        Args:
            check_date: Date to check
            
        Returns:
            True if the date is a holiday
        """
        holidays = self._get_holidays()
        return check_date in holidays
    
    @lru_cache(maxsize=1000)
    def get_holiday_name(self, check_date: date) -> Optional[str]:
        """Get holiday name for a date.
        
        Args:
            check_date: Date to check
            
        Returns:
            Holiday name if it's a holiday, None otherwise
        """
        holidays = self._get_holidays()
        holiday = holidays.get(check_date)
        return holiday.name if holiday else None
    
    @lru_cache(maxsize=1000)
    def get_holiday(self, check_date: date) -> Optional[Holiday]:
        """Get holiday object for a date.
        
        Args:
            check_date: Date to check
            
        Returns:
            Holiday object if it's a holiday, None otherwise
        """
        holidays = self._get_holidays()
        return holidays.get(check_date)
    
    def get_holidays_in_range(self, start_date: date, end_date: date) -> List[Tuple[date, str]]:
        """Get all holidays in a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of (date, holiday_name) tuples
        """
        holidays = self._get_holidays()
        holidays_in_range = []
        
        for holiday_date, holiday in holidays.items():
            if start_date <= holiday_date <= end_date:
                holidays_in_range.append((holiday_date, holiday.name))
        
        return sorted(holidays_in_range)
    
    def get_holidays_in_range_detailed(self, start_date: date, end_date: date) -> List[Holiday]:
        """Get all holiday objects in a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of Holiday objects
        """
        holidays = self._get_holidays()
        holidays_in_range = []
        
        for holiday_date, holiday in holidays.items():
            if start_date <= holiday_date <= end_date:
                holidays_in_range.append(holiday)
        
        return sorted(holidays_in_range, key=lambda h: h.date)
    
    @lru_cache(maxsize=10)  # 最大10年分をキャッシュ
    def get_holidays_by_year(self, year: int) -> List[Tuple[date, str]]:
        """Get all holidays for a specific year.
        
        Args:
            year: Year to get holidays for
            
        Returns:
            List of (date, holiday_name) tuples
        """
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        return self.get_holidays_in_range(start_date, end_date)
    
    @lru_cache(maxsize=10)  # 最大10年分をキャッシュ
    def get_holidays_by_year_detailed(self, year: int) -> List[Holiday]:
        """Get all holiday objects for a specific year.
        
        Args:
            year: Year to get holidays for
            
        Returns:
            List of Holiday objects
        """
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        return self.get_holidays_in_range_detailed(start_date, end_date)
    
    def refresh_data(self):
        """Force refresh holiday data from Cabinet Office."""
        self._download_and_cache()
    
    @lru_cache(maxsize=100)
    def get_next_holiday(self, from_date: Optional[date] = None) -> Optional[Tuple[date, str]]:
        """Get the next holiday from a given date.
        
        Args:
            from_date: Date to search from (default: today)
            
        Returns:
            (date, holiday_name) tuple of next holiday, or None if not found
        """
        if from_date is None:
            from_date = date.today()
        
        holidays = self._get_holidays()
        future_holidays = [
            (holiday_date, holiday.name)
            for holiday_date, holiday in holidays.items()
            if holiday_date > from_date
        ]
        
        if future_holidays:
            return min(future_holidays, key=lambda x: x[0])
        
        return None
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about loaded holidays.
        
        Returns:
            Dictionary with statistics
        """
        holidays = self._get_holidays()
        if not holidays:
            return {'total': 0, 'years': 0, 'min_year': 0, 'max_year': 0}
        
        years = set(holiday_date.year for holiday_date in holidays.keys())
        
        return {
            'total': len(holidays),
            'years': len(years),
            'min_year': min(years) if years else 0,
            'max_year': max(years) if years else 0
        }
    
    def get_memory_stats(self) -> MemoryStats:
        """Get memory usage statistics.
        
        Returns:
            Memory statistics
        """
        holidays = self._get_holidays()
        cache_size_mb = 0.0
        
        if os.path.exists(self.cache_file):
            cache_size_mb = os.path.getsize(self.cache_file) / 1024 / 1024
        
        return self.memory_monitor.get_memory_stats(
            holiday_count=len(holidays),
            cache_size_mb=cache_size_mb
        )
    
    def optimize_memory(self) -> Dict[str, Any]:
        """Optimize memory usage.
        
        Returns:
            Optimization results
        """
        # LRUキャッシュクリア
        self.is_holiday.cache_clear()
        self.get_holiday_name.cache_clear()
        self.get_holiday.cache_clear()
        self.get_holidays_by_year.cache_clear()
        self.get_holidays_by_year_detailed.cache_clear()
        self.get_next_holiday.cache_clear()
        
        # 遅延読み込みキャッシュクリア
        if self.lazy_loader:
            self.lazy_loader.clear_cache()
        
        # メモリ最適化実行
        optimization_result = self.memory_monitor.optimize_memory()
        
        self.logger.info(f"メモリ最適化完了: {optimization_result}")
        return optimization_result
    
    def clear_cache(self):
        """Clear all caches and force reload on next access."""
        self.optimize_memory()
        
        if self.lazy_loading and self.lazy_loader:
            self.lazy_loader.clear_cache()
        elif self.holidays:
            self.holidays.clear()
    
    def set_memory_limit(self, memory_limit_mb: float):
        """Set memory usage limit.
        
        Args:
            memory_limit_mb: Memory limit in MB
        """
        self.memory_monitor.memory_limit_mb = memory_limit_mb
        
        # 多層キャッシュのメモリ制限も更新
        if self.multilayer_cache:
            self.multilayer_cache.max_memory_mb = memory_limit_mb * 0.3
        
        self.logger.info(f"メモリ制限を設定: {memory_limit_mb}MB")
    
    def invalidate_cache(self, cache_type: str = 'all'):
        """キャッシュ無効化.
        
        Args:
            cache_type: 'all', 'memory', 'file', 'multilayer'のいずれか
        """
        if cache_type in ['all', 'memory']:
            # LRUキャッシュクリア
            self.is_holiday.cache_clear()
            self.get_holiday_name.cache_clear()
            self.get_holiday.cache_clear()
            self.get_holidays_by_year.cache_clear()
            self.get_holidays_by_year_detailed.cache_clear()
            self.get_next_holiday.cache_clear()
            self.logger.info("メモリキャッシュを無効化")
        
        if cache_type in ['all', 'file']:
            # ファイルキャッシュ削除
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                self.logger.info("ファイルキャッシュを無効化")
        
        if cache_type in ['all', 'multilayer'] and self.multilayer_cache:
            # 多層キャッシュクリア
            self.multilayer_cache.clear_all()
            self.logger.info("多層キャッシュを無効化")
        
        # 遅延読み込みキャッシュクリア
        if self.lazy_loader:
            self.lazy_loader.clear_cache()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """キャッシュ統計情報取得.
        
        Returns:
            キャッシュ統計情報
        """
        stats = {
            'memory_stats': self.get_memory_stats(),
            'lru_cache_info': {
                'is_holiday': self.is_holiday.cache_info()._asdict(),
                'get_holiday_name': self.get_holiday_name.cache_info()._asdict(),
                'get_holiday': self.get_holiday.cache_info()._asdict(),
                'get_holidays_by_year': self.get_holidays_by_year.cache_info()._asdict(),
                'get_holidays_by_year_detailed': self.get_holidays_by_year_detailed.cache_info()._asdict(),
                'get_next_holiday': self.get_next_holiday.cache_info()._asdict(),
            },
            'file_cache': {
                'exists': os.path.exists(self.cache_file),
                'size_mb': os.path.getsize(self.cache_file) / 1024 / 1024 if os.path.exists(self.cache_file) else 0,
                'last_modified': datetime.fromtimestamp(os.path.getmtime(self.cache_file)).isoformat() if os.path.exists(self.cache_file) else None
            }
        }
        
        if self.multilayer_cache:
            stats['multilayer_cache'] = self.multilayer_cache.get_stats()._asdict()
        
        return stats
    
    def _periodic_cache_cleanup(self):
        """定期的なキャッシュクリーンアップ"""
        current_time = time.time()
        
        # 1時間ごとにクリーンアップ実行
        if current_time - self._last_cache_cleanup > 3600:
            self.logger.info("定期キャッシュクリーンアップ開始")
            
            # メモリ最適化
            optimization_result = self.optimize_memory()
            
            # 多層キャッシュの統計確認
            if self.multilayer_cache:
                cache_stats = self.multilayer_cache.get_stats()
                
                # ヒット率が低い場合は警告
                total_requests = cache_stats.l1_hits + cache_stats.l1_misses
                if total_requests > 100:
                    hit_rate = cache_stats.l1_hits / total_requests
                    if hit_rate < 0.5:
                        self.logger.warning(f"L1キャッシュヒット率が低下: {hit_rate:.2%}")
            
            self._last_cache_cleanup = current_time
            self.logger.info(f"キャッシュクリーンアップ完了: {optimization_result}")
    
    def warm_up_cache(self, years: List[int] = None):
        """キャッシュウォームアップ.
        
        Args:
            years: ウォームアップ対象年のリスト（デフォルト: 当年から3年分）
        """
        if years is None:
            years = [self.current_year + i for i in range(3)]
        
        self.logger.info(f"キャッシュウォームアップ開始: {years}")
        
        for year in years:
            try:
                # 年別祝日データを事前読み込み
                holidays = self.get_holidays_by_year(year)
                self.logger.info(f"{year}年の祝日データをキャッシュ: {len(holidays)}件")
                
                # メモリ制限チェック
                self.memory_monitor.check_memory_limit()
                
            except Exception as e:
                self.logger.warning(f"{year}年のキャッシュウォームアップ失敗: {e}")
        
        self.logger.info("キャッシュウォームアップ完了")
    
    def enable_cache_monitoring(self, interval_seconds: int = 300):
        """キャッシュ監視を有効化.
        
        Args:
            interval_seconds: 監視間隔（秒）
        """
        def monitor_cache():
            while True:
                try:
                    time.sleep(interval_seconds)
                    
                    # 定期クリーンアップ
                    self._periodic_cache_cleanup()
                    
                    # 統計情報ログ出力
                    stats = self.get_cache_stats()
                    self.logger.info(f"キャッシュ統計: {stats}")
                    
                except Exception as e:
                    self.logger.error(f"キャッシュ監視エラー: {e}")
        
        # バックグラウンドスレッドで監視開始
        monitor_thread = threading.Thread(target=monitor_cache, daemon=True)
        monitor_thread.start()
        self.logger.info(f"キャッシュ監視を開始: {interval_seconds}秒間隔")