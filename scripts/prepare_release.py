#!/usr/bin/env python3
"""Prepare pinned upstream assets and SHIKI configuration; never deploy services.

SHIKI customization, 2026-10-22; portable path handling, 2026-10-23.
Distributed under GPL-3.0; see the repository LICENSE and UPSTREAM.json.
"""
import argparse
import concurrent.futures
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

BASE = Path(__file__).resolve().parent.parent
SOURCE_COMMIT = 'fad759efda02bc5ccf145b86732e7434d44b4ece'
EXPECTED = '2482048fb024c24a87d9a37d8bc2e0799548e74b8f75fddb656f54fa3153814a'
RELEASE_NAME = '2026.9.27-20261022'
TOOLS = '''json-prettify json-minify json-linter json-editor json-diff json-query
json-escaper json-flatten-nestify json-to-java json-to-yaml-converter json-to-xml
json-to-csv csv-to-json json-to-typescript base64-string-converter base64-file-converter
url-encoder url-parser url-builder jwt-parser jwt-generator regex-tester date-converter
timezone-converter date-duration-calculator cron-expression-builder crontab-generator
sql-prettify sql-minifier sql-parameters text-diff markdown-preview markdown-to-html
markdown-table-generator yaml-prettify yaml-to-json-converter xml-formatter xml-to-json
properties-converter env-variables-converter hash-text file-hasher hmac-generator
uuid-generator ulid-generator token-generator bcrypt certificate-key-parser http-status-codes
mime-types curl-converter user-agent-parser html-entities case-converter text-statistics
list-converter list-comparer duplicate-line-finder string-escaper unicode-to-java-entities
chmod-calculator ipv4-subnet-calculator base-converter data-storage-unit-converter
docker-run-to-docker-compose-converter docker-compose-validator docker-compose-to-env-file'''.split()


def compress(path):
    raw = path.read_bytes()
    gz = gzip.compress(raw, compresslevel=6, mtime=0)
    if len(gz) < len(raw):
        path.with_name(path.name + '.gz').write_bytes(gz)
    result = subprocess.run(['brotli', '-q', '6', '-c', str(path)], check=True, capture_output=True)
    if len(result.stdout) < len(raw):
        path.with_name(path.name + '.br').write_bytes(result.stdout)
    return len(raw), len(gz), len(result.stdout)


def validate_tools(source):
    commit = subprocess.run(
        ['git', '-C', str(source), 'rev-parse', 'HEAD'],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    if commit != SOURCE_COMMIT:
        raise SystemExit(f'Expected upstream commit {SOURCE_COMMIT}, got {commit}')
    if subprocess.run(
        ['git', '-C', str(source), 'status', '--porcelain', '--', 'src/tools'],
        check=True, capture_output=True, text=True,
    ).stdout:
        raise SystemExit('Upstream src/tools must be unchanged')
    known = set()
    for path in (source / 'src/tools').glob('*/index.ts'):
        match = re.search(r'''path:\s*['"]([^'"]+)''', path.read_text())
        if match:
            known.add(match[1].lstrip('/'))
    assert set(TOOLS) <= known, set(TOOLS) - known
    assert len(TOOLS) == len(set(TOOLS))


def write_configuration(release):
    dist = release / 'dist'
    selected = TOOLS + ['ccxi-login']
    filter_config = {
        'includeToolsFilterRegex': '^/(' + '|'.join(re.escape(name) for name in selected) + ')$',
        'excludeToolsFilterRegex': '.*',
    }
    (dist / 'tools-filter.json').write_text(json.dumps(filter_config, indent=2) + '\n')
    (dist / 'tools-settings.json').write_text('{"default_locale":"zh"}\n')
    external = [{
        'name': 'CCXI 登录态与 Token',
        'path': '/ccxi-login',
        'description': '由 9955HX 执行。查看测试/预发认证缓存，显式获取 Token；不执行业务请求。',
        'keywords': ['ccxi', 'login', 'token', '登录态', '认证', '9955HX'],
        'category': 'Development',
        'href': 'https://shiki-9955hx.tailaed862.ts.net:8446/',
    }]
    (dist / 'external-tools.json').write_text(json.dumps(external, ensure_ascii=False, indent=2) + '\n')
    (dist / 'home.custom.md').write_text('''## 开发工作台

为日常 Java / Web 开发精选常用工具。通用转换在当前浏览器中处理。

[JSON](/json-prettify) · [Base64](/base64-string-converter) · [URL](/url-encoder) · [JWT](/jwt-parser) · [正则](/regex-tester) · [时间](/date-converter) · [SQL](/sql-prettify) · [Diff](/text-diff)

[CCXI 登录态与 Token · 执行设备 9955HX](https://shiki-9955hx.tailaed862.ts.net:8446/)

登录能力需要 9955HX 在线，并具备有效认证缓存和企业网络条件；3600 只托管工具箱。上游通用工具可能将输入保存在 URL 或浏览器本地，请按实际内容选择使用。
''')
    metadata = {
        'upstream': 'sharevb/it-tools', 'version': 'v2026.9.27',
        'source_commit': SOURCE_COMMIT,
        'upstream_zip_sha256': EXPECTED, 'release': RELEASE_NAME,
        'builtin_tools': TOOLS, 'external_tools': ['ccxi-login'],
        'default_tool_count': len(selected), 'hidden_builtins': 474 - len(TOOLS),
        'filtering_is_access_control': False,
    }
    (release / 'release.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, default=BASE / 'downloads/it-tools-2026.9.27.zip')
    parser.add_argument('--source', type=Path, default=BASE / 'upstream/it-tools')
    parser.add_argument('--output', type=Path, default=BASE / 'generated' / RELEASE_NAME)
    args = parser.parse_args()
    release = args.output.resolve()
    if hashlib.sha256(args.archive.read_bytes()).hexdigest() != EXPECTED:
        raise SystemExit('Upstream archive SHA-256 mismatch')
    if release.exists():
        raise SystemExit(f'Refusing to overwrite existing release: {release}')
    validate_tools(args.source)
    with zipfile.ZipFile(args.archive) as archive:
        for info in archive.infolist():
            if not (release / info.filename).resolve().is_relative_to(release):
                raise SystemExit(f'Unsafe archive member: {info.filename}')
        archive.extractall(release)
    write_configuration(release)
    dist = release / 'dist'
    paths = [p for p in dist.rglob('*') if p.is_file() and p.suffix in {'.js', '.css', '.wasm', '.json', '.html', '.svg', '.xml', '.txt'} and p.stat().st_size > 512]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        sizes = list(pool.map(compress, paths))
    summary = dict(zip(['identity_bytes', 'gzip_bytes', 'brotli_bytes'], map(sum, zip(*sizes))))
    summary.update({'files': len(paths), 'default_tools': len(TOOLS) + 1, 'release': str(release)})
    (release / 'compression.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
