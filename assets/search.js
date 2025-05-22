document.getElementById('search-input').addEventListener('input', function(event) {
    const searchTerm = event.target.value.toLowerCase();
    const listItems = document.querySelectorAll('.ipk-list li');
    
    listItems.forEach(function(item) {
        const linkText = item.textContent.toLowerCase();
        if (linkText.includes(searchTerm)) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
});

function showPlugins(platform) {
    const pluginList = document.getElementById('plugin-list');
    pluginList.innerHTML = ''; // 清空插件列表

    // 加载相应平台的插件
    fetch(`opkg/${platform}/`)
        .then(response => response.json())
        .then(plugins => {
            plugins.forEach(plugin => {
                const li = document.createElement('li');
                const link = document.createElement('a');
                link.href = plugin.url;
                link.textContent = plugin.name;
                li.appendChild(link);
                pluginList.appendChild(li);
            });
        })
        .catch(error => {
            console.error('Error loading plugins:', error);
        });
}

