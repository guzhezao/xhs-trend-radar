# 环境自检

抓取动作全部通过 MiniMax Code 的 `browser` 工具完成，不需要安装 Playwright 或平台 SDK。
最终报告由 Python 3 标准库脚本 `build-report.py` 生成。这个文件是 `SKILL.md` 第 0 节的展开说明。

**两道检查，都不能跳：A 验工具、B 验登录态。**

## 检查 A：工具能力

```
browser({ action: "navigate", input: { url: "https://www.xiaohongshu.com/explore" } })
browser({ action: "inspect" })
```

**必须先 navigate 再 inspect。** 空白页的 `inspect` 也会正常返回 `snapshotId`，
单独跑一次裸 `inspect` 只能证明"工具存在"，证明不了任何页面状态——那是无效自检。

### 通过标准

返回结果同时满足：

- 含 `snapshotId` 字段
- 元素句柄是不透明 ref（不是 CSS selector 字符串）
- 支持后续用 `snapshotId` + `offset` 续读分页

### 不通过时的输出

原样告知用户，不要尝试降级到 `web_fetch` 或建议装 Playwright：

> 本 skill 需要 MiniMax Code 的内置浏览器（保留登录态 + opaque ref 快照）。
> 当前环境不满足，无法运行。请在 MiniMax Code 中执行。

## 检查 B：登录态（每次开抓前必做）

工具可用 ≠ 能抓到东西。在检查 A 打开的页面上判断登录态：

| 观察到 | 结论 |
|---|---|
| 登录按钮 / 扫码弹层 / 搜索框 placeholder 为「登录探索更多内容」 | **未登录** |
| 正常笔记卡片列表，无登录引导 | 已登录，可以开抓 |

未登录的完整表现（实测 2026-07-29）：

```
HTTP 200，页面结构完整
__INITIAL_STATE__.search.feeds          → []
__INITIAL_STATE__.global.hasWebSession  → false
#global                                  → data-logged="0"
搜索框 placeholder                       → "登录探索更多内容"
```

处理：**停下**，让用户在右侧浏览器完成登录后再继续。

> 右侧浏览器当前未登录小红书。请在右侧面板登录后告诉我，我再继续。
> （未登录时小红书返回 200 + 空笔记数组，不会报错，硬跑会交付空清单。）

**不要换关键词重试，不要输出"该词下没有高赞内容"，也不要"先试试看能不能拿到"。**

## 为什么不做降级

降级方案实测都不成立：

- `web_fetch` 抓搜索页 → **HTTP 200 但 `feeds` 是空数组**，
  静默失败，脚本会误判成功
- headless 浏览器 → 同上，无登录态就没有笔记数据
- CSS selector 定位 → Vue scoped 属性 + 构建 hash，每次发版都变

给一个"能跑但结果是错的"流程，比明确报错更糟。
尤其是这个平台的失败方式是静默的，错误结果长得跟正确结果一模一样。
