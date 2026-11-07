function changeImage(el) {
    const mainImg = document.getElementById('main-product-image');
    if (!mainImg) return;
    mainImg.src = el.dataset.full;

    // حذف active از همه، اضافه به کلیک‌شده
    document.querySelectorAll('.thumbnails .thumb').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
}

// وقتی فرم submit می‌شه، دکمه رو در حالت لودینگ ببر
document.addEventListener('submit', function(e) {
    const btn = e.target.querySelector('button[type="submit"]');
    if (btn && !btn.disabled) {
        btn.disabled = true;
        const originalText = btn.innerHTML;
        btn.innerHTML = '<span class="spinner"></span> لطفاً صبر کنید...';
        // بعد از 10 ثانیه برگردون (برای امنیت)
        setTimeout(() => {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }, 10000);
    }
});

// بستن منوی موبایل با کلیک روی لینک
document.querySelectorAll('.mobile-nav a').forEach(link => {
    link.addEventListener('click', () => {
        document.getElementById('mobileNav')?.classList.remove('open');
    });
});