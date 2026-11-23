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
            if (window.innerWidth > 1024 && navLinks.classList.contains('active')) {
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
    // Берём чистое число из data-атрибута, который мы прописали в HTML
    const target = parseFloat(el.dataset.value);
    if (isNaN(target)) return; // если числа нет — ничего не делаем

    // Берём суффикс (например, " ₽" или пустую строку)
    const suffix = el.dataset.suffix || '';
    
    // Определяем, нужны ли копейки (если в исходном числе есть точка)
    const hasDecimals = el.dataset.value.includes('.');

    const duration = 1200;
    const start = performance.now();

    function tick(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
        const current = target * eased;
        
        let formatted;
        if (hasDecimals) {
            formatted = current.toLocaleString('ru-RU', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        } else {
            // для целых чисел (кол-во транзакций) — без копеек
            formatted = Math.round(current).toLocaleString('ru-RU'); 
        }
        
        el.textContent = formatted + suffix;
        if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}
// Запуск анимации для всех карточек при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.stat-value').forEach(el => {
        // Если есть data-value — запускаем анимацию
        if (el.dataset.value) {
            // Сначала очищаем текст (чтобы не было мелькания старого числа)
            el.textContent = '';
            animateNumber(el);
        }
    });
});

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

// ============ ТЕМЫ ОФОРМЛЕНИЯ ============
(function initThemeSwitcher() {
    const STORAGE_THEME = 'budget-theme';
    const STORAGE_EFFECTS = 'budget-effects';
    const root = document.documentElement;
    const meta = document.getElementById('themeColorMeta');
    const switcher = document.getElementById('themeSwitcher');
    const toggle = document.getElementById('themeToggle');
    const effectsInput = document.getElementById('effectsToggle');

    const THEME_COLORS = {
        midnight: '#0a0e27',
        light: '#f5f7fb',
        neon: '#05010f',
        sunset: '#1a0f14',
    };

    function applyTheme(name, persist) {
        if (!THEME_COLORS[name]) name = 'midnight';
        root.setAttribute('data-theme', name);
        if (meta) meta.setAttribute('content', THEME_COLORS[name]);

        document.querySelectorAll('[data-theme-value]').forEach((btn) => {
            const active = btn.dataset.themeValue === name;
            btn.classList.toggle('is-active', active);
            btn.setAttribute('aria-pressed', String(active));
        });

        if (persist) {
            try { localStorage.setItem(STORAGE_THEME, name); } catch (e) { /* ignore */ }
        }

        document.dispatchEvent(new CustomEvent('themechange', { detail: { theme: name } }));
    }

    function setEffects(enabled, persist) {
        root.setAttribute('data-effects', enabled ? 'on' : 'off');
        if (effectsInput) effectsInput.checked = enabled;
        if (persist) {
            try { localStorage.setItem(STORAGE_EFFECTS, enabled ? 'on' : 'off'); } catch (e) { /* ignore */ }
        }
        document.dispatchEvent(new CustomEvent('effectstoggle', { detail: { enabled } }));
    }

    function closeMenu() {
        if (!switcher) return;
        switcher.classList.remove('open');
        if (toggle) toggle.setAttribute('aria-expanded', 'false');
    }

    if (toggle && switcher) {
        toggle.addEventListener('click', (event) => {
            event.stopPropagation();
            const isOpen = switcher.classList.toggle('open');
            toggle.setAttribute('aria-expanded', String(isOpen));
        });
    }

    document.querySelectorAll('[data-theme-value]').forEach((btn) => {
        btn.addEventListener('click', () => {
            applyTheme(btn.dataset.themeValue, true);
            closeMenu();
        });
    });

    if (effectsInput) {
        effectsInput.addEventListener('change', () => setEffects(effectsInput.checked, true));
    }

    document.addEventListener('click', (event) => {
        if (switcher && !switcher.contains(event.target)) closeMenu();
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') closeMenu();
    });

    // Синхронизируем интерфейс с темой, которую применил анти-вспышечный скрипт.
    applyTheme(root.getAttribute('data-theme') || 'midnight', false);
    setEffects(root.getAttribute('data-effects') !== 'off', false);
})();

