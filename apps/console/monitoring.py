"""
System monitoring module for CommuMap Admin Console.

Provides real-time system health monitoring including database,
cache, disk space, and application metrics.
"""
import os
import logging
from typing import Dict, Any, List
from django.db import connections, DatabaseError
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.db.models import Count
from apps.core.models import User, AuditLog
from apps.services.models import Service
from .models import SystemMetrics

# Try to import psutil, provide fallback if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None


logger = logging.getLogger(__name__)


class SystemMonitor:
    """
    Real-time system health monitoring class.
    
    Provides methods to check various system components and
    record metrics for monitoring dashboards.
    """
    
    @staticmethod
    def check_database_health() -> Dict[str, Any]:
        """Check database health (alias for get_database_health)."""
        return SystemMonitor.get_database_health()
    
    @staticmethod
    def check_cache_health() -> Dict[str, Any]:
        """Check cache health (alias for get_cache_health)."""
        return SystemMonitor.get_cache_health()
    
    @staticmethod
    def check_disk_usage() -> Dict[str, Any]:
        """Check disk usage (alias for get_disk_space)."""
        return SystemMonitor.get_disk_space()
    
    @staticmethod
    def check_memory_usage() -> Dict[str, Any]:
        """Check memory usage (alias for get_memory_usage)."""
        return SystemMonitor.get_memory_usage()
    
    @staticmethod
    def get_database_health() -> Dict[str, Any]:
        """
        Check database connection and performance metrics.
        
        Returns:
            dict: Database health information
        """
        try:
            # Test database connection
            db_conn = connections['default']
            
            with db_conn.cursor() as cursor:
                # Test query execution time
                start_time = timezone.now()
                cursor.execute("SELECT 1")
                end_time = timezone.now()
                query_time = (end_time - start_time).total_seconds() * 1000
            
            # Get connection pool info (simplified for SQLite)
            pool_info = {
                'active_connections': 1,
                'total_connections': 1,
                'max_connections': 100
            }
            
            # Check for slow queries (placeholder)
            slow_queries = 0
            
            health_status = {
                'status': 'healthy',
                'connection_test': 'passed',
                'query_response_time_ms': round(query_time, 2),
                'connection_pool': pool_info,
                'slow_queries_count': slow_queries,
                'database_size_mb': SystemMonitor._get_database_size(),
                'last_backup': SystemMonitor._get_last_backup_time(),
                'health_score': SystemMonitor._calculate_db_health_score(query_time)
            }
            
            # Record metric
            SystemMonitor._record_metric(
                'database_response_time',
                query_time,
                'ms',
                'performance'
            )
            
            return health_status
            
        except DatabaseError as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'connection_test': 'failed',
                'error': str(e),
                'health_score': 0
            }
        except Exception as e:
            logger.error(f"Unexpected error during database health check: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'health_score': 0
            }
    
    @staticmethod
    def get_cache_health() -> Dict[str, Any]:
        """
        Check cache system health and performance.
        
        Returns:
            dict: Cache health information
        """
        try:
            # Test cache operations
            test_key = 'health_check_test'
            test_value = 'test_data'
            
            start_time = timezone.now()
            cache.set(test_key, test_value, 30)
            cached_value = cache.get(test_key)
            end_time = timezone.now()
            
            cache_time = (end_time - start_time).total_seconds() * 1000
            
            # Cleanup test key
            cache.delete(test_key)
            
            cache_working = cached_value == test_value
            
            # Get cache statistics (placeholder for Redis)
            cache_stats = {
                'hit_rate': 85.5,  # Placeholder
                'memory_usage_mb': 128,  # Placeholder
                'total_keys': 1500,  # Placeholder
                'expired_keys': 45  # Placeholder
            }
            
            health_status = {
                'status': 'healthy' if cache_working else 'unhealthy',
                'response_time_ms': round(cache_time, 2),
                'cache_test': 'passed' if cache_working else 'failed',
                'statistics': cache_stats,
                'health_score': 95 if cache_working else 0
            }
            
            # Record metric
            SystemMonitor._record_metric(
                'cache_response_time',
                cache_time,
                'ms',
                'performance'
            )
            
            return health_status
            
        except Exception as e:
            logger.error(f"Cache health check failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'health_score': 0
            }
    
    @staticmethod
    def get_disk_space() -> Dict[str, Any]:
        """
        Check available disk space and storage metrics.
        
        Returns:
            dict: Disk space information
        """
        try:
            if not PSUTIL_AVAILABLE:
                return {
                    'status': 'unavailable',
                    'message': 'psutil not available for disk monitoring',
                    'health_score': 95
                }
            
            # Get disk usage for the project directory
            disk_usage = psutil.disk_usage(settings.BASE_DIR)
            
            total_gb = disk_usage.total / (1024**3)
            used_gb = disk_usage.used / (1024**3)
            free_gb = disk_usage.free / (1024**3)
            usage_percent = (disk_usage.used / disk_usage.total) * 100
            
            # Get log file sizes
            log_dir = getattr(settings, 'LOG_DIR', os.path.join(settings.BASE_DIR, 'logs'))
            log_size_mb = SystemMonitor._get_directory_size(log_dir) / (1024**2)
            
            # Get media file sizes
            media_size_mb = SystemMonitor._get_directory_size(settings.MEDIA_ROOT) / (1024**2)
            
            # Determine health status
            if usage_percent > 95:
                status = 'critical'
                health_score = 10
            elif usage_percent > 90:
                status = 'warning'
                health_score = 50
            elif usage_percent > 80:
                status = 'caution'
                health_score = 75
            else:
                status = 'healthy'
                health_score = 95
            
            disk_info = {
                'status': status,
                'total_gb': round(total_gb, 2),
                'used_gb': round(used_gb, 2),
                'free_gb': round(free_gb, 2),
                'usage_percent': round(usage_percent, 1),
                'log_files_mb': round(log_size_mb, 2),
                'media_files_mb': round(media_size_mb, 2),
                'health_score': health_score
            }
            
            # Record metrics
            SystemMonitor._record_metric(
                'disk_usage_percent',
                usage_percent,
                '%',
                'storage'
            )
            
            SystemMonitor._record_metric(
                'disk_free_gb',
                free_gb,
                'GB',
                'storage'
            )
            
            return disk_info
            
        except Exception as e:
            logger.error(f"Disk space check failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'health_score': 0
            }
    
    @staticmethod
    def get_memory_usage() -> Dict[str, Any]:
        """
        Check system memory usage.
        
        Returns:
            dict: Memory usage information
        """
        try:
            if not PSUTIL_AVAILABLE:
                return {
                    'status': 'unavailable',
                    'message': 'psutil not available for memory monitoring',
                    'health_score': 95
                }
            
            memory = psutil.virtual_memory()
            
            total_gb = memory.total / (1024**3)
            used_gb = memory.used / (1024**3)
            available_gb = memory.available / (1024**3)
            usage_percent = memory.percent
            
            # Determine health status
            if usage_percent > 95:
                status = 'critical'
                health_score = 10
            elif usage_percent > 90:
                status = 'warning'
                health_score = 50
            elif usage_percent > 80:
                status = 'caution'
                health_score = 75
            else:
                status = 'healthy'
                health_score = 95
            
            memory_info = {
                'status': status,
                'total_gb': round(total_gb, 2),
                'used_gb': round(used_gb, 2),
                'available_gb': round(available_gb, 2),
                'usage_percent': round(usage_percent, 1),
                'health_score': health_score
            }
            
            # Record metric
            SystemMonitor._record_metric(
                'memory_usage_percent',
                usage_percent,
                '%',
                'performance'
            )
            
            return memory_info
            
        except Exception as e:
            logger.error(f"Memory usage check failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'health_score': 0
            }
    
    @staticmethod
    def get_application_metrics() -> Dict[str, Any]:
        """
        Get application-specific metrics and statistics.
        
        Returns:
            dict: Application metrics
        """
        try:
            # Get user statistics
            total_users = User.objects.count()
            active_users = User.objects.filter(is_active=True).count()
            verified_users = User.objects.filter(is_verified=True).count()
            
            # Get user counts by role
            user_roles = User.objects.values('role').annotate(count=Count('role'))
            role_distribution = {role['role']: role['count'] for role in user_roles}
            
            # Get service statistics
            total_services = Service.objects.count()
            active_services = Service.objects.filter(is_active=True).count()
            verified_services = Service.objects.filter(is_verified=True).count()
            
            # Get recent activity (last 24 hours)
            yesterday = timezone.now() - timezone.timedelta(days=1)
            recent_registrations = User.objects.filter(created_at__gte=yesterday).count()
            recent_logins = AuditLog.objects.filter(
                action='user_login',
                created_at__gte=yesterday
            ).count()
            
            # Calculate error rate (placeholder)
            error_rate = 0.02  # 2% error rate
            
            # Calculate overall health score
            health_score = SystemMonitor._calculate_app_health_score(
                active_users / max(total_users, 1),
                verified_services / max(total_services, 1),
                error_rate
            )
            
            app_metrics = {
                'users': {
                    'total': total_users,
                    'active': active_users,
                    'verified': verified_users,
                    'recent_registrations': recent_registrations,
                    'role_distribution': role_distribution
                },
                'services': {
                    'total': total_services,
                    'active': active_services,
                    'verified': verified_services
                },
                'activity': {
                    'recent_logins': recent_logins,
                    'error_rate_percent': round(error_rate * 100, 2)
                },
                'health_score': health_score
            }
            
            # Record metrics
            SystemMonitor._record_metric('total_users', total_users, 'count', 'usage')
            SystemMonitor._record_metric('active_users', active_users, 'count', 'usage')
            SystemMonitor._record_metric('total_services', total_services, 'count', 'usage')
            SystemMonitor._record_metric('error_rate', error_rate * 100, '%', 'application')
            
            return app_metrics
            
        except Exception as e:
            logger.error(f"Application metrics check failed: {str(e)}")
            return {
                'error': str(e),
                'health_score': 0
            }
    
    @staticmethod
    def get_system_overview() -> Dict[str, Any]:
        """
        Get comprehensive system overview combining all health checks.
        
        Returns:
            dict: Complete system health overview
        """
        try:
            database_health = SystemMonitor.get_database_health()
            cache_health = SystemMonitor.get_cache_health()
            disk_health = SystemMonitor.get_disk_space()
            memory_health = SystemMonitor.get_memory_usage()
            app_metrics = SystemMonitor.get_application_metrics()
            
            # Calculate overall system health
            health_scores = [
                database_health.get('health_score', 0),
                cache_health.get('health_score', 0),
                disk_health.get('health_score', 0),
                memory_health.get('health_score', 0),
                app_metrics.get('health_score', 0)
            ]
            
            overall_score = sum(health_scores) / len(health_scores)
            
            if overall_score >= 90:
                overall_status = 'excellent'
                status_color = 'success'
            elif overall_score >= 75:
                overall_status = 'good'
                status_color = 'info'
            elif overall_score >= 50:
                overall_status = 'warning'
                status_color = 'warning'
            else:
                overall_status = 'critical'
                status_color = 'error'
            
            overview = {
                'overall_status': overall_status,
                'overall_score': round(overall_score, 1),
                'status_color': status_color,
                'timestamp': timezone.now().isoformat(),
                'components': {
                    'database': database_health,
                    'cache': cache_health,
                    'disk': disk_health,
                    'memory': memory_health,
                    'application': app_metrics
                }
            }
            
            # Record overall health metric
            SystemMonitor._record_metric(
                'system_health_score',
                overall_score,
                'score',
                'performance'
            )
            
            return overview
            
        except Exception as e:
            logger.error(f"System overview check failed: {str(e)}")
            return {
                'overall_status': 'error',
                'overall_score': 0,
                'status_color': 'error',
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }
    
    @staticmethod
    def get_recent_metrics(hours: int = 24) -> Dict[str, List[Dict]]:
        """
        Get recent system metrics for charts and trends.
        
        Args:
            hours: Number of hours to look back
        
        Returns:
            dict: Recent metrics grouped by category
        """
        try:
            since = timezone.now() - timezone.timedelta(hours=hours)
            
            metrics = SystemMetrics.objects.filter(
                recorded_at__gte=since
            ).order_by('recorded_at')
            
            # Group metrics by category and name
            grouped_metrics = {}
            
            for metric in metrics:
                category = metric.metric_category
                name = metric.metric_name
                
                if category not in grouped_metrics:
                    grouped_metrics[category] = {}
                
                if name not in grouped_metrics[category]:
                    grouped_metrics[category][name] = []
                
                grouped_metrics[category][name].append({
                    'timestamp': metric.recorded_at.isoformat(),
                    'value': metric.metric_value,
                    'unit': metric.metric_unit
                })
            
            return grouped_metrics
            
        except Exception as e:
            logger.error(f"Failed to get recent metrics: {str(e)}")
            return {}
    
    @staticmethod
    def _record_metric(name: str, value: float, unit: str, category: str):
        """Record a metric in the database."""
        try:
            SystemMetrics.objects.create(
                metric_name=name,
                metric_value=value,
                metric_unit=unit,
                metric_category=category
            )
        except Exception as e:
            logger.error(f"Failed to record metric {name}: {str(e)}")
    
    @staticmethod
    def _get_database_size() -> float:
        """Get database size in MB."""
        try:
            db_path = settings.DATABASES['default']['NAME']
            if os.path.exists(db_path):
                return os.path.getsize(db_path) / (1024**2)
            return 0
        except:
            return 0
    
    @staticmethod
    def _get_last_backup_time() -> str:
        """Get the timestamp of the last database backup."""
        # Placeholder - would check backup directory
        return "Not available"
    
    @staticmethod
    def _calculate_db_health_score(response_time: float) -> int:
        """Calculate database health score based on response time."""
        if response_time < 10:  # Less than 10ms
            return 95
        elif response_time < 50:  # Less than 50ms
            return 80
        elif response_time < 100:  # Less than 100ms
            return 60
        elif response_time < 500:  # Less than 500ms
            return 40
        else:
            return 20
    
    @staticmethod
    def _calculate_app_health_score(active_user_ratio: float, 
                                   verified_service_ratio: float, 
                                   error_rate: float) -> int:
        """Calculate application health score."""
        score = 100
        
        # Deduct points for low active user ratio
        if active_user_ratio < 0.5:
            score -= 20
        elif active_user_ratio < 0.7:
            score -= 10
        
        # Deduct points for low verified service ratio
        if verified_service_ratio < 0.5:
            score -= 20
        elif verified_service_ratio < 0.7:
            score -= 10
        
        # Deduct points for high error rate
        if error_rate > 0.1:  # 10%
            score -= 30
        elif error_rate > 0.05:  # 5%
            score -= 15
        elif error_rate > 0.02:  # 2%
            score -= 5
        
        return max(0, score)
    
    @staticmethod
    def _get_directory_size(directory: str) -> int:
        """Get total size of directory in bytes."""
        try:
            total_size = 0
            if os.path.exists(directory):
                for dirpath, dirnames, filenames in os.walk(directory):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        if os.path.exists(filepath):
                            total_size += os.path.getsize(filepath)
            return total_size
        except Exception:
            return 0 