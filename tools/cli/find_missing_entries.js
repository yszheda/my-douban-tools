// 豆瓣音乐缺失条目查找脚本
// 使用方法：在浏览器控制台运行此脚本，或通过 MCP DevTools 注入

(async function findMissingEntries() {
    const EXPORTED_IDS_STORAGE_KEY = 'douban_exported_collect_ids';
    const RESULTS_STORAGE_KEY = 'douban_missing_results';
    const BATCH_SIZE = 50; // 每批处理的页数
    const DELAY_MS = 500; // 页间延迟

    // 从 localStorage 读取已导出的 ID
    function getExportedIds() {
        const stored = localStorage.getItem(EXPORTED_IDS_STORAGE_KEY);
        return stored ? new Set(JSON.parse(stored)) : new Set();
    }

    // 提取当前页面的所有 subject_id
    function extractSubjectIdsFromPage() {
        const links = document.querySelectorAll('a[href*="/subject/"]');
        const ids = new Set();
        links.forEach(link => {
            const match = link.href.match(/\/subject\/(\d+)\//);
            if (match) {
                ids.add(match[1]);
            }
        });
        return Array.from(ids);
    }

    // 导航到指定页面并收集 ID
    async function navigateAndCollect(startIndex) {
        const url = `https://music.douban.com/people/63343218/collect?sort=time&scaleall=f&mode=grid&start=${startIndex}`;
        window.location.href = url;

        return new Promise((resolve) => {
            setTimeout(() => {
                resolve(extractSubjectIdsFromPage());
            }, 2000); // 等待页面加载
        });
    }

    // 获取总页数
    function getTotalPages() {
        const pagination = document.querySelector('.paginator');
        if (pagination) {
            const pages = pagination.querySelectorAll('a[href*="start="]');
            let maxPage = 1;
            pages.forEach(page => {
                const match = page.href.match(/start=(\d+)/);
                if (match) {
                    const pageNum = parseInt(match[1]) / 15 + 1;
                    maxPage = Math.max(maxPage, pageNum);
                }
            });
            return maxPage;
        }
        return 433; // 默认值
    }

    // 主循环
    async function run() {
        console.log('=== 豆瓣音乐缺失条目查找工具 ===');
        console.log('开始收集所有条目...');

        const exportedIds = getExportedIds();
        console.log(`已导出 ID 数量：${exportedIds.size}`);

        const allFoundIds = new Set();
        const missingIds = [];
        let currentPage = 0;
        let totalMissing = 0;

        // 从 URL 获取当前页码
        const urlParams = new URLSearchParams(window.location.search);
        const startParam = parseInt(urlParams.get('start') || '0');
        const startPage = Math.floor(startParam / 15);

        console.log(`从第 ${startPage + 1} 页开始（start=${startParam}）`);

        for (let page = startPage; page < 433; page++) {
            const startIndex = page * 15;
            const ids = await navigateAndCollect(startIndex);

            // 找出缺失的 ID
            const newMissing = ids.filter(id => !exportedIds.has(id));

            if (newMissing.length > 0) {
                missingIds.push(...newMissing.map(id => ({
                    subject_id: id,
                    found_on_page: page + 1,
                    start_index: startIndex
                })));
                totalMissing += newMissing.length;
                console.log(`[第${page + 1}页] 发现 ${newMissing.length} 个缺失条目，累计缺失：${totalMissing}`);
            }

            allFoundIds.add(...ids);
            currentPage = page;

            // 每 10 页报告一次进度
            if ((page + 1) % 10 === 0) {
                console.log(`[进度] 已处理 ${page + 1}/433 页，累计发现 ${totalMissing} 个缺失条目`);

                // 保存中间结果
                localStorage.setItem(RESULTS_STORAGE_KEY, JSON.stringify({
                    progress_page: page + 1,
                    missing_count: totalMissing,
                    missing_entries: missingIds
                }));
            }

            // 检查是否还有下一页
            const nextLink = document.querySelector('a[href*="start="][rel="next"]');
            if (!nextLink && page > 430) {
                console.log('已到达最后一页');
                break;
            }
        }

        // 最终结果
        const results = {
            completed_at: new Date().toISOString(),
            total_pages_processed: currentPage + 1,
            total_exported: exportedIds.size,
            total_found_on_douban: allFoundIds.size,
            total_missing: missingIds.length,
            missing_entries: missingIds
        };

        localStorage.setItem(RESULTS_STORAGE_KEY, JSON.stringify(results));
        console.log('=== 完成 ===');
        console.log(`缺失条目总数：${missingIds.length}`);
        console.log('结果已保存到 localStorage:', RESULTS_STORAGE_KEY);
        console.log('运行以下命令获取结果：');
        console.log(`JSON.parse(localStorage.getItem('${RESULTS_STORAGE_KEY}'))`);

        return results;
    }

    return await run();
})();
