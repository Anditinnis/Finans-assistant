// ============ НАВБАР: скролл-эффект ============
window.addEventListener('scroll', () => {
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        navbar.classList.toggle('scrolled', window.scrollY > 20);
    }
}, { passive: true });

// ============ HAMBURGER-МЕНЮ ============
document.addEventListener('DOMContentLoaded', () => {
    const hamburger = document.getElementById('hamburger');
    const navLinks = document.getElementById('navLinks');

    if (!hamburger || !navLinks) return;

    const overlay = document.createElement('div');
    overlay.className = 'nav-overlay';
    document.body.appendChild(overlay);

    function toggleMenu(open) {
        const isOpen = open !== undefined ? open : !navLinks.classList.contains('active');
        navLinks.classList.toggle('active', isOpen);
        overlay.classList.toggle('active', isOpen);
        hamburger.classList.toggle('active', isOpen);
        hamburger.setAttribute('aria-expanded', String(isOpen));
        document.body.classList.toggle('menu-open', isOpen);
    }

    hamburger.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleMenu();
    });

    overlay.addEventListener('click', () => toggleMenu(false));

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && navLinks.classList.contains('active')) {
            toggleMenu(false);
        }
    });

    navLinks.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => toggleMenu(false));
    });

    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            if (window.innerWidth > 768 && navLinks.classList.contains('active')) {
                toggleMenu(false);
            }
        }, 150);
    });
});

// ============ ОБЩИЕ ФЛАГИ ============
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const isTouch = window.matchMedia('(hover: none)').matches;

// ============ ПОЯВЛЕНИЕ ПРИ СКРОЛЛЕ ============
if (!prefersReducedMotion && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.feature-card, .step, .stat-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
}

// ============ ПАРАЛЛАКС ФОНА ============
if (!isTouch && !prefersReducedMotion) {
    document.addEventListener('mousemove', (e) => {
        const blobs = document.querySelectorAll('.blob');
        const x = (e.clientX / window.innerWidth - 0.5) * 30;
        const y = (e.clientY / window.innerHeight - 0.5) * 30;
        blobs.forEach((blob, i) => {
            const factor = (i + 1) * 0.5;
            blob.style.transform = `translate(${x * factor}px, ${y * factor}px)`;
        });
    }, { passive: true });
}

