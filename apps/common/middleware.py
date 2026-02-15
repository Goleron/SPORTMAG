"""
Middleware для логирования и мониторинга
"""
import time
import logging
import uuid
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('apps')


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware для логирования запросов с корреляционными ID
    """
    
    def process_request(self, request):
        """Добавляем корреляционный ID к запросу"""
        request.correlation_id = str(uuid.uuid4())
        request.start_time = time.time()
    
    def process_response(self, request, response):
        """Логируем информацию о запросе"""
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            # Логируем медленные запросы (> 1 секунда)
            if duration > 1.0:
                logger.warning(
                    'Slow request',
                    extra={
                        'correlation_id': getattr(request, 'correlation_id', None),
                        'method': request.method,
                        'path': request.path,
                        'status_code': response.status_code,
                        'duration': round(duration, 3),
                        'user': getattr(request.user, 'username', 'anonymous') if hasattr(request, 'user') else 'anonymous',
                    }
                )
            else:
                logger.info(
                    'Request processed',
                    extra={
                        'correlation_id': getattr(request, 'correlation_id', None),
                        'method': request.method,
                        'path': request.path,
                        'status_code': response.status_code,
                        'duration': round(duration, 3),
                    }
                )
        
        # Добавляем корреляционный ID в заголовок ответа
        if hasattr(request, 'correlation_id'):
            response['X-Correlation-ID'] = request.correlation_id
        
        return response
    
    def process_exception(self, request, exception):
        """Логируем исключения"""
        logger.error(
            'Request exception',
            extra={
                'correlation_id': getattr(request, 'correlation_id', None),
                'method': request.method,
                'path': request.path,
                'exception_type': type(exception).__name__,
                'exception_message': str(exception),
            },
            exc_info=True
        )


class DatabaseQueryLoggingMiddleware(MiddlewareMixin):
    """
    Middleware для логирования количества запросов к БД
    """
    
    def process_request(self, request):
        """Инициализируем счетчик запросов"""
        from django.db import connection
        request.db_query_count_start = len(connection.queries)
    
    def process_response(self, request, response):
        """Логируем количество запросов к БД"""
        from django.db import connection
        
        if hasattr(request, 'db_query_count_start'):
            query_count = len(connection.queries) - request.db_query_count_start
            
            # Логируем если запросов больше 10 (потенциальная N+1 проблема)
            if query_count > 10:
                logger.warning(
                    'High database query count',
                    extra={
                        'correlation_id': getattr(request, 'correlation_id', None),
                        'method': request.method,
                        'path': request.path,
                        'query_count': query_count,
                    }
                )
        
        return response

