function searchPackages() {
    const query = document.getElementById('search').value.toLowerCase();
    const links = document.querySelectorAll('.ipk-list li a');
    
    links.forEach(link => {
        const text = link.textContent.toLowerCase();
        if (text.includes(query)) {
            link.parentElement.style.display = 'block'; // 显示匹配的条目
        } else {
            link.parentElement.style.display = 'none'; // 隐藏不匹配的条目
        }
    });
}
