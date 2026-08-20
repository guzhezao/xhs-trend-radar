# 报告生成：只填数据，不碰 HTML

本 skill 的交付物是一份**单文件 HTML 报告**。样式、三张图表、点击跳转逻辑
**全部已经写死在 `assets/report-shell.html` 里**，你不需要、也不许自己写 HTML/CSS/JS。

**你唯一要做的事：产出一个符合下面结构的 JSON 数据文件，然后跑一条拼装命令。**

上一版失败的教训：模型从零手写 SVG 图表，调试了几十轮还渲染不出、没有交互、不能点击。
根因就是"让模型写 HTML"。现在图表逻辑它看不到也不用写——**发挥空间为零，就不会翻车。**

---

## 1. 三步生成

```text
# 第 1 步：抓取时，进度就存成符合 REPORT_DATA 结构的 JSON（见第 2 节）
#          文件名建议 xhs-trend-<关键词>-<YYYYMMDD>.data.json

# 第 2 步：跑跨平台拼装脚本（Python 3，仅用标准库）
python <skill目录>/scripts/build-report.py <你的data.json路径> <输出报告.html路径>

# 第 3 步：用 <media type="file" src="<报告.html绝对路径>" /> 交付给用户
```

`build-report.py` 做的事：校验数据，再把 `assets/chart.umd.min.js`（Chart.js 库，已内联）+
`assets/report-shell.html`（骨架）+ 你的数据，拼成一个**不依赖网络、双击就能开、图表能点**的单文件 HTML。

**不许绕过脚本自己拼 HTML。** 脚本会校验 JSON 合法性，非法直接报错——这是防呆。

---

## 2. REPORT_DATA 数据结构（照着填）

这就是 data.json 的完整结构。抓取过程中逐条往 `notes` 数组里 append，最后补顶层字段。

```json
{
  "keyword": "AI 工作台",
  "captured_at": "2026-07-30 16:55",
  "range": "近 1 个月",
  "range_days": 30,
  "sort_note": "搜索结果页综合排序前 30 条 → 按点赞重排取前 10",
  "account": "AI 工具测评",
  "target": 10,
  "lede": "一段导语 HTML，可用 <b> 加粗。讲清现在什么在火、为什么（见第 3 节）",
  "kpi": {
    "max_like": 12483,
    "max_like_note": "《标题》",
    "max_sl_ratio": "0.74",
    "max_sl_note": "第 01 条 · 实用信号最强",
    "newest_days": 4,
    "newest_note": "《标题》",
    "window_open": 5
  },
  "drive_dist": { "practical": 4, "info": 2, "emotion": 2, "unknown": 2 },
  "groups": {
    "now":  ["现在就做的条目（标题+序号）"],
    "plan": ["排期做的条目"],
    "ref":  "只做参考的条目，一段话说明"
  },
  "notes": [
    {
      "status": "verified",
      "title": "笔记标题原文",
      "author": "作者昵称",
      "publish_date": "2026-07-24",
      "days_ago": 6,
      "like": 12483,
      "save": 9207,
      "comment": 731,
      "tags": ["AI工具", "效率", "周报"],
      "url": "https://www.xiaohongshu.com/explore/<note_id>?xsec_token=<token>&xsec_source=pc_search",
      "judge": {
        "stage": "窗口开着",
        "drive": "实用（藏/赞 0.74）",
        "barrier": "可直接做",
        "relevance": "强相关"
      },
      "suggestion": "做不做，切什么角度"
    },
    {
      "status": "failed",
      "title": "打不开的那条标题",
      "author": "作者",
      "like": 3205,
      "fail_reason": "详情页 3 次打开均超时",
      "judge": {}
    }
  ],
  "footer": {}
}
```

### 字段规则（硬）

| 字段 | 谁必填 | 说明 |
|---|---|---|
| `status` | 每条 | `"verified"`（详情页打开成功）或 `"failed"`（兜底） |
| `like/save/comment` | verified 条必填 | `failed` 条只有 `like`（搜索页卡片有）；`save/comment` 省略，模板自动显示"未获取"、图表自动留 `null` 缺口 |
| `days_ago` | verified 条必填 | 距今天数，散点图靠它定位；缺了这条画不进散点 |
| `url` | verified 条必填 | 必须带 `xsec_token`，从搜索页卡片 href 原样取（见 SKILL.md 第 5 节）|
| `fail_reason` | failed 条必填 | 写清楚打开失败几次、什么原因；没试过就不算 failed |
| `judge` 四项 | 有数据才填 | 缺数据留空字符串或省略，模板自动填"未获取"，**不许猜** |

### KPI 四格只放事实（不放验证率）

- `max_like` / `max_sl_ratio` / `newest_days` / `window_open` 全部从 verified 数据算出来
- `max_sl_ratio`（最高藏赞比）**没有藏的数据就算不出来** —— 算不出说明详情页没打开够，回去补
- **验证率不进 KPI**，它在页脚由模板自动算（`target` - verified 条数 = 兜底条数）

---

## 3. 导语 `lede` 怎么写

一段 2-3 句人话，把结论说完，用户只看这段也能拿到判断。必须含三个带数字的要素：

1. 热度集中在什么类型（由 `drive_dist` 得出）
2. 窗口状态（`X / Y 条窗口仍开着`）
3. 互动结构说明什么（藏赞比中位数 / 评论最高那条在争什么）

参考：

> 「AI 工作台」当前热度集中在**可直接抄走的模板类干货**：8 条已验证笔记里 5 条窗口仍开着，
> 藏赞比中位数 **0.58**（偏收藏型），说明用户是**存起来照着做**。评论量最高的是横评类（02），
> 争议点在**付费值不值**。

`lede` 里可以直接写 `<b>` 加粗，模板原样渲染。

---

## 4. 图表和交互（已写死，了解即可，不用你做）

模板里三张图全部用内联的 Chart.js 渲染，**点击图表元素会 `window.open` 对应笔记链接**：

| 图 | 类型 | 数据来源 | 交互 |
|---|---|---|---|
| 赞/藏/评对比 | 柱状 | 每条的 like/save/comment | 点柱子跳该笔记 |
| 发布新鲜度 × 互动 | 散点 | verified 条的 days_ago + like | 点气泡跳该笔记，越右越新 |
| 驱动力分布 | 环形 | `drive_dist` 四个数 | —— |

- 兜底条目的 `save/comment` 是 `null`，柱状图上留**空缺口**，肉眼可见数据缺失
- 驱动力图的 `unknown` 那块是**灰色扇区**，兜底条目都计入这里

这些你都不用写。你只要把数字填对，图自然就对。填错了图会画歪——所以**数字必须来自真实抓取**。

---

## 5. 自检（生成后打开确认）

1. `build-report.py` 跑通且没有数据校验错误
2. 浏览器打开报告，三张图都显示了（不是空白）
3. 点一下柱子，能跳到对应笔记详情页（不是 404）
4. 兜底条目在柱状图上是缺口、在明细里是灰卡片
5. KPI 四格是事实结论，没有验证率
6. 已用 `<media type="file" />` 交付

第 2 条空白 = Chart.js 没加载（正常不会，库是内联的）；第 3 条跳 404 = url 少了 xsec_token。
