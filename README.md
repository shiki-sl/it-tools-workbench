# SHIKI IT Tools 工作台

供 AMD 3600 上的私有工作台使用的轻量配置与发行包准备仓库。运行入口：<https://shiki-3600.tailaed862.ts.net/>。

前端使用 [sharevb/it-tools](https://github.com/sharevb/it-tools) 的官方静态发行包，本仓库没有分叉或修改上游应用源码。固定版本为 `v2026.9.27`，源码提交为 `fad759efda02bc5ccf145b86732e7434d44b4ece`。发行包地址和 SHA-256 见 [UPSTREAM.json](UPSTREAM.json)。

## 仓库范围

- `scripts/prepare_release.py`：核验官方发行包和上游源码版本，检查精选工具名，生成工具筛选、中文默认语言、中文首页、外部登录入口与版本清单，并为静态文件生成 gzip/Brotli 副本。路径参数化于 2026-10-23，生成配置保持 2026-10-22 部署版本内容。
- `deploy/Caddyfile`：仅监听 `127.0.0.1:8086`，由现有 Tailscale Serve 提供 HTTPS；哈希资源长期缓存，普通配置不长期缓存，缺失资源返回 404，`/api/*` 返回 404。
- `deploy/it-tools.service`：系统级 Caddy 服务模板。3600 承载静态页面；认证能力在 9955HX 的独立服务中运行。

默认精选 67 个内置工具，加上一个指向 `https://shiki-9955hx.tailaed862.ts.net:8446/` 的外部登录态与 Token 入口。筛选仅影响工具导航，不是访问控制。上游通用工具可能把输入放入 URL 或浏览器存储，应按实际内容选择使用。

本仓库不包含发行包、生成后的静态站点、上游依赖、Caddy 二进制、备份、认证源码、账户配置、凭据、日志和上游 `.github` 工作流，也不配置自动发布或部署。

## 准备可复现的静态目录

需要已可用的 Python 3.9+、Git、Brotli CLI；准备过程只写本地输出目录，不访问业务接口、不安装服务、不修改 Tailscale 或线上目录。以下下载和源码检出需网络；不需要 Node/pnpm 或重做上游构建。

```sh
mkdir -p downloads upstream
curl -fL --retry 2 \
  https://github.com/sharevb/it-tools/releases/download/v2026.9.27/it-tools-2026.9.27.zip \
  -o downloads/it-tools-2026.9.27.zip
git clone --branch v2026.9.27 --depth 1 https://github.com/sharevb/it-tools.git upstream/it-tools
python3 scripts/prepare_release.py
```

脚本核验 ZIP SHA-256 为 `2482048fb024c24a87d9a37d8bc2e0799548e74b8f75fddb656f54fa3153814a`，同时要求上游检出提交匹配且 `src/tools` 无工作区改动。默认生成 `generated/2026.9.27-20261022/`：其中 `dist/` 为可服务的站点，`release.json` 记录来源和工具清单，`compression.json` 记录预压缩统计。已有输出目录会拒绝覆盖。

可复用其他位置的只读输入，或指定独立输出：

```sh
python3 scripts/prepare_release.py \
  --archive /path/to/it-tools-2026.9.27.zip \
  --source /path/to/unchanged-it-tools-checkout \
  --output /path/to/new-release-directory
```

完整对应源码可通过上述 Git 检出获得，也可从 [固定提交源码包](https://github.com/sharevb/it-tools/archive/fad759efda02bc5ccf145b86732e7434d44b4ece.tar.gz) 取得；准备脚本校验工具名时要求使用 Git 检出。

## 服务约定与人工更新边界

3600 当前约定为 `/srv/it-tools/current/dist`，Caddy 为 `/srv/it-tools/bin/caddy`，配置为 `/srv/it-tools/config/Caddyfile`，系统服务为 `it-tools.service`。`current` 指向独立版本目录，上一版本保留以便回退。Caddy 2.11.7 与 Tailscale 是运行时环境依赖，不随本仓库下载或安装。

原有 `install_3600.py` 是 2026-10-22 的一次性 root 安装脚本，绑定了具体节点身份、空 Serve 路由和“无已有部署”的前置条件，不能用于现有服务升级；本仓库不收录该脚本。升级时需要单独核验目标、备份现有配置与 Serve 状态、检查新目录及 HTTP 响应，再由获授权的执行者切换 `current`；本仓库的准备脚本不会执行这些线上操作。更改生成的 JSON/Markdown 后须同步更新对应 `.br`/`.gz`，避免读取旧压缩内容。不得用 `tailscale serve reset` 清理单个入口。

只读状态检查示例（在已核实的 3600 上）：

```sh
systemctl status it-tools.service
systemctl is-enabled it-tools.service
tailscale serve status
curl -I https://shiki-3600.tailaed862.ts.net/
```

## 来源与许可

上游 IT Tools 由 Corentin Thomasset 及 sharevb/it-tools 贡献者维护，使用 GNU GPL v3；原始许可全文保留于 [LICENSE](LICENSE)。本仓库中的工作台定制与脚本于 2026-10-22/23 整理，按同一 GPL-3.0 许可提供；第三方代码和发行包保留其原有版权与许可。本仓库只保存配置和生成脚本，使用或分发生成的上游站点时应同时保留对应来源、许可和取得源码的方法。
