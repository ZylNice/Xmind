import os
import sys
import time
import requests
from github import Github, GithubException

# ================= 配置 =================
# 1. 从环境变量获取敏感信息 (GitHub Actions 会自动注入这些变量)
# 注意：如果在本地运行，需要你自己手动设置这些环境变量，或者暂时改回写死的方式
GH_TOKEN = os.environ.get("GH_TOKEN")
XMIND_COOKIE = os.environ.get("XMIND_COOKIE")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY") # GitHub Actions 会自动提供 "用户名/仓库名"

# 2. 其他配置
XMIND_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Cookie": XMIND_COOKIE
}
XMIND_LIST_API = "https://xmind.works/api/v2/files?limit=1000"
BACKUP_DIR = "xmind_backup/"  # 备份到仓库的哪个目录

def main():
    # 检查环境变量是否存在
    if not GH_TOKEN or not XMIND_COOKIE:
        print("❌ 错误: 缺少环境变量 GH_TOKEN 或 XMIND_COOKIE")
        sys.exit(1)
        
    print(f"🚀 启动备份任务，仓库: {REPO_NAME}")

    # 1. 连接 GitHub
    g = Github(GH_TOKEN)
    repo = g.get_repo(REPO_NAME)

    # 2. 获取 XMind 文件列表
    print("☁️ 正在获取 XMind 云端列表...")
    try:
        resp = requests.get(XMIND_LIST_API, headers=XMIND_HEADERS)
        resp.raise_for_status()
        files = resp.json()
        # 兼容处理：如果返回的是字典且包含 items
        if isinstance(files, dict) and 'items' in files:
            files = files['items']
    except Exception as e:
        print(f"❌ 获取列表失败: {e}")
        sys.exit(1)

    print(f"✅ 找到 {len(files)} 个文件")

    # 3. 遍历下载并上传
    for idx, item in enumerate(files):
        name = item.get('name', f'untitled_{idx}')
        if not name.endswith('.xmind'): name += '.xmind'
        
        # 获取下载链接
        file_id = item.get('id')
        # 优先用 API 返回的 url，没有则尝试拼接
        download_url = item.get('downloadUrl') or f"https://xmind.works/api/v2/files/{file_id}/download"
        
        print(f"⬇️ [{idx+1}/{len(files)}] 下载: {name}")
        
        try:
            # 下载内容
            content = requests.get(download_url, headers=XMIND_HEADERS).content
            
            # 上传到 GitHub
            file_path = f"{BACKUP_DIR}{name}"
            
            try:
                # 尝试获取现有文件 hash (为了更新)
                contents = repo.get_contents(file_path)
                repo.update_file(contents.path, f"Update {name}", content, contents.sha)
                print(f"   └── ✅ 更新成功")
            except GithubException as e:
                if e.status == 404:
                    # 文件不存在，新建
                    repo.create_file(file_path, f"Add {name}", content)
                    print(f"   └── ✨ 新建成功")
                else:
                    raise e
                    
        except Exception as e:
            print(f"   └── ⚠️ 失败: {e}")
        
        # 稍微歇息，防止被 XMind 封 IP
        time.sleep(2)

if __name__ == "__main__":
    main()