// ============ ЧАСТИЦЫ ЗА КУРСОРОМ ============
(function initParticles() {
    const canvas = document.getElementById('fxCanvas');
    if (!canvas || !canvas.getContext) return;

    const root = document.documentElement;
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const coarsePointer = window.matchMedia('(hover: none)').matches;

    if (reduceMotion || coarsePointer) {
        canvas.remove();
        return;
    }

    const ctx = canvas.getContext('2d');
    const particles = [];
    const ambient = [];
    const MAX_PARTICLES = 70;
    let colors = ['#6366f1', '#8b5cf6', '#ec4899', '#06b6d4'];
    let width = 0;
    let height = 0;
    let dpr = 1;
    let lastSpawn = 0;
    let rafId = null;

    function effectsEnabled() {
        return root.getAttribute('data-effects') !== 'off';
    }

    function readColors() {
        const raw = getComputedStyle(root).getPropertyValue('--fx-colors') || '';
        const parsed = raw.split(',').map((item) => item.trim()).filter(Boolean);
        if (parsed.length) colors = parsed;
    }

    function pickColor() {
        return colors[Math.floor(Math.random() * colors.length)];
    }

    function makeAmbient() {
        return {
            x: Math.random() * width,
            y: Math.random() * height,
            r: 1.2 + Math.random() * 2.4,
            vx: (Math.random() - 0.5) * 0.12,
            vy: -0.05 - Math.random() * 0.12,
            alpha: 0.12 + Math.random() * 0.25,
            color: pickColor(),
        };
    }

    function seedAmbient() {
        ambient.length = 0;
        const count = Math.max(8, Math.round(width / 170));
        for (let i = 0; i < count; i += 1) ambient.push(makeAmbient());
    }

    function resize() {
        dpr = Math.min(window.devicePixelRatio || 1, 2);
        width = window.innerWidth;
        height = window.innerHeight;
        canvas.width = Math.floor(width * dpr);
        canvas.height = Math.floor(height * dpr);
        canvas.style.width = width + 'px';
        canvas.style.height = height + 'px';
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        seedAmbient();
    }

    function spawn(x, y) {
        if (particles.length >= MAX_PARTICLES) return;
        const angle = Math.random() * Math.PI * 2;
        const speed = 0.15 + Math.random() * 0.55;
        particles.push({
            x: x,
            y: y,
            vx: Math.cos(angle) * speed,
            vy: Math.sin(angle) * speed - 0.15,
            r: 1.5 + Math.random() * 3.5,
            life: 1,
            decay: 0.008 + Math.random() * 0.012,
            color: pickColor(),
        });
    }

    function draw() {
        if (!effectsEnabled()) {
            rafId = null;
            return;
        }

        ctx.clearRect(0, 0, width, height);

        ambient.forEach((p) => {
            p.x += p.vx;
            p.y += p.vy;
            if (p.y < -10) {
                p.y = height + 10;
                p.x = Math.random() * width;
            }
            if (p.x < -10) p.x = width + 10;
            if (p.x > width + 10) p.x = -10;

            ctx.beginPath();
            ctx.globalAlpha = p.alpha;
            ctx.fillStyle = p.color;
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fill();
        });

        for (let i = particles.length - 1; i >= 0; i -= 1) {
            const p = particles[i];
            p.x += p.vx;
            p.y += p.vy;
            p.vy += 0.008;
            p.vx *= 0.995;
            p.vy *= 0.995;
            p.life -= p.decay;

            if (p.life <= 0) {
                particles.splice(i, 1);
                continue;
            }

            ctx.beginPath();
            ctx.globalAlpha = p.life * 0.55;
            ctx.fillStyle = p.color;
            ctx.arc(p.x, p.y, p.r * p.life, 0, Math.PI * 2);
            ctx.fill();
        }

        ctx.globalAlpha = 1;
        rafId = requestAnimationFrame(draw);
    }

    function start() {
        if (rafId || !effectsEnabled()) return;
        rafId = requestAnimationFrame(draw);
    }

    function stop() {
        if (rafId) cancelAnimationFrame(rafId);
        rafId = null;
        particles.length = 0;
        ctx.clearRect(0, 0, width, height);
    }

    window.addEventListener('mousemove', (event) => {
        if (!effectsEnabled()) return;
        const now = performance.now();
        if (now - lastSpawn < 45) return;
        lastSpawn = now;
        spawn(event.clientX, event.clientY);
        if (Math.random() > 0.6) {
            spawn(
                event.clientX + (Math.random() - 0.5) * 18,
                event.clientY + (Math.random() - 0.5) * 18
            );
        }
    }, { passive: true });

    document.addEventListener('themechange', readColors);

    document.addEventListener('effectstoggle', (event) => {
        if (event.detail.enabled) start();
        else stop();
    });

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) stop();
        else start();
    });

    window.addEventListener('resize', resize, { passive: true });

    readColors();
    resize();
    start();
})();

// ============ УБОРКА ТОСТОВ ============
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.toast').forEach((toast, index) => {
        setTimeout(() => toast.remove(), 4600 + index * 200);
    });
});