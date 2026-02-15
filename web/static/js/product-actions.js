// Обработка действий с товарами (добавление в корзину, изменение количества)

document.addEventListener('DOMContentLoaded', function() {
    // Обработка кнопки "В корзину"
    document.querySelectorAll('.add-to-cart-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const productId = this.getAttribute('data-product-id');
            const productActions = this.closest('.product-actions');
            const quantityInput = productActions.querySelector('.quantity-input');
            const quantity = quantityInput ? parseInt(quantityInput.value) : 1;
            
            // Показываем переключатель количества, если он скрыт
            const quantityControl = productActions.querySelector('.quantity-control');
            if (quantityControl && quantityControl.classList.contains('d-none')) {
                quantityControl.classList.remove('d-none');
                const actionButtons = productActions.querySelector('.action-buttons');
                if (actionButtons) {
                    actionButtons.querySelector('.add-to-cart-btn').textContent = 'Обновить корзину';
                }
            }
            
            // Отправляем запрос на добавление в корзину
            addToCart(productId, quantity, productActions);
        });
    });
    
    // Обработка кнопки "Купить сейчас"
    document.querySelectorAll('.buy-now-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const productId = this.getAttribute('data-product-id');
            const productActions = this.closest('.product-actions');
            const quantityInput = productActions.querySelector('.quantity-input');
            const quantity = quantityInput ? parseInt(quantityInput.value) : 1;
            
            // Добавляем в корзину и переходим к оформлению
            addToCartAndCheckout(productId, quantity);
        });
    });
    
    // Обработка кнопок изменения количества
    document.querySelectorAll('.quantity-increase').forEach(button => {
        button.addEventListener('click', function() {
            const input = this.parentElement.querySelector('.quantity-input');
            const max = parseInt(input.getAttribute('max')) || 999;
            const current = parseInt(input.value) || 1;
            if (current < max) {
                input.value = current + 1;
            }
        });
    });
    
    document.querySelectorAll('.quantity-decrease').forEach(button => {
        button.addEventListener('click', function() {
            const input = this.parentElement.querySelector('.quantity-input');
            const min = parseInt(input.getAttribute('min')) || 1;
            const current = parseInt(input.value) || 1;
            if (current > min) {
                input.value = current - 1;
            }
        });
    });
    
    // Обработка прямого ввода количества
    document.querySelectorAll('.quantity-input').forEach(input => {
        input.addEventListener('change', function() {
            const min = parseInt(this.getAttribute('min')) || 1;
            const max = parseInt(this.getAttribute('max')) || 999;
            let value = parseInt(this.value) || min;
            
            if (value < min) value = min;
            if (value > max) value = max;
            
            this.value = value;
        });
        
        // Разрешаем редактирование при клике
        input.addEventListener('click', function() {
            if (this.hasAttribute('readonly')) {
                this.removeAttribute('readonly');
                this.focus();
                this.select();
            }
        });
        
        input.addEventListener('blur', function() {
            const max = parseInt(this.getAttribute('max')) || 999;
            if (parseInt(this.value) > max) {
                this.setAttribute('readonly', 'readonly');
            }
        });
    });
});

function addToCart(productId, quantity, productActions) {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/cart/add/${productId}/`;
    
    // Пытаемся получить CSRF токен из разных источников
    let csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfToken) {
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = csrfToken.value;
        form.appendChild(csrfInput);
    } else if (typeof csrftoken !== 'undefined') {
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = csrftoken;
        form.appendChild(csrfInput);
    }
    
    const quantityInput = document.createElement('input');
    quantityInput.type = 'hidden';
    quantityInput.name = 'quantity';
    quantityInput.value = quantity;
    form.appendChild(quantityInput);
    
    document.body.appendChild(form);
    form.submit();
}

function addToCartAndCheckout(productId, quantity) {
    // Сначала добавляем в корзину
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/cart/add/${productId}/`;
    
    // Пытаемся получить CSRF токен из разных источников
    let csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfToken) {
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = csrfToken.value;
        form.appendChild(csrfInput);
    } else if (typeof csrftoken !== 'undefined') {
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = csrftoken;
        form.appendChild(csrfInput);
    }
    
    const quantityInput = document.createElement('input');
    quantityInput.type = 'hidden';
    quantityInput.name = 'quantity';
    quantityInput.value = quantity;
    form.appendChild(quantityInput);
    
    // После успешного добавления переходим к оформлению
    form.addEventListener('submit', function(e) {
        // Переход произойдет после успешного добавления
        setTimeout(() => {
            window.location.href = '/checkout/';
        }, 500);
    });
    
    document.body.appendChild(form);
    form.submit();
}

