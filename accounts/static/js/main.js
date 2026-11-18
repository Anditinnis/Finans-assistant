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

    if (!hamburger || !navLinks) {
        console.warn('Hamburger или navLinks не найдены в DOM');
        return;
    }

    // Создаём оверлей
    const overlay = document.createElement('div');
    overlay.className = 'nav-overlay';
    document.body.appendChild(overlay);

    // По умолчанию оверлей не перехватывает клики
    overlay.style.pointerEvents = 'none';

    function toggleMenu(open) {
        const isOpen = open !== undefined ? open : !navLinks.classList.contains('active');
        navLinks.classList.toggle('active', isOpen);
        overlay.classList.toggle('active', isOpen);
        hamburger.classList.toggle('active', isOpen);
        hamburger.setAttribute('aria-expanded', String(isOpen));
        document.body.classList.toggle('menu-open', isOpen);

        // Оверлей перехватывает клики только когда меню открыто
        overlay.style.pointerEvents = isOpen ? 'auto' : 'none';

        // Принудительно поднимаем меню над оверлеем
        if (isOpen) {
            navLinks.style.zIndex = '106';
            navLinks.style.pointerEvents = 'auto';
            // Убеждаемся, что все ссылки и кнопки кликабельны
            navLinks.querySelectorAll('a, button').forEach(el => {
                el.style.pointerEvents = 'auto';
                el.style.position = 'relative';
                el.style.zIndex = '107';
            });
        } else {
            navLinks.style.zIndex = '';
            navLinks.style.pointerEvents = '';
            navLinks.querySelectorAll('a, button').forEach(el => {
                el.style.pointerEvents = '';
                el.style.position = '';
                el.style.zIndex = '';
            });
        }
    }

    hamburger.addEventListener('click', () => toggleMenu());
    overlay.addEventListener('click', () => toggleMenu(false));

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && navLinks.classList.contains('active')) {
            toggleMenu(false);
        }
    });

    // Закрываем меню при клике по любой ссылке
    navLinks.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => toggleMenu(false));
    });

    // Закрываем меню при ресайзе на десктоп
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

// ============ ПОЯВЛЕНИЕ ПРИ СКРОЛЛЕ ============
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

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
const isTouch = window.matchMedia('(hover: none)').matches;

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