import os
import sys
import time
import requests
from github import Github, Auth

# ================= 配置 =================
GH_TOKEN = os.environ.get("GH_TOKEN")
XMIND_COOKIE = os.environ.get("XMIND_COOKIE")
XMIND_FWT = os.environ.get("XMIND_FWT") # 新增：必须的环境变量
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")

# XMind 国内版 API
XMIND_LIST_API = "https://app.xmind.cn/api/drive/list-folder"
BACKUP_DIR = "xmind_backup/"

def main():
    if not GH_TOKEN or not XMIND_COOKIE or not XMIND_FWT:
        print("❌ 错误: 缺少环境变量 GH_TOKEN, XMIND_COOKIE 或 XMIND_FWT")
        sys.exit(1)
        
    print(f"🚀 启动备份任务，仓库: {REPO_NAME}")

    # 1. 连接 GitHub (修复了之前的 DeprecationWarning)
    auth = Auth.Token(GH_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(REPO_NAME)

    # 2. 准备国内版的请求头和载荷(Payload)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Cookie": XMIND_COOKIE,
        "fwt": XMIND_FWT  # 核心身份令牌
    }
    
    # 你刚才抓到的载荷数据
    payload = {
        "folderId": "_xmind_CfoeIoGlZY",
        "limit": 100,
        "order": "desc",
        "sortBy": "modifiedTime",
        "teamOrMyWorksId": "_xmind_CfoeIoGlZY",
        "type": "file"
    }

    # 3. 获取文件列表 (改用 POST 请求)
    print("☁️ 正在请求 XMind 国内版接口...")
    try:
        resp = requests.post(XMIND_LIST_API, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        
        # 提取文件列表，兼容不同的数据结构
        files = []
        if isinstance(data, list):
            files = data
        elif isinstance(data, dict):
            files = data.get('data', {}).get('files', []) if 'files' in str(data) else data.get('items', [])
            if not files and 'data' in data and isinstance(data['data'], list):
                files = data['data']
                
    except Exception as e:
        print(f"❌ 获取列表失败: {e}")
        print(f"服务器返回: {resp.text if 'resp' in locals() else '未知'}")
        sys.exit(1)

    print(f"✅ 找到 {len(files)} 个文件/文件夹")

    # 4. 遍历下载并上传
    for idx, item in enumerate(files):
        # 如果是文件夹则跳过（type 通常为 folder 或 file）
        if item.get('type') == 'folder':
            continue
            
        name = item.get('name', f'untitled_{idx}')
        if not name.endswith('.xmind'): 
            name += '.xmind'
            
        file_id = item.get('id')
        print(f"⬇️ [{idx+1}/{len(files)}] 下载: {name}")
        
        # 尝试国内版可能的下载链接格式
        download_url = item.get('downloadUrl')
        if not download_url:
            download_url = f"https://app.xmind.cn/api/drive/file/{file_id}/download"
            
        try:
            down_resp = requests.get(download_url, headers=headers)
            if down_resp.status_code != 200:
                print(f"   └── ❌ 下载失败 (状态码: {down_resp.status_code})")
                continue
                
            content = down_resp.content
            file_path = f"{BACKUP_DIR}{name}"
            
            try:
                contents = repo.get_contents(file_path)
                repo.update_file(contents.path, f"Update {name}", content, contents.sha)
                print(f"   └── ✅ 更新成功")
            except Exception as e:
                if getattr(e, 'status', 0) == 404:
                    repo.create_file(file_path, f"Add {name}", content)
                    print(f"   └── ✨ 新建成功")
                else:
                    print(f"   └── ⚠️ GitHub 同步错误: {e}")
                    
        except Exception as e:
            print(f"   └── ⚠️ 失败: {e}")
        
        time.sleep(2)

if __name__ == "__main__":
    main()
