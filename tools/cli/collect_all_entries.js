
// 豆瓣音乐条目收集脚本
// 收集所有条目到 localStorage，然后导出到 Python 进行比较

(async function collectAllEntries() {
    const BASE_URL = 'https://music.douban.com/people/63343218/collect?sort=time&start=';
    const DELAY_MS = 1000;
    
    console.log('=== 开始收集所有条目 ===');
    
    // 初始化
    let allData = [];
    let processedPages = [];
    
    // 从 URL 获取当前页
    const urlParams = new URLSearchParams(window.location.search);
    let currentStart = parseInt(urlParams.get('start') || '0');
    let currentPage = Math.floor(currentStart / 15);
    
    console.log('从第', currentPage + 1, '页开始');
    
    // 主循环
    for (let page = currentPage; page < 433; page++) {
        const start = page * 15;
        const url = BASE_URL + start;
        
        // 导航
        window.location.href = url;
        await new Promise(resolve => setTimeout(resolve, DELAY_MS));
        
        // 收集
        const items = [];
        const links = document.querySelectorAll('a[href*="/subject/"]');
        
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
        
        // 保存
        const existingIds = new Set(allData.map(i => i.subject_id));
        const newItems = items.filter(i => !existingIds.has(i.subject_id));
        allData.push(...newItems);
        processedPages.push(page);
        
        // 每 10 页保存一次
        if ((page + 1) % 10 === 0) {
            localStorage.setItem('douban_collect_data', JSON.stringify({
                items: allData,
                pages: processedPages
            }));
            console.log(`Page ${page + 1}/433 - 累计：${allData.length}, 唯一：${new Set(allData.map(i => i.subject_id)).size}`);
        }
    }
    
    // 最终保存
    localStorage.setItem('douban_collect_data', JSON.stringify({
        items: allData,
        pages: processedPages
    }));
    
    const uniqueIds = new Set(allData.map(i => i.subject_id));
    console.log('
=== 收集完成 ===');
    console.log('总条目:', allData.length);
    console.log('唯一 ID:', uniqueIds.size);
    console.log('数据已保存到 localStorage: douban_collect_data');
    
    return { total: allData.length, unique: uniqueIds.size };
})();
