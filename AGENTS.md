# Skill 分发约定

- 仅分发当前生产 shiyanhui-platform/SKILL.md，不含源码或凭据。
- install.sh 使用固定 SHA256 与固定 GitHub commit，先读取平台固定 MinIO 下载入口，失败才切 GitHub；不使用 sudo、不登录平台、不覆盖已有不同技能。
- 修改安装器需运行 bash -n install.sh 与 python3 -m unittest discover -s tests -v；修改技能需同步固定版本/key/摘要及平台下载入口，不能仅更新一侧。
