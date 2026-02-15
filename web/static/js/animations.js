// Современные анимации и интерактивные эффекты для сайта

document.addEventListener('DOMContentLoaded', function() {
    // ============================================
    // Анимация при скролле
    // ============================================
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animated');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Применяем анимацию к элементам
    document.querySelectorAll('.animate-on-scroll').forEach(el => {
        observer.observe(el);
    });

    // ============================================
    // Эффект параллакса только для изображений ВНЕ карточек товаров
    // (в карточках товаров картинки остаются статичными, только лёгкий zoom при наведении)
    // ============================================
    const parallaxImages = document.querySelectorAll('.parallax-image:not(.card-img-top)');
    
    if (parallaxImages.length > 0) {
        window.addEventListener('scroll', function() {
            const scrolled = window.pageYOffset;
            parallaxImages.forEach(image => {
                if (image.closest('.product-card')) return;
                const speed = 0.5;
                const yPos = -(scrolled * speed);
                image.style.transform = `translateY(${yPos}px)`;
            });
        });
    }

    // ============================================
    // Эффект магнитного притяжения для кнопок
    // ============================================
    const magneticButtons = document.querySelectorAll('.magnetic-btn, .btn-primary, .btn-hero-catalog');
    
    magneticButtons.forEach(btn => {
        btn.addEventListener('mousemove', function(e) {
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;
            
            const moveX = x * 0.15;
            const moveY = y * 0.15;
            
            this.style.transform = `translate(${moveX}px, ${moveY}px)`;
        });
        
        btn.addEventListener('mouseleave', function() {
            this.style.transform = 'translate(0, 0)';
        });
    });

    // ============================================
    // Эффект навигации при скролле
    // ============================================
    const navbar = document.querySelector('.navbar');
    let lastScroll = 0;
    
    window.addEventListener('scroll', function() {
        const currentScroll = window.pageYOffset;
        
        if (currentScroll > 100) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
        
        // Скрытие/показ навигации при скролле
        if (currentScroll > lastScroll && currentScroll > 200) {
            navbar.style.transform = 'translateY(-100%)';
        } else {
            navbar.style.transform = 'translateY(0)';
        }
        
        lastScroll = currentScroll;
    });

    // ============================================
    // Анимация счетчиков (для статистики)
    // ============================================
    function animateCounter(element, target, duration = 2000) {
        let start = 0;
        const increment = target / (duration / 16);
        
        const timer = setInterval(() => {
            start += increment;
            if (start >= target) {
                element.textContent = Math.round(target);
                clearInterval(timer);
            } else {
                element.textContent = Math.round(start);
            }
        }, 16);
    }

    const counters = document.querySelectorAll('.counter');
    const counterObserver = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const target = parseInt(entry.target.getAttribute('data-target'));
                animateCounter(entry.target, target);
                counterObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });

    counters.forEach(counter => {
        counterObserver.observe(counter);
    });

    // ============================================
    // Эффект печатающегося текста
    // ============================================
    function typeWriter(element, text, speed = 100) {
        let i = 0;
        element.textContent = '';
        
        function type() {
            if (i < text.length) {
                element.textContent += text.charAt(i);
                i++;
                setTimeout(type, speed);
            }
        }
        
        type();
    }

    const typeWriterElements = document.querySelectorAll('.typewriter');
    typeWriterElements.forEach(el => {
        const text = el.getAttribute('data-text') || el.textContent;
        el.textContent = '';
        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    typeWriter(entry.target, text);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });
        observer.observe(el);
    });

    // ============================================
    // Эффект волны для кнопок
    // ============================================
    function createRipple(event) {
        const button = event.currentTarget;
        const circle = document.createElement('span');
        const diameter = Math.max(button.clientWidth, button.clientHeight);
        const radius = diameter / 2;

        circle.style.width = circle.style.height = `${diameter}px`;
        circle.style.left = `${event.clientX - button.offsetLeft - radius}px`;
        circle.style.top = `${event.clientY - button.offsetTop - radius}px`;
        circle.classList.add('ripple');

        const ripple = button.getElementsByClassName('ripple')[0];
        if (ripple) {
            ripple.remove();
        }

        button.appendChild(circle);
    }

    const rippleButtons = document.querySelectorAll('.btn, .card, .product-card');
    rippleButtons.forEach(button => {
        button.addEventListener('click', createRipple);
    });

    // ============================================
    // Плавная прокрутка с эффектом
    // ============================================
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // ============================================
    // Эффект появления карточек товаров
    // ============================================
    const productCards = document.querySelectorAll('.product-card');
    productCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(30px)';
        
        setTimeout(() => {
            card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });

    // ============================================
    // Эффект hover для карточек категорий
    // ============================================
    const categoryCards = document.querySelectorAll('.category-card');
    categoryCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });

    // ============================================
    // Эффект загрузки для изображений
    // ============================================
    const images = document.querySelectorAll('img');
    images.forEach(img => {
        if (!img.complete) {
            img.classList.add('loading-shimmer');
            img.addEventListener('load', function() {
                this.classList.remove('loading-shimmer');
                this.style.opacity = '0';
                setTimeout(() => {
                    this.style.transition = 'opacity 0.5s';
                    this.style.opacity = '1';
                }, 100);
            });
        }
    });

    // ============================================
    // Анимация при добавлении в корзину
    // ============================================
    window.addEventListener('cart-updated', function() {
        const cartIcon = document.querySelector('.nav-link[href*="cart"]');
        if (cartIcon) {
            cartIcon.style.animation = 'pulse 0.5s';
            setTimeout(() => {
                cartIcon.style.animation = '';
            }, 500);
        }
    });
});

// Добавляем стили для ripple эффекта
const style = document.createElement('style');
style.textContent = `
    .ripple {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.6);
        transform: scale(0);
        animation: ripple-animation 0.6s ease-out;
        pointer-events: none;
    }
    
    @keyframes ripple-animation {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
    
    .btn, .card, .product-card {
        position: relative;
        overflow: hidden;
    }
`;
document.head.appendChild(style);

