// 豆瓣音乐缺失条目查找工具 v2
// 使用方法：在浏览器控制台运行此脚本
// 脚本会自动逐页导航并收集所有条目，找出缺失的条目

(async function findMissingEntries() {
    console.log('=== 豆瓣音乐缺失条目查找工具 ===');
    console.log('此脚本将自动收集所有 433 页的条目并找出缺失的条目');

    // 配置
    const CONFIG = {
        delayMs: 1000,           // 页间延迟（毫秒）
        batchSize: 433,          // 每批处理页数
        userId: '63343218',      // 用户 ID
        storageKey: 'douban_missing_finder_v2'
    };

    // 已导出的 ID 列表（从 album_list_full.json 生成）
    // 为了减少脚本大小，我们在运行时从 localStorage 读取
    // 首次运行时需要在 Python 中生成并注入

    const EXPORTED_IDS_STORAGE = 'douban_exported_ids';
    let exportedIds = new Set(JSON.parse(localStorage.getItem(EXPORTED_IDS_STORAGE) || '[]'));

    if (exportedIds.size === 0) {
        console.warn('警告：未找到已导出 ID，需要在 Python 中生成并注入');
        console.log('运行以下 Python 命令生成注入脚本：');
        console.log('python -c "import json; ids=[e[\'subject_id\'] for e in json.load(open(\'album_list_full.json\'))[\'collections\'][\'collect\']]; print(f\'localStorage.setItem(\\\"douban_exported_ids\\\", JSON.stringify({json.dumps(ids)}))\')"');
    }

    console.log('已导出 ID 数量:', exportedIds.size);

    // 加载或初始化状态
    let state = JSON.parse(localStorage.getItem(CONFIG.storageKey) || '{"items":[],"pages":[],"missing":[]}');
    if (!state.items) state.items = [];
    if (!state.pages) state.pages = [];
    if (!state.missing) state.missing = [];

    console.log('已收集条目:', state.items.length);
    console.log('已找到缺失条目:', state.missing.length);

    // 找到起始页
    const processedSet = new Set(state.pages);
    let startPage = 0;
    for (let p = 0; p < 433; p++) {
        if (!processedSet.has(p)) {
            startPage = p;
            break;
        }
    }

    console.log('从第', startPage + 1, '页开始');
    console.log('输入 stopMissing() 可以随时停止');

    // 停止标志
    let shouldStop = false;
    window.stopMissing = () => {
        shouldStop = true;
        console.log('已设置停止标志，当前页完成后停止');
    };

    // 保存状态
    function saveState() {
        localStorage.setItem(CONFIG.storageKey, JSON.stringify(state));
    }

    // 主循环
    for (let page = startPage; page < 433 && !shouldStop; page++) {
        const start = page * 15;
        const url = `https://music.douban.com/people/${CONFIG.userId}/collect?sort=time&start=${start}&mode=grid`;

        // 导航
        window.location.href = url;

        // 等待页面加载
        await new Promise(resolve => setTimeout(resolve, CONFIG.delayMs));

        // 收集当前页面条目
        const items = [];
        const links = document.querySelectorAll('a[href*="/subject/"]');

        links.forEach(link => {
            const match = link.href.match(/\/subject\/(\d+)\//);
            if (match) {
                const id = match[1];
                if (!items.find(x => x.subject_id === id)) {
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
        const existingIds = new Set(state.items.map(x => x.subject_id));
        const newItems = items.filter(x => !existingIds.has(x.subject_id));
        if (newItems.length > 0) state.items.push(...newItems);

        // 找出缺失的条目
        if (exportedIds.size > 0) {
            const missing = items.filter(item => !exportedIds.has(item.subject_id));
            if (missing.length > 0) {
                state.missing.push(...missing);
                console.log(`Page ${page + 1}/433 - 缺失：${missing.length}, 累计缺失：${state.missing.length}`);
            }
        }

        state.pages.push(page);

        // 每 10 页保存一次
        if ((page + 1) % 10 === 0) {
            saveState();
        }

        const uniqueCollected = new Set(state.items.map(x => x.subject_id)).size;
        const uniqueMissing = new Set(state.missing.map(x => x.subject_id)).size;

        if ((page + 1) % 10 === 0 || missing?.length > 0) {
            console.log(`Page ${page + 1}/433 - 收集唯一:${uniqueCollected}, 缺失唯一:${uniqueMissing}`);
        }
    }

    // 最终保存
    saveState();

    const uniqueCollected = new Set(state.items.map(x => x.subject_id)).size;
    const uniqueMissing = new Set(state.missing.map(x => x.subject_id)).size;

    console.log('\n=== 收集完成 ===');
    console.log('总收集条目:', state.items.length);
    console.log('收集唯一 ID:', uniqueCollected);
    console.log('缺失条目数:', state.missing.length);
    console.log('缺失唯一 ID:', uniqueMissing);
    console.log('处理页数:', state.pages.length);
    console.log('\n数据已保存到 localStorage:', CONFIG.storageKey);
    console.log('\n导出命令：');
    console.log(`JSON.parse(localStorage.getItem('${CONFIG.storageKey}'))`);
    console.log(`JSON.stringify(localStorage.getItem('${CONFIG.storageKey}'))`);

    return {
        totalCollected: state.items.length,
        uniqueCollected: uniqueCollected,
        missingCount: state.missing.length,
        uniqueMissing: uniqueMissing,
        pagesProcessed: state.pages.length
    };
})();
