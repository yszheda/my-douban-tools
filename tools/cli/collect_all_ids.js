
(async function collectAllIds() {
    const ALL_IDS_KEY = 'douban_all_collect_ids';
    let allIds = JSON.parse(localStorage.getItem(ALL_IDS_KEY) || '[]');
    const processedPages = new Set(JSON.parse(localStorage.getItem('douban_processed_pages') || '[]'));
    
    // 从指定页码开始
    const urlParams = new URLSearchParams(window.location.search);
    let start = parseInt(urlParams.get('start') || '0');
    let page = Math.floor(start / 15);
    
    // 如果是新会话，重置
    if (page === 0 && processedPages.size > 100) {
        allIds = [];
        processedPages.clear();
    }
    
    // 提取当前页面的 ID
    function extractIds() {
        const links = document.querySelectorAll('a[href*="/subject/"]');
        const ids = new Set();
        links.forEach(link => {
            const match = link.href.match(/\/subject\/(\d+)\//);
            if (match) ids.add(match[1]);
        });
        return Array.from(ids);
    }
    
    // 导航到下一页
    function nextPage() {
        const nextStart = start + 15;
        if (nextStart > 7000) return null; // 安全限制
        
        const url = new URL(window.location.href);
        url.searchParams.set('start', nextStart);
        window.location.href = url.toString();
        
        return nextStart;
    }
    
    // 收集当前页
    const currentIds = extractIds();
    console.log(`Page ${page + 1} (start=${start}): found ${currentIds.length} items`);
    
    allIds.push(...currentIds);
    processedPages.add(page);
    
    // 保存到 localStorage
    localStorage.setItem(ALL_IDS_KEY, JSON.stringify(allIds));
    localStorage.setItem('douban_processed_pages', JSON.stringify([...processedPages]));
    
    return {
        page: page + 1,
        idsThisPage: currentIds.length,
        totalIdsCollected: allIds.length,
        uniqueIds: new Set(allIds).size,
        processedPages: processedPages.size
    };
})();
