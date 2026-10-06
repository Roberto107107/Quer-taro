"use strict";
document.addEventListener("DOMContentLoaded", () => {
    const viewer = document.getElementById('image-viewer');
    if (viewer && typeof viewer.showModal === 'function') {
        const fullImage = viewer.querySelector('img');
        let opener;
        document.querySelectorAll('[data-expand-image]').forEach(link => {
            link.addEventListener('click', event => {
                if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
                event.preventDefault();
                opener = link;
                fullImage.src = link.href;
                fullImage.alt = link.closest('figure').querySelector('img').alt;
                viewer.showModal();
                document.body.classList.add('image-viewer-open');
            });
        });
        viewer.querySelector('[data-close-image]').addEventListener('click', () => viewer.close());
        viewer.addEventListener('click', event => {
            const bounds = viewer.getBoundingClientRect();
            if (event.target === viewer && (event.clientX < bounds.left || event.clientX > bounds.right ||
                event.clientY < bounds.top || event.clientY > bounds.bottom)) viewer.close();
        });
        viewer.addEventListener('close', () => {
            document.body.classList.remove('image-viewer-open');
            fullImage.removeAttribute('src');
            opener?.focus();
        });
    }
    const imageInput = document.getElementById('imagen');
    const imagePreview = document.getElementById('imagen-preview');
    if (imageInput && imagePreview) {
        let previewUrl;
        imageInput.addEventListener('change', () => {
            if (previewUrl) URL.revokeObjectURL(previewUrl);
            imagePreview.hidden = true;
            imagePreview.removeAttribute('src');
            imageInput.setCustomValidity('');
            const file = imageInput.files[0];
            if (!file) return;
            if (!['image/jpeg','image/png','image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024) {
                imageInput.setCustomValidity('Selecciona un JPG, PNG o WebP de hasta 5 MB.');
                imageInput.reportValidity();
                return;
            }
            imageInput.setCustomValidity('');
            previewUrl = URL.createObjectURL(file);
            imagePreview.src = previewUrl;
            imagePreview.hidden = false;
        });
    }
    const createMenu = document.querySelector('.create-menu');
    if (createMenu) {
        document.addEventListener('click', event => {
            if (!createMenu.contains(event.target)) createMenu.open = false;
        });
        document.addEventListener('keydown', event => {
            if (event.key === 'Escape' && createMenu.open) {
                createMenu.open = false;
                createMenu.querySelector('summary').focus();
            }
        });
    }
    const date = document.getElementById("adminCurrentDate");
    if (date) date.textContent = new Date().toLocaleDateString("es-MX", {dateStyle: "long"});
    document.querySelectorAll("form[data-confirm]").forEach(form => {
        form.addEventListener("submit", event => {
            if (!window.confirm(form.dataset.confirm)) event.preventDefault();
        });
    });
});
