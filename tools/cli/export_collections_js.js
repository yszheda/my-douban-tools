// 豆瓣收藏列表导出脚本 - 浏览器控制台版
// 使用方法：在浏览器控制台中运行此脚本

(function() {
    const USER_ID = '63343218';
    const ITEMS_PER_PAGE = 30;

    async function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    async function fetchPage(type, start) {
        const url = `https://music.douban.com/people/${USER_ID}/${type}?start=${start}&mode=list`;
        window.location.href = url;
        await sleep(3000); // 等待页面加载

        const links = Array.from(document.querySelectorAll('a[href*="/subject/"]'))
            .filter(a => !a.href.includes('/people/'))
            .map(a => {
                const match = a.href.match(/\/subject\/(\d+)\//);
                return {
                    subject_id: match ? match[1] : null,
                    title: a.title || a.textContent.trim()
                };
            })
            .filter(x => x.subject_id);

        const seen = new Set();
        const unique = links.filter(x => {
            if (seen.has(x.subject_id)) return false;
            seen.add(x.subject_id);
            return true;
        });

        const hasNext = Array.from(document.querySelectorAll('a')).some(a => a.textContent.includes('后页'));

        return { entries: unique, hasNext, count: unique.length };
    }

    async function fetchAll(type) {
        console.log(`开始导出 ${type}...`);
        const allEntries = [];
        let start = 0;
        let page = 1;

        while (true) {
            console.log(`[进度] ${type} 第${page}页 - 累计${allEntries.length}条`);
            const result = await fetchPage(type, start);

            if (result.count === 0) {
                console.log(`[结束] ${type} 无更多条目`);
                break;
            }

            allEntries.push(...result.entries);

            if (!result.hasNext) {
                console.log(`[完成] ${type} 共${allEntries.length}条`);
                break;
            }

            start += ITEMS_PER_PAGE;
            page++;
            await sleep(2000);
        }

        return allEntries;
    }

    // 导出所有类型
    async function exportAll() {
        console.log('=' .repeat(60));
        console.log('豆瓣音乐收藏列表导出工具');
        console.log('=' .repeat(60));
        console.log(`用户：${USER_ID}`);
        console.log(`开始时间：${new Date().toISOString()}`);

        const results = {
            collect: await fetchAll('collect'),
            do: await fetchAll('do'),
            wish: await fetchAll('wish')
        };

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

        console.log('=' .repeat(60));
        console.log('导出完成!');
        console.log(`已听 (collect): ${results.collect.length}`);
        console.log(`在听 (do): ${results.do.length}`);
        console.log(`想听 (wish): ${results.wish.length}`);
        console.log(`总计：${output.stats.total}`);
        console.log('=' .repeat(60));
        console.log('结果已存储在 output 变量中');
        console.log('使用 JSON.stringify(output) 可以导出为 JSON');

        return output;
    }

    // 导出单个类型
    async function exportType(type) {
        const entries = await fetchAll(type);
        const output = {
            exported_at: new Date().toISOString(),
            user_id: USER_ID,
            type: type,
            total: entries.length,
            entries: entries
        };

        console.log(`${type} 完成：${entries.length}条`);
        console.log('结果已存储在 output 变量中');

        return output;
    }

    // 导出到 JSON 文件
    function downloadJSON(data, filename) {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // 导出所有并下载
    async function exportAndDownload() {
        const output = await exportAll();
        downloadJSON(output, `album_list_${USER_ID}.json`);
        console.log('文件已下载');
    }

    // 暴露到全局
    window.doubanExporter = {
        exportAll,
        exportType,
        exportAndDownload,
        downloadJSON,
        fetchAll,
        fetchPage
    };

    console.log('豆瓣导出工具已加载');
    console.log('使用方法:');
    console.log('  await doubanExporter.exportAll()       - 导出所有收藏');
    console.log('  await doubanExporter.exportType("collect") - 导出已听');
    console.log('  await doubanExporter.exportAndDownload() - 导出并下载 JSON');
    console.log('  await doubanExporter.downloadJSON(data, "filename.json") - 下载 JSON 文件');
})();
