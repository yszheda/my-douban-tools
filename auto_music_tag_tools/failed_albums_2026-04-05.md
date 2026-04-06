# 豆瓣音乐批量处理 - 失败专辑记录

**日期：** 2026-04-05
**处理批次：** 50 个专辑
**成功：** 19 专辑
**失败：** 29 专辑
**跳过：** 2 专辑

---

## 失败原因分类

### 1. 缺少艺术家信息（"请提供表演者"）
大部分失败是因为专辑信息文件中缺少艺术家（artist）字段，导致豆瓣创建表单验证失败。

**受影响的专辑（共 27 个）：**
- [1/50] Leoš Janáček - Osud... (barcode: 401179038412)
- [5/50] Lukas Geniušas - 16th International Chopin... (缺少搜索条件)
- [7/50] Maria Gambaryan - Russian Piano School... (缺少搜索条件)
- [11/50] Mikhail Voskresensky - Alexander Scriabin... (缺少搜索条件)
- [12/50] Russian Piano Music, Volume 1: Shostakovich... (barcode: 09730)
- [13/50] Nikita Magaloff - Last Recital in Tokyo 1991... (barcode: 4988062041298)
- [19/50] Anton Bruckner - Symphony No. 3 in D minor... (缺少搜索条件)
- [20/50] Giacomo Puccini - La Bohème (1955 Live Recording)... (缺少搜索条件)
- [21/50] Richard Strauss - Der Rosenkavalier (1949 Recording)... (缺少搜索条件)
- [22/50] Richard Strauss - The Last Concerts 1947-1949... (缺少搜索条件)
- [23/50] Chopin - Concertos pour piano / 肖邦 - 第一、二钢琴协奏曲... (barcode: 044007689942)
- [25/50] 跳过 (barcode 4 本次已处理)
- [26/50] 跳过 (barcode 4 本次已处理)
- [27/50] The Great Opera Singers (EMI 6CD) - 成功创建但没有封面
- [28/50] Scriabin And The Scriabinians (Harmonia Mundi) - 成功创建但没有封面
- [29/50] Sviatoslav Richter & Vassili Lobanov - Britten, Bartok, Stravinsky... - 成功创建
- [30/50] Sviatoslav Richter in Budapest - The Concert of 9 February 1958... (缺少搜索条件)
- [31/50] Tchaikovsky - Eugene Onegin - Lemeshev... (缺少搜索条件)
- [32/50] Teresa Berganza - Eighteenth-Century Portraits (Decca 2CD) - 成功创建
- [33/50] The World of Operetta - Franz Lehar (Teldec) - 成功创建
- [34/50] Three Tenors of the Opéra-Comique - Louis Cazette... (缺少搜索条件)
- [35/50] Vaclav Talich - Smetana Ma Vlast 1954 (Naxos) - 成功创建
- [36/50] Vladimir Nielsen - Schumann, Mendelssohn, Medtner and Ravel (Northern Flowers) - 成功创建
- [37/50] Sergey Taneyev - String Trio in E-flat minor... (缺少搜索条件)
- [38/50] Rachmaninov Preludes Plus piano sonatas... (barcode: BBCMM415)
- [48/50] Tito Schipa - The Romance of Spain (Pearl) (barcode: 727031918325)
- [49/50] Leoš Janáček - Sinfonietta Op.60 / Violin Sonata... (barcode: 743213048123)
- [50/50] Bedřich Smetana - Má Vlast (My Country)... (barcode: 747313323722)

### 2. 成功创建的专辑（6 个）
- [2/50] Lehar - Das Land des Lächelns (Auszüge) - di Stefano... (nuid=1628920)
- [3/50] Les Introuvables du Chant Wagnerien - Wagner Singing on Record (EMI 4CD) (nuid=1628923)
- [6/50] Maria Callas - Puccini Heroines and Lyric Soprano Arias (nuid=1628924) - 无封面
- [17/50] Mozart - Le Nozze di Figaro (1958 Live Recording)... (nuid=1628927)
- [24/50] Arias and Duets (咏叹调与二重唱) (nuid=1628935) - 无封面
- [39/50] Britten • Bartók • Stravinsky / Works for 2 Pianos (nuid=1628930)

---

## 建议修复措施

1. **检查专辑信息文件** - 确保每个专辑目录中的 `专辑基本信息.md` 文件包含 `artist` 字段
2. **批量修复** - 对于缺少艺术家的专辑，可以从目录名中提取艺术家信息
3. **手动处理** - 对于特别珍贵的录音，建议手动在豆瓣上创建条目

---

## 已更新记录文件

- `processed_barcodes.txt`: 106 → 135 个记录 (+29)
- `processed_dirs.log`: 56 → 104 个记录 (+48)
