// 豆瓣收藏列表快速导出脚本 - 增强版
// 使用方法：在浏览器控制台运行 doubanExporter.autoExportAll()

(function() {
    const USER_ID = '63343218';
    const ITEMS_PER_PAGE = 30;
    const DELAY_BETWEEN_PAGES = 2000; // 2 秒延迟，避免反爬

    async function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async function fetchPage(type, start) {
        const url = `https://music.douban.com/people/${USER_ID}/${type}?start=${start}&mode=list`;
        console.log(`  导航到：${url}`);
        window.location.href = url;
        await sleep(2500); // 等待页面加载

        const links = Array.from(document.querySelectorAll('a[href*="/subject/"]'))
            .filter(a => !a.href.includes('/people/'))
            .map(a => {
                const match = a.href.match(/\/subject\/(\d+)\//);
                return { subject_id: match ? match[1] : null, title: a.title || a.textContent.trim() };
            })
            .filter(x => x.subject_id);

        const seen = new Set();
        const unique = links.filter(x => { if (seen.has(x.subject_id)) return false; seen.add(x.subject_id); return true; });
        const hasNext = Array.from(document.querySelectorAll('a')).some(a => a.textContent.includes('后页'));

        return { entries: unique, hasNext, count: unique.length };
    }

    async function fetchAll(type) {
        console.log(`[开始] 导出 ${type}...`);
        const allEntries = [];
        let start = 0, page = 1;

        while (true) {
            console.log(`[进度] ${type} 第${page}页 - 累计${allEntries.length}条`);
            const result = await fetchPage(type, start);
            if (result.count === 0) break;
            allEntries.push(...result.entries);
            if (!result.hasNext) break;
            start += ITEMS_PER_PAGE;
            page++;
            await sleep(DELAY_BETWEEN_PAGES);
        }

        console.log(`[完成] ${type} 共${allEntries.length}条`);
        return allEntries;
    }

    async function autoExportAll() {
        console.log('='.repeat(60));
        console.log('豆瓣音乐收藏列表自动导出');
        console.log('='.repeat(60));
        console.log(`用户：${USER_ID}`);
        console.log(`开始：${new Date().toISOString()}`);

        const results = {};
        for (const type of ['collect', 'do', 'wish']) {
            results[type] = await fetchAll(type);
        }

        const output = {
            exported_at: new Date().toISOString(),
            user_id: USER_ID,
            stats: {
                collect: results.collect.length,
                do: results.do.length,
                wish: results.wish.length,
                total: results.collect.length + results.do.length + results.wish.length
            },
            collections: results
        };

        console.log('='.repeat(60));
        console.log('导出完成!');
        console.log(`collect: ${results.collect.length} 条`);
        console.log(`do: ${results.do.length} 条`);
        console.log(`wish: ${results.wish.length} 条`);
        console.log(`总计：${output.stats.total} 条`);
        console.log('='.repeat(60));

        window.exportResult = output;
        return output;
    }

    function downloadResult() {
        if (!window.exportResult) {
            console.log('请先运行 autoExportAll()');
            return;
        }
        const blob = new Blob([JSON.stringify(window.exportResult, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `album_list_${USER_ID}_${new Date().toISOString().slice(0,10)}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        console.log('文件已下载');
    }

    // 支持从指定位置继续导出
    async function autoExportFrom(type, startPage) {
        console.log(`[续跑] 从 ${type} 第${startPage}页开始导出`);
        const result = await fetchAll(type);
        return result;
    }

    window.doubanExporter = { autoExportAll, autoExportFrom, downloadResult };
    console.log('导出工具已加载');
    console.log('运行 doubanExporter.autoExportAll() 开始完整导出');
    console.log('运行 doubanExporter.downloadResult() 下载结果');
})();
