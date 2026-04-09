document.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const text = this.closest('.border').querySelector('pre').innerText;
        navigator.clipboard.writeText(text).then(() => {
            alert('复制成功');
        });
    });
});