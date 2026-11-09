# 001 生产 Skill 单行安装

时间：2026-11-09（Asia/Shanghai）

## Context
用户批准现有生产 skill 放入生产 MinIO，下载失败用 GitHub 保底；提供一行命令给 Codex，源码打包延期。

## Strategy
skill正文与平台根skill.md一致，固定版本和SHA256；安装器从平台公开固定下载入口读取私有MinIO对象，失败切固定GitHub commit。GitHub提供固定版本安装脚本入口。现有不同技能停止，相同版本幂等；不使用管理员权限、sudo或平台凭据。

## Changes
- shiyanhui-platform/SKILL.md：同步当前已授权生产备用入口，其余保持现有正文。
- install.sh：下载、超时、大小/摘要校验、安装及本地修改保护。
- tests/test_install.py：真实curl+本地HTTP夹具验证8条路径。
- AGENTS.md/.gitignore：维护约定及测试缓存排除。

## Ref
See 平台根 prompt_log.md 2026-11-09 ### 11；tasks/115-customer-skill-distribution-2026-11-09.md。

## Backlogs
- [x] 8项安装测试、bash语法、skill校验通过。
- [x] 生产MinIO对象与固定GitHub正文SHA256一致，原模板与桶策略不变。
- [x] 真实GitHub兜底安装到隔离CODEX_HOME通过。
- [ ] GitHub PR创建需已登录会话或API凭据，当前只有SSH推送授权。
- [ ] 平台后端/按钮发布需生产镜像交互导入。
