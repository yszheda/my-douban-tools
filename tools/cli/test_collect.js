
// 清除旧数据
localStorage.removeItem('douban_collected_data');
console.log('已清除旧数据');

// 收集当前页面
const links = document.querySelectorAll('a[href*="/subject/"]');
const items = [];

links.forEach(link => {
    const match = link.href.match(/\/subject\/(\d+)\//);
    if (match) {
        const id = match[1];
        const card = link.closest('.item');
        let title = '';
        if (card) {
            const titleEl = card.querySelector('.title');
            if (titleEl) title = titleEl.textContent.trim().replace(/\s+/g, ' ');
        }
        items.push({ subject_id: id, title: title.substring(0, 100) });
    }
});

console.log('当前页面条目:', items.length);
console.log(items);

// 保存到 localStorage
localStorage.setItem('douban_current_page', JSON.stringify(items));
return items;