// ============ RIPPLE-ЭФФЕКТ ============
if (!isTouch) {
    document.querySelectorAll('.btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            ripple.style.cssText = `
                position: absolute;
                width: ${size}px; height: ${size}px;
                left: ${e.clientX - rect.left - size/2}px;
                top: ${e.clientY - rect.top - size/2}px;
                background: rgba(255,255,255,0.4);
                border-radius: 50%;
                transform: scale(0);
                animation: ripple 0.6s ease-out;
                pointer-events: none;
            `;
            this.appendChild(ripple);
            setTimeout(() => ripple.remove(), 600);
        });
    });

    const style = document.createElement('style');
    style.textContent = `
        @keyframes ripple {
            to { transform: scale(4); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
}

// ============ ПАУЗА АНИМАЦИЙ В ФОНЕ ============
document.addEventListener('visibilitychange', () => {
    const blobs = document.querySelectorAll('.blob');
    blobs.forEach(blob => {
        blob.style.animationPlayState = document.hidden ? 'paused' : 'running';
    });
});

// ============ АНИМАЦИЯ ЧИСЕЛ ============
function animateNumber(el) {
    // Получаем исходную строку (например, "648.00 ₽" или "1000.00 ₽")
    const originalText = el.textContent.trim();
    
    // Отделяем валюту (₽) и всё остальное
    const suffix = originalText.includes('₽') ? ' ₽' : '';
    
    // Убираем всё, кроме цифр и точки/запятой
    let numStr = originalText.replace('₽', '').replace(/\s/g, '');
    
    // Если пришла точка (Django отдаёт 648.00), меняем её на запятую для парсинга
    if (numStr.includes('.') && !numStr.includes(',')) {
        numStr = numStr.replace('.', '.');
    } else {
        // Если уже есть запятая (русский формат), убираем точки тысяч
        numStr = numStr.replace(/\./g, '').replace(',', '.');
    }
    
    const target = parseFloat(numStr);
    if (isNaN(target)) return;

    const duration = 1200;
    const start = performance.now();
    
    // Определяем, нужны ли копейки (если транзакций 4, показываем "4", а не "4,00")
    const hasDecimals = originalText.includes('.') || originalText.includes(',');

    function tick(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = target * eased;
        
        let formatted = current.toLocaleString('ru-RU', {
            minimumFractionDigits: hasDecimals ? 2 : 0,
            maximumFractionDigits: hasDecimals ? 2 : 0
        });
        
        el.textContent = formatted + suffix;
        if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}

// ============ ПРОГРЕСС БЮДЖЕТА ============
document.addEventListener('DOMContentLoaded', () => {
    const fill = document.getElementById('budgetFill');
    const percentEl = document.getElementById('budgetPercent');
    if (!fill || !percentEl) return;

    const expense = parseFloat(fill.dataset.expense || 0);
    const income = parseFloat(fill.dataset.income || 0);
    const percent = income > 0 ? Math.min((expense / income) * 100, 100) : 0;

    setTimeout(() => {
        fill.style.width = percent + '%';
        let current = 0;
        const step = percent / 30;
        const timer = setInterval(() => {
            current += step;
            if (current >= percent) {
                current = percent;
                clearInterval(timer);
            }
            percentEl.textContent = Math.round(current) + '%';
        }, 20);
    }, 300);

    if (percent > 90) fill.classList.add('danger');
    else if (percent > 70) fill.classList.add('warning');
});

// ============ КОНФЕТТИ ============
function launchConfetti() {
    const colors = ['#6366f1', '#8b5cf6', '#ec4899', '#10b981', '#f59e0b'];
    for (let i = 0; i < 60; i++) {
        const confetti = document.createElement('div');
        confetti.style.cssText = `
            position: fixed;
            width: 8px; height: 8px;
            background: ${colors[Math.floor(Math.random() * colors.length)]};
            left: ${Math.random() * 100}vw;
            top: -10px;
            border-radius: ${Math.random() > 0.5 ? '50%' : '0'};
            pointer-events: none;
            z-index: 9999;
            animation: confettiFall ${2 + Math.random() * 2}s linear forwards;
        `;
        document.body.appendChild(confetti);
        setTimeout(() => confetti.remove(), 4000);
    }
}
window.launchConfetti = launchConfetti;

// ============ ПРИВЕТСТВИЕ И ЧАСЫ ============
document.addEventListener('DOMContentLoaded', () => {
    const greeting = document.getElementById('greeting');
    const clock = document.getElementById('liveClock');
    if (greeting) {
        const h = new Date().getHours();
        greeting.textContent = h < 6 ? 'Доброй ночи' : h < 12 ? 'Доброе утро' : h < 18 ? 'Добрый день' : 'Добрый вечер';
    }
    if (clock) {
        const update = () => {
            const now = new Date();
            clock.textContent = now.toLocaleString('ru-RU', {
                weekday: 'long', day: 'numeric', month: 'long',
                hour: '2-digit', minute: '2-digit'
            });
        };
        update();
        setInterval(update, 30000);
    }
});

// ============ TILT-ЭФФЕКТ ============
if (!isTouch && !prefersReducedMotion) {
    document.querySelectorAll('.stat-card, .feature-card').forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = (e.clientX - rect.left) / rect.width - 0.5;
            const y = (e.clientY - rect.top) / rect.height - 0.5;
            card.style.transform = `perspective(800px) rotateX(${-y * 6}deg) rotateY(${x * 6}deg) translateY(-4px)`;
        });
        card.addEventListener('mouseleave', () => {
            card.style.transform = '';
        });
    });
}

// ============ LOADER: СКРЫТИЕ БЕЗ ЗАДЕРЖКИ ============
function hideLoader() {
    const loader = document.getElementById('pageLoader');
    if (loader) {
        loader.classList.add('hidden');
        // полностью убрать из DOM через 0.4s (после transition)
        setTimeout(() => loader.remove(), 400);
    }
}

// Скрываем, как только DOM готов (не ждём картинки/шрифты)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', hideLoader);
} else {
    hideLoader();
}

// FALLBACK: если DOMContentLoaded уже прошёл, но что-то пошло не так —
// максимум 1.5 секунды, а не 3
setTimeout(hideLoader, 1500);

// при возврате со страницы через bfcache — лоадер не нужен
window.addEventListener('pageshow', (e) => {
    if (e.persisted) hideLoader();
});