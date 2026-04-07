
// 收集当前页面所有条目
function collectPage() {
    const links = document.querySelectorAll('a[href*="/subject/"]');
    const items = [];
    
    links.forEach(link => {
        const match = link.href.match(/\/subject\/(\d+)\//);
        if (match) {
            const id = match[1];
            if (!items.find(i => i.subject_id === id)) {
                const card = link.closest('.item');
                let title = '';
                if (card) {
                    const titleEl = card.querySelector('.title');
                    if (titleEl) title = titleEl.textContent.trim().replace(/\s+/g, ' ');
                }
                items.push({ subject_id: id, title: title });
            }
        }
    });
    
    return items;
}

// 获取页码
function getPageInfo() {
    const urlParams = new URLSearchParams(window.location.search);
    const start = parseInt(urlParams.get('start') || '0');
    return { start, page: Math.floor(start / 15) + 1 };
}

// 累积保存
function save(items) {
    let allData = JSON.parse(localStorage.getItem('douban_all_collect') || '[]');
    const { page, start } = getPageInfo();
    
    // 去重
    const existingIds = new Set(allData.map(i => i.subject_id));
    const newItems = items.filter(i => !existingIds.has(i.subject_id));
    
    allData.push(...newItems);
    localStorage.setItem('douban_all_collect', JSON.stringify(allData));
    
    return {
        page: page,
        start: start,
        itemsThisPage: items.length,
        newItems: newItems.length,
        totalItems: allData.length,
        uniqueItems: new Set(allData.map(i => i.subject_id)).size
    };
}

// 主流程
const items = collectPage();
const stats = save(items);
console.log('Page', stats.page, '- new:', stats.newItems, '- unique:', stats.uniqueItems);
return stats;
