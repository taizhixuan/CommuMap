"""
System maintenance operations for CommuMap Admin Console.

Provides system maintenance functionality including database backup,
cache management, log rotation, and feature toggling.
"""
import os
import logging
import shutil
import gzip
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from django.conf import settings
from django.core.management import call_command
from django.core.cache import cache
from django.utils import timezone
from django.db import transaction
from apps.core.models import SystemSettings, AuditLog
from .models import MaintenanceTask


logger = logging.getLogger(__name__)


class MaintenanceOperations:
    """
    System maintenance operations manager.
    
    Handles various maintenance tasks that can be executed by admin users
    including backups, cache management, and system cleanup.
    """
    
    @staticmethod
    def backup_database(initiated_by, backup_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a database backup with timestamp.
        
        Args:
            initiated_by: User who initiated the backup
            backup_name: Optional custom name for the backup
        
        Returns:
            dict: Backup operation result
        """
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"database_backup_{timestamp}"
        
        # Create maintenance task
        task = MaintenanceTask.objects.create(
            task_type='backup',
            title=f"Database Backup: {backup_name}",
            description="Creating database backup with current data",
            initiated_by=initiated_by,
            parameters={'backup_name': backup_name}
        )
        
        try:
            task.mark_started()
            
            # Create backup directory if it doesn't exist
            backup_dir = os.path.join(settings.BASE_DIR, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            # Define backup file path
            backup_filename = f"{backup_name}.sql"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # For SQLite, copy the database file
            if 'sqlite' in settings.DATABASES['default']['ENGINE']:
                source_db = settings.DATABASES['default']['NAME']
                backup_db_path = os.path.join(backup_dir, f"{backup_name}.db")
                
                shutil.copy2(source_db, backup_db_path)
                
                # Create SQL dump as well
                try:
                    with open(backup_path, 'w') as backup_file:
                        call_command('dumpdata', 
                                   stdout=backup_file,
                                   format='json',
                                   indent=2)
                except Exception as e:
                    logger.warning(f"Could not create JSON dump: {str(e)}")
                
                backup_size = os.path.getsize(backup_db_path)
                
            else:
                # For PostgreSQL/MySQL, use pg_dump/mysqldump
                backup_size = MaintenanceOperations._create_sql_dump(backup_path)
            
            # Compress the backup
            compressed_path = f"{backup_path}.gz"
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove uncompressed file
            if os.path.exists(backup_path):
                os.remove(backup_path)
            
            compressed_size = os.path.getsize(compressed_path)
            
            result_data = {
                'backup_name': backup_name,
                'backup_path': compressed_path,
                'original_size_mb': round(backup_size / (1024**2), 2),
                'compressed_size_mb': round(compressed_size / (1024**2), 2),
                'compression_ratio': round((1 - compressed_size / backup_size) * 100, 1) if backup_size > 0 else 0,
                'backup_time': timezone.now().isoformat()
            }
            
            task.mark_completed(result_data)
            
            # Log the operation
            AuditLog.objects.create(
                user=initiated_by,
                action='backup_created',
                description=f"Database backup created: {backup_name}",
                metadata=result_data
            )
            
            return {
                'success': True,
                'message': f"Database backup '{backup_name}' created successfully",
                'data': result_data
            }
            
        except Exception as e:
            error_msg = f"Database backup failed: {str(e)}"
            task.mark_failed(error_msg)
            logger.error(error_msg)
            
            return {
                'success': False,
                'message': error_msg,
                'error': str(e)
            }
    
    @staticmethod
    def clear_cache(initiated_by, cache_types: Optional[list] = None) -> Dict[str, Any]:
        """
        Clear cache systems (Redis, file cache, etc.).
        
        Args:
            initiated_by: User who initiated the cache clear
            cache_types: List of cache types to clear (None = all)
        
        Returns:
            dict: Cache clear operation result
        """
        if not cache_types:
            cache_types = ['default', 'sessions', 'file_cache']
        
        task = MaintenanceTask.objects.create(
            task_type='cache_clear',
            title="Cache Clear Operation",
            description=f"Clearing cache types: {', '.join(cache_types)}",
            initiated_by=initiated_by,
            parameters={'cache_types': cache_types}
        )
        
        try:
            task.mark_started()
            
            cleared_caches = []
            errors = []
            
            # Clear Django cache
            if 'default' in cache_types:
                try:
                    cache.clear()
                    cleared_caches.append('default')
                except Exception as e:
                    errors.append(f"Default cache: {str(e)}")
            
            # Clear session cache
            if 'sessions' in cache_types:
                try:
                    call_command('clearsessions')
                    cleared_caches.append('sessions')
                except Exception as e:
                    errors.append(f"Sessions: {str(e)}")
            
            # Clear file cache
            if 'file_cache' in cache_types:
                try:
                    cache_dir = os.path.join(settings.BASE_DIR, 'cache')
                    if os.path.exists(cache_dir):
                        shutil.rmtree(cache_dir)
                        os.makedirs(cache_dir)
                    cleared_caches.append('file_cache')
                except Exception as e:
                    errors.append(f"File cache: {str(e)}")
            
            result_data = {
                'cleared_caches': cleared_caches,
                'errors': errors,
                'clear_time': timezone.now().isoformat()
            }
            
            if errors:
                task.mark_failed(f"Partial cache clear: {'; '.join(errors)}")
                success = False
                message = f"Cache partially cleared with errors: {'; '.join(errors)}"
            else:
                task.mark_completed(result_data)
                success = True
                message = f"Cache cleared successfully: {', '.join(cleared_caches)}"
            
            # Log the operation
            AuditLog.objects.create(
                user=initiated_by,
                action='cache_cleared',
                description=message,
                metadata=result_data
            )
            
            return {
                'success': success,
                'message': message,
                'data': result_data
            }
            
        except Exception as e:
            error_msg = f"Cache clear failed: {str(e)}"
            task.mark_failed(error_msg)
            logger.error(error_msg)
            
            return {
                'success': False,
                'message': error_msg,
                'error': str(e)
            }
    
    @staticmethod
    def rotate_logs(initiated_by, max_age_days: int = 30) -> Dict[str, Any]:
        """
        Archive and rotate old log files.
        
        Args:
            initiated_by: User who initiated log rotation
            max_age_days: Maximum age of logs to keep
        
        Returns:
            dict: Log rotation operation result
        """
        task = MaintenanceTask.objects.create(
            task_type='log_rotation',
            title="Log Rotation",
            description=f"Rotating logs older than {max_age_days} days",
            initiated_by=initiated_by,
            parameters={'max_age_days': max_age_days}
        )
        
        try:
            task.mark_started()
            
            log_dir = getattr(settings, 'LOG_DIR', os.path.join(settings.BASE_DIR, 'logs'))
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            archive_dir = os.path.join(log_dir, 'archive')
            os.makedirs(archive_dir, exist_ok=True)
            
            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            
            rotated_files = []
            archived_size = 0
            
            for filename in os.listdir(log_dir):
                if filename.endswith('.log'):
                    file_path = os.path.join(log_dir, filename)
                    
                    # Check file modification time
                    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if mod_time < cutoff_date:
                        # Archive the file
                        timestamp = mod_time.strftime("%Y%m%d")
                        archived_name = f"{filename}.{timestamp}.gz"
                        archive_path = os.path.join(archive_dir, archived_name)
                        
                        # Compress and move
                        with open(file_path, 'rb') as f_in:
                            with gzip.open(archive_path, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        
                        file_size = os.path.getsize(file_path)
                        archived_size += file_size
                        
                        # Remove original
                        os.remove(file_path)
                        
                        rotated_files.append({
                            'filename': filename,
                            'archived_as': archived_name,
                            'size_mb': round(file_size / (1024**2), 2)
                        })
            
            result_data = {
                'rotated_files': rotated_files,
                'total_files': len(rotated_files),
                'total_archived_mb': round(archived_size / (1024**2), 2),
                'archive_directory': archive_dir,
                'rotation_time': timezone.now().isoformat()
            }
            
            task.mark_completed(result_data)
            
            # Log the operation
            AuditLog.objects.create(
                user=initiated_by,
                action='logs_rotated',
                description=f"Rotated {len(rotated_files)} log files",
                metadata=result_data
            )
            
            return {
                'success': True,
                'message': f"Successfully rotated {len(rotated_files)} log files",
                'data': result_data
            }
            
        except Exception as e:
            error_msg = f"Log rotation failed: {str(e)}"
            task.mark_failed(error_msg)
            logger.error(error_msg)
            
            return {
                'success': False,
                'message': error_msg,
                'error': str(e)
            }
    
    @staticmethod
    def toggle_feature(initiated_by, feature_name: str, enabled: Optional[bool] = None) -> Dict[str, Any]:
        """
        Toggle or set a feature flag.
        
        Args:
            initiated_by: User who initiated the feature toggle
            feature_name: Name of the feature to toggle
            enabled: Specific state to set (None = toggle current state)
        
        Returns:
            dict: Feature toggle operation result
        """
        task = MaintenanceTask.objects.create(
            task_type='feature_toggle',
            title=f"Feature Toggle: {feature_name}",
            description=f"Toggling feature '{feature_name}'",
            initiated_by=initiated_by,
            parameters={'feature_name': feature_name, 'enabled': enabled}
        )
        
        try:
            task.mark_started()
            
            # Get settings instance
            settings_instance = SystemSettings.get_instance()
            
            # Map feature names to actual model fields
            feature_field_mapping = {
                'registration': 'registration_enabled',
                'service_submissions': 'service_submissions_enabled',
                'emergency_mode': 'emergency_mode',
                'auto_approve_services': 'auto_approve_services',
                'auto_approve_comments': 'auto_approve_comments',
                'maintenance_mode': 'maintenance_mode',
            }
            
            if feature_name not in feature_field_mapping:
                raise ValueError(f"Unknown feature flag: {feature_name}")
            
            setting_field = feature_field_mapping[feature_name]
            current_state = getattr(settings_instance, setting_field)
            new_state = enabled if enabled is not None else not current_state
            
            # Update the setting
            setattr(settings_instance, setting_field, new_state)
            settings_instance.save()
            
            # Also update the SettingsLoader cache
            from .managers import SettingsLoader
            settings_loader = SettingsLoader()
            settings_loader._reload_settings()
            
            result_data = {
                'feature_name': feature_name,
                'previous_state': current_state,
                'new_state': new_state,
                'toggle_time': timezone.now().isoformat()
            }
            
            task.mark_completed(result_data)
            
            # Log the operation
            AuditLog.objects.create(
                user=initiated_by,
                action='feature_toggled',
                description=f"Feature '{feature_name}' toggled from {current_state} to {new_state}",
                metadata=result_data
            )
            
            return {
                'success': True,
                'message': f"Feature '{feature_name}' {'enabled' if new_state else 'disabled'}",
                'data': result_data
            }
            
        except Exception as e:
            error_msg = f"Feature toggle failed: {str(e)}"
            task.mark_failed(error_msg)
            logger.error(error_msg)
            
            return {
                'success': False,
                'message': error_msg,
                'error': str(e)
            }
    
    @staticmethod
    def cleanup_old_data(initiated_by, cleanup_types: Optional[list] = None, days_old: int = 90) -> Dict[str, Any]:
        """
        Clean up old data from the system.
        
        Args:
            initiated_by: User who initiated the cleanup
            cleanup_types: Types of data to clean up
            days_old: Age threshold for cleanup (days)
        
        Returns:
            dict: Cleanup operation result
        """
        if not cleanup_types:
            cleanup_types = ['audit_logs', 'metrics', 'notifications', 'maintenance_tasks']
        
        task = MaintenanceTask.objects.create(
            task_type='user_cleanup',
            title="Old Data Cleanup",
            description=f"Cleaning up data older than {days_old} days",
            initiated_by=initiated_by,
            parameters={'cleanup_types': cleanup_types, 'days_old': days_old}
        )
        
        try:
            task.mark_started()
            
            cutoff_date = timezone.now() - timezone.timedelta(days=days_old)
            cleanup_results = {}
            
            # Clean up audit logs
            if 'audit_logs' in cleanup_types:
                deleted_count = AuditLog.objects.filter(created_at__lt=cutoff_date).count()
                AuditLog.objects.filter(created_at__lt=cutoff_date).delete()
                cleanup_results['audit_logs'] = deleted_count
            
            # Clean up old metrics
            if 'metrics' in cleanup_types:
                from .models import SystemMetrics
                deleted_count = SystemMetrics.objects.filter(recorded_at__lt=cutoff_date).count()
                SystemMetrics.objects.filter(recorded_at__lt=cutoff_date).delete()
                cleanup_results['metrics'] = deleted_count
            
            # Clean up old notifications
            if 'notifications' in cleanup_types:
                from .models import NotificationQueue
                deleted_count = NotificationQueue.objects.filter(
                    created_at__lt=cutoff_date,
                    status__in=['sent', 'failed', 'cancelled']
                ).count()
                NotificationQueue.objects.filter(
                    created_at__lt=cutoff_date,
                    status__in=['sent', 'failed', 'cancelled']
                ).delete()
                cleanup_results['notifications'] = deleted_count
            
            # Clean up old maintenance tasks
            if 'maintenance_tasks' in cleanup_types:
                deleted_count = MaintenanceTask.objects.filter(
                    created_at__lt=cutoff_date,
                    status__in=['completed', 'failed', 'cancelled']
                ).count()
                MaintenanceTask.objects.filter(
                    created_at__lt=cutoff_date,
                    status__in=['completed', 'failed', 'cancelled']
                ).delete()
                cleanup_results['maintenance_tasks'] = deleted_count
            
            total_deleted = sum(cleanup_results.values())
            
            result_data = {
                'cleanup_types': cleanup_types,
                'days_old': days_old,
                'cutoff_date': cutoff_date.isoformat(),
                'cleanup_results': cleanup_results,
                'total_deleted': total_deleted,
                'cleanup_time': timezone.now().isoformat()
            }
            
            task.mark_completed(result_data)
            
            # Log the operation
            AuditLog.objects.create(
                user=initiated_by,
                action='data_cleanup',
                description=f"Cleaned up {total_deleted} old records",
                metadata=result_data
            )
            
            return {
                'success': True,
                'message': f"Successfully cleaned up {total_deleted} old records",
                'data': result_data
            }
            
        except Exception as e:
            error_msg = f"Data cleanup failed: {str(e)}"
            task.mark_failed(error_msg)
            logger.error(error_msg)
            
            return {
                'success': False,
                'message': error_msg,
                'error': str(e)
            }
    
    @staticmethod
    def get_maintenance_history(days: int = 30) -> Dict[str, Any]:
        """
        Get maintenance task history.
        
        Args:
            days: Number of days to look back
        
        Returns:
            dict: Maintenance history data
        """
        try:
            since = timezone.now() - timezone.timedelta(days=days)
            
            tasks = MaintenanceTask.objects.filter(
                created_at__gte=since
            ).order_by('-created_at')
            
            task_data = []
            for task in tasks:
                task_data.append({
                    'id': str(task.id),
                    'task_type': task.task_type,
                    'title': task.title,
                    'status': task.status,
                    'initiated_by': task.initiated_by.email,
                    'created_at': task.created_at.isoformat(),
                    'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                    'duration_seconds': task.duration_seconds,
                    'error_message': task.error_message if task.error_message else None
                })
            
            # Get summary statistics
            task_counts = {}
            for task in tasks:
                task_type = task.task_type
                if task_type not in task_counts:
                    task_counts[task_type] = {'total': 0, 'completed': 0, 'failed': 0}
                
                task_counts[task_type]['total'] += 1
                if task.status == 'completed':
                    task_counts[task_type]['completed'] += 1
                elif task.status == 'failed':
                    task_counts[task_type]['failed'] += 1
            
            return {
                'success': True,
                'data': {
                    'tasks': task_data,
                    'summary': task_counts,
                    'total_tasks': len(task_data),
                    'period_days': days
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get maintenance history: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def _create_sql_dump(backup_path: str) -> int:
        """Create SQL dump for PostgreSQL/MySQL databases."""
        # Placeholder for SQL dump creation
        # In a real implementation, this would use pg_dump or mysqldump
        with open(backup_path, 'w') as f:
            f.write("-- SQL dump placeholder\n")
        return os.path.getsize(backup_path) 