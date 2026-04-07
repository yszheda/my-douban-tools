
import json

# 读取收集的数据
with open('all_collected.json', 'r', encoding='utf-8') as f:
    collected = json.load(f)

# 读取已导出的数据
with open('album_list_full.json', 'r', encoding='utf-8') as f:
    exported = json.load(f)

collected_ids = set(i['subject_id'] for i in collected['items'])
exported_ids = set(e['subject_id'] for e in exported['collections']['collect'])

print(f"收集的条目数：{len(collected_ids)}")
print(f"已导出的条目数：{len(exported_ids)}")

# 找出缺失的
missing_in_exported = collected_ids - exported_ids
missing_in_collected = exported_ids - collected_ids

print(f"
在收集数据中但不在已导出数据中的：{len(missing_in_exported)}")
print(f"在已导出数据中但不在收集数据中的：{len(missing_in_collected)}")

# 保存缺失条目
if missing_in_exported:
    missing_items = [i for i in collected['items'] if i['subject_id'] in missing_in_exported]
    with open('missing_entries.json', 'w', encoding='utf-8') as f:
        json.dump(missing_items, f, ensure_ascii=False, indent=2)
    print(f"
缺失条目已保存到 missing_entries.json")
