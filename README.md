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

生产构建（本地 Node）：

```bash
npm run build
NODE_ENV=production npm start
```

## Vercel 部署

在线部署目标：**Vercel**（通过 GitHub 连接）。

### 架构（Vercel）

| 本地 (`npm run dev`) | Vercel |
|----------------------|--------|
| Vite + Express (`better-sqlite3`) | 静态 `dist/` + Serverless `/api/*` |
| Express rate-limit | Serverless 内存限流（同文案 429） |
| `data/food.db` 只读 | 同库打进函数包（`sql.js` WASM，无原生绑定） |

前端模式（长辈 / 儿童 / 成人）与 Web Speech 仍在浏览器端，无需改动。

### 一键步骤

1. 将本仓库推到 GitHub（需 `GH_TOKEN` 或本机 `gh auth login`）。
2. [vercel.com/new](https://vercel.com/new) → Import 该 GitHub 仓库。
3. Framework Preset: **Vite**；Build `npm run build`；Output `dist`（已写在 `vercel.json`）。
4. Deploy。上线后打开 `https://<project>.vercel.app`。

CLI（已登录 Vercel 时）：

```bash
npx vercel --yes
npx vercel --prod --yes
```

配置文件：`vercel.json`（SPA rewrite、API `includeFiles` 打包 `data/food.db` + `sql.js` wasm）。

### 限流说明（Vercel）

Serverless 实例内存限流为 **尽力而为**（冷启动会重置计数）。文案与本地一致：`每分钟只能使用五次，超出了五次，等下一分钟再开始`。若需跨实例严格 5 次/分钟，可后续接 Upstash Redis。

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

限流：**5 次 / 分钟 / IP**（本地 Express；Vercel Serverless 内存桶）。

## 技术栈

- Frontend: Vite + React + TypeScript
- Local API: Express + better-sqlite3
- Vercel API: Serverless Functions + sql.js（只读 SQLite）
- Data: Python (requests / pandas)

## License

数据版权归各公开成分表发布方；本仓库代码 MIT。
