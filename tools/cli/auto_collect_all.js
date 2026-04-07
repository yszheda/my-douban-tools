// 豆瓣音乐自动收集所有条目脚本
// 使用方法：在浏览器控制台运行此脚本，等待完成

(async function autoCollectAll() {
    const BASE_URL = 'https://music.douban.com/people/63343218/collect?sort=time&start=';
    const DELAY_MS = 1500; // 页间延迟（毫秒）
    const STOP_KEY = 'douban_collect_stop'; // 停止标志

    console.log('=== 豆瓣音乐条目收集工具 ===');
    console.log('开始收集所有条目...');

    // 初始化或加载已有数据
    let allData = JSON.parse(localStorage.getItem('douban_all_collect') || '[]');
    let processedPages = JSON.parse(localStorage.getItem('douban_processed_pages') || '[]');

    const startPage = processedPages.length > 0 ? Math.max(...processedPages) + 1 : 0;
    console.log(`从第 ${startPage + 1} 页开始`);
    console.log(`已收集条目：${allData.length}`);
    console.log(`已处理页数：${processedPages.length}`);

    // 检查是否需要停止
    function shouldStop() {
        return localStorage.getItem(STOP_KEY) === 'true';
    }

    // 清除停止标志
    localStorage.removeItem(STOP_KEY);
    console.log('输入 stopCollect() 可以随时停止收集');

    // 主循环
    for (let page = startPage; page < 433; page++) {
        if (shouldStop()) {
            console.log('\n用户请求停止，保存进度...');
            break;
        }

        const start = page * 15;
        const url = BASE_URL + start;

        // 导航到指定页面
        window.location.href = url;

        // 等待页面加载
        await new Promise(resolve => setTimeout(resolve, DELAY_MS));

        // 收集当前页面条目
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

        // 去重并保存
        const existingIds = new Set(allData.map(i => i.subject_id));
        const newItems = items.filter(i => !existingIds.has(i.subject_id));

        if (newItems.length > 0) {
            allData.push(...newItems);
            localStorage.setItem('douban_all_collect', JSON.stringify(allData));
        }

        processedPages.push(page);
        localStorage.setItem('douban_processed_pages', JSON.stringify(processedPages));

        console.log(`Page ${page + 1}/433 - 新增：${newItems.length}, 累计：${allData.length}, 唯一：${new Set(allData.map(i => i.subject_id)).size}`);
    }

    // 最终统计
    const uniqueIds = new Set(allData.map(i => i.subject_id));
    console.log('\n=== 收集完成 ===');
    console.log(`总条目数：${allData.length}`);
    console.log(`唯一条目数：${uniqueIds.size}`);
    console.log(`处理页数：${processedPages.length}`);
    console.log(`数据已保存到 localStorage: douban_all_collect`);
    console.log('\n运行以下命令导出数据：');
    console.log(`JSON.stringify(localStorage.getItem('douban_all_collect'))`);

    // 停止标志
    localStorage.setItem(STOP_KEY, 'false');

    return {
        totalItems: allData.length,
        uniqueItems: uniqueIds.size,
        pagesProcessed: processedPages.length
    };
})();

// 停止收集函数
function stopCollect() {
    localStorage.setItem('douban_collect_stop', 'true');
    console.log('已设置停止标志，收集将在当前页完成后停止');
}
