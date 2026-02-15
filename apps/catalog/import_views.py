"""
Импорт категорий и товаров из CSV с rate limiting.
"""
import csv
import io
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import Product, Category
from ..common.permissions import IsAdmin
from ..common.throttles import ImportRateThrottle


@api_view(['POST'])
@permission_classes([IsAdmin])
def import_products_csv(request):
    throttle = ImportRateThrottle()
    if not throttle.allow_request(request, None):
        return Response(
            {'error': 'Превышен лимит запросов на импорт. Попробуйте позже.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    if 'file' not in request.FILES:
        return Response(
            {'error': 'Файл не предоставлен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    file = request.FILES['file']
    if not file.name.endswith('.csv'):
        return Response(
            {'error': 'Файл должен быть в формате CSV'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    MAX_FILE_SIZE = 10 * 1024 * 1024
    if file.size > MAX_FILE_SIZE:
        return Response(
            {'error': f'Размер файла превышает максимально допустимый ({MAX_FILE_SIZE / 1024 / 1024:.1f}MB)'},
            status=status.HTTP_400_BAD_REQUEST
        )
    if file.size < 10:
        return Response(
            {'error': 'Файл слишком маленький или пустой'},
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        file_content = file.read()
        decoded_file = None
        
        for encoding in ['utf-8-sig', 'utf-8', 'cp1251', 'windows-1251']:
            try:
                decoded_file = file_content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if decoded_file is None:
            return Response(
                {'error': 'Не удалось определить кодировку файла. Используйте UTF-8'},
                status=status.HTTP_400_BAD_REQUEST
            )
        MAX_ROWS = 10000
        lines = decoded_file.splitlines()
        row_count = len(lines) - 1
        
        if row_count > MAX_ROWS:
            return Response(
                {'error': f'Файл содержит слишком много строк ({row_count}). Максимум: {MAX_ROWS}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if row_count < 1:
            return Response(
                {'error': 'Файл не содержит данных (только заголовки)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        csv_reader = csv.DictReader(io.StringIO(decoded_file))
        
    except Exception as e:
        return Response(
            {'error': f'Ошибка чтения файла: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    errors = []
    success_count = 0
    updated_count = 0
    products_to_create = []
    products_to_update = []
    existing_skus = set(Product.objects.values_list('sku', flat=True))
    category_map = {cat.name: cat for cat in Category.objects.all()}
    
    try:
        with transaction.atomic():
            for row_num, row in enumerate(csv_reader, start=2):
                try:
                    if not row.get('SKU') or not row.get('Название'):
                        errors.append(f'Строка {row_num}: Отсутствуют обязательные поля (SKU, Название)')
                        continue
                    
                    sku = row['SKU'].strip()
                    name = row['Название'].strip()
                    description = row.get('Описание', '').strip()
                    category = None
                    if row.get('Категория'):
                        category_name = row['Категория'].strip()
                        category = category_map.get(category_name)
                        if not category:
                            errors.append(f'Строка {row_num}: Категория "{category_name}" не найдена')
                            continue
                    try:
                        price = float(row['Цена'].replace(',', '.')) if row.get('Цена') else 0.0
                    except (ValueError, AttributeError):
                        errors.append(f'Строка {row_num}: Неверный формат цены')
                        continue
                    try:
                        stock_quantity = int(row['Количество на складе']) if row.get('Количество на складе') else 0
                    except (ValueError, AttributeError):
                        errors.append(f'Строка {row_num}: Неверный формат количества')
                        continue
                    is_available = row.get('Доступен', 'да').lower() in ('да', 'yes', 'true', '1')
                    if sku in existing_skus:
                        products_to_update.append({
                            'sku': sku,
                            'name': name,
                            'description': description,
                            'category': category,
                            'price': price,
                            'stock_quantity': stock_quantity,
                            'is_available': is_available,
                            'row_num': row_num
                        })
                    else:
                        products_to_create.append(Product(
                            sku=sku,
                            name=name,
                            description=description,
                            category=category,
                            price=price,
                            stock_quantity=stock_quantity,
                            is_available=is_available
                        ))
                        existing_skus.add(sku)
                except Exception as e:
                    errors.append(f'Строка {row_num}: {str(e)}')
                    continue
            if products_to_create:
                Product.objects.bulk_create(products_to_create, batch_size=100)
                success_count = len(products_to_create)
            if products_to_update:
                update_skus = [p['sku'] for p in products_to_update]
                existing_products = {p.sku: p for p in Product.objects.filter(sku__in=update_skus)}
                
                products_bulk_update = []
                for update_data in products_to_update:
                    sku = update_data['sku']
                    if sku in existing_products:
                        product = existing_products[sku]
                        product.name = update_data['name']
                        if update_data['description']:
                            product.description = update_data['description']
                        if update_data['category']:
                            product.category = update_data['category']
                        product.price = update_data['price']
                        product.stock_quantity = update_data['stock_quantity']
                        product.is_available = update_data['is_available']
                        products_bulk_update.append(product)
                
                if products_bulk_update:
                    Product.objects.bulk_update(
                        products_bulk_update,
                        ['name', 'description', 'category', 'price', 'stock_quantity', 'is_available'],
                        batch_size=100
                    )
                    updated_count = len(products_bulk_update)
            from .services import ProductService, CategoryService
            ProductService.invalidate_cache()
            CategoryService.invalidate_cache()
    
    except Exception as e:
        return Response(
            {'error': f'Ошибка импорта: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return Response({
        'message': 'Импорт завершен',
        'created': success_count,
        'updated': updated_count,
        'errors': errors,
        'total_processed': success_count + updated_count,
        'has_errors': len(errors) > 0
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAdmin])
def import_categories_csv(request):
    throttle = ImportRateThrottle()
    if not throttle.allow_request(request, None):
        return Response(
            {'error': 'Превышен лимит запросов на импорт. Попробуйте позже.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    if 'file' not in request.FILES:
        return Response(
            {'error': 'Файл не предоставлен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    file = request.FILES['file']
    
    if not file.name.endswith('.csv'):
        return Response(
            {'error': 'Файл должен быть в формате CSV'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    MAX_FILE_SIZE = 10 * 1024 * 1024
    if file.size > MAX_FILE_SIZE:
        return Response(
            {'error': f'Размер файла превышает максимально допустимый ({MAX_FILE_SIZE / 1024 / 1024:.1f}MB)'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        decoded_file = file.read().decode('utf-8-sig')
        csv_reader = csv.DictReader(io.StringIO(decoded_file))
    except Exception as e:
        return Response(
            {'error': f'Ошибка чтения файла: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    errors = []
    success_count = 0
    updated_count = 0
    categories_to_create = []
    categories_to_update = []
    existing_names = {cat.name: cat for cat in Category.objects.all()}
    try:
        with transaction.atomic():
            for row_num, row in enumerate(csv_reader, start=2):
                try:
                    if not row.get('Название'):
                        errors.append(f'Строка {row_num}: Отсутствует обязательное поле "Название"')
                        continue
                    
                    name = row['Название'].strip()
                    description = row.get('Описание', '').strip()
                    parent = None
                    if row.get('Родительская категория'):
                        parent_name = row['Родительская категория'].strip()
                        parent = existing_names.get(parent_name)
                        if not parent:
                            errors.append(f'Строка {row_num}: Родительская категория "{parent_name}" не найдена')
                            continue
                    if name in existing_names:
                        categories_to_update.append({
                            'name': name,
                            'description': description,
                            'parent': parent,
                            'row_num': row_num
                        })
                    else:
                        categories_to_create.append(Category(
                            name=name,
                            description=description,
                            parent=parent
                        ))
                        existing_names[name] = None
                except Exception as e:
                    errors.append(f'Строка {row_num}: {str(e)}')
                    continue
            if categories_to_create:
                Category.objects.bulk_create(categories_to_create, batch_size=100)
                success_count = len(categories_to_create)
            if categories_to_update:
                update_names = [c['name'] for c in categories_to_update]
                existing_categories = {c.name: c for c in Category.objects.filter(name__in=update_names)}
                
                categories_bulk_update = []
                for update_data in categories_to_update:
                    name = update_data['name']
                    if name in existing_categories:
                        category = existing_categories[name]
                        if update_data['description']:
                            category.description = update_data['description']
                        if update_data['parent']:
                            category.parent = update_data['parent']
                        categories_bulk_update.append(category)
                
                if categories_bulk_update:
                    Category.objects.bulk_update(
                        categories_bulk_update,
                        ['description', 'parent'],
                        batch_size=100
                    )
                    updated_count = len(categories_bulk_update)
            from .services import CategoryService
            CategoryService.invalidate_cache()
    
    except Exception as e:
        return Response(
            {'error': f'Ошибка импорта: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return Response({
        'message': 'Импорт завершен',
        'created': success_count,
        'updated': updated_count,
        'errors': errors,
        'total_processed': success_count + updated_count,
        'has_errors': len(errors) > 0
    }, status=status.HTTP_200_OK)

