
function collectCurrentPageIds() {
    const links = document.querySelectorAll('a[href*="/subject/"]');
    const ids = new Set();
    const items = [];
    
    links.forEach(link => {
        const match = link.href.match(/\/subject\/(\d+)\//);
        if (match) {
            const id = match[1];
            if (!ids.has(id)) {
                ids.add(id);
                // 获取标题
                const card = link.closest('.item') || link.closest('[data-Subject-id]');
                let title = '';
                if (card) {
                    const titleEl = card.querySelector('.title');
                    if (titleEl) title = titleEl.textContent.trim();
                }
                items.push({ subject_id: id, title: title.substring(0, 100) });
            }
        }
    });
    
    // 获取当前页码
    const urlParams = new URLSearchParams(window.location.search);
    const start = parseInt(urlParams.get('start') || '0');
    const page = Math.floor(start / 15);
    
    // 保存到 localStorage
    const allData = JSON.parse(localStorage.getItem('douban_collected_data') || '{"items": [], "pages": []}');
    
    if (!allData.pages.includes(page)) {
        allData.pages.push(page);
        allData.items.push(...items);
        localStorage.setItem('douban_collected_data', JSON.stringify(allData));
    }
    
    return {
        page: page + 1,
        start: start,
        itemsFound: items.length,
        totalPages: allData.pages.length,
        totalItems: allData.items.length,
        uniqueIds: new Set(allData.items.map(i => i.subject_id)).size
    };
}

// 运行
collectCurrentPageIds();
