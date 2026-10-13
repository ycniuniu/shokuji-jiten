# 食事事典 / Food Nutrition Encyclopedia

Vite + React + Express + SQLite 多国食物成分检索应用。

项目目录名：`food-nutrition`（英文 slug）。界面文案以中文为主。

## 功能

- 搜索 / 列表：大图、名称、kcal/100g
- 详情弹窗：营养表 + **常见份量**按克数换算（以每 100 g 为基准）
- 点击食物名称 → Web Speech API（`zh-CN`、慢速、高音量）；**长辈模式**默认开启语音
- API 限流：每分钟 5 次；超出返回 429，前端提示：
  `每分钟只能使用五次，超出了五次，等下一分钟再开始`
- 三种模式：
  - **长辈**：大字、高对比、语音优先
  - **儿童**：圆角软彩、卡通占位、游戏化营养小贴士
  - **成人**：完整营养表

视觉：New Yorker 杂志风 — Playfair Display 标题、系统无衬线正文、黑白 + 一点红、大留白、轻阴影；无渐变 / 无玻璃拟态。

## 快速开始

```bash
cd food-nutrition
npm install

# 1) 下载多国原始数据（部分源可能被墙/需人工，失败会写入 data/source_status.json）
npm run download:data

# 2) 规范化并生成 SQLite
npm run build:db

# 3) 生成 logo / Food-101 匹配图（若尚未生成）
python3 data/scripts/make_logo.py
python3 data/scripts/fetch_images.py

# 4) 同时启动 API (3001) + Vite (5173)
npm run dev
```

打开 http://localhost:5173

生产构建：

```bash
npm run build
NODE_ENV=production npm start
```

## 数据管线

| 脚本 | 作用 |
|------|------|
| `data/scripts/download_sources.py` | 下载 CN/JP/KR/SG/US/UK/FR/DE 原始数据到 `data/raw/` |
| `data/scripts/build_db.py` | 归一化 → `data/food.db`，匹配 Food-101 图片路径与常见份量 |
| `data/scripts/fetch_images.py` | 写入 `public/images/*.jpg` |
| `data/scripts/make_logo.py` | 生成 `public/logo.png` |

统一字段：名称、来源国、分类、kcal/100g、蛋白质/脂肪/碳水、钠、Ca/Fe/Zn/Se、维生素、常见份量。

缺源时会记录到 `data/source_status.json`。仓库已包含可用的 `data/food.db`（约 2.1 万条）。

### 数据源与装载结果（v1）

| 国家 | 来源 | 条数 | 备注 |
|------|------|------|------|
| CN | [china-food-composition-data](https://github.com/Sanotsu/china-food-composition-data) `json_data_v3` | ~1654 | 完整 |
| JP | MEXT 八訂 JSON（katoharu432 GitHub） | ~2478 | 完整 |
| KR | foodsafetykorea Excel | 5 | 门户需人工；用 curated sample |
| SG | HPB SG FoodID | 5 | 无 bulk API；用 curated sample |
| US | USDA FDC Foundation + SR Legacy（截断） | ~4234 | SR Legacy 取前 4000 |
| UK | CoFID 2021 xlsx（GOV.UK） | ~2884 | CoFID API 曾离线 |
| FR | ANSES Ciqual 2020 XLS | ~3185 | data.gouv / anses.fr |
| DE | BLS 4.0（blsdb.de） | ~7140 | 官方 zip |

合计约 **21,585** 条（去重后）。

Python 依赖：`pip install -r data/scripts/requirements.txt`

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查（不限流） |
| GET | `/api/foods?q=&limit=&offset=` | 搜索（限流） |
| GET | `/api/foods/:id` | 详情（限流） |
| GET | `/api/stats` | 按国家统计（限流） |

限流：`express-rate-limit`，**5 次 / 分钟 / IP**。

## 技术栈

- Frontend: Vite + React + TypeScript
- Backend: Express + better-sqlite3
- Data: Python (requests / pandas)

## License

数据版权归各公开成分表发布方；本仓库代码 MIT。
