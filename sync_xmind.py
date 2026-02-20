import os
import sys
import time
import requests
from github import Github, Auth

# ================= 配置 =================
GH_TOKEN = os.environ.get("GH_TOKEN")
XMIND_COOKIE = os.environ.get("XMIND_COOKIE")
XMIND_FWT = os.environ.get("XMIND_FWT")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")

XMIND_LIST_API = "https://app.xmind.cn/api/drive/list-folder"
BACKUP_DIR = "xmind_backup/"

def main():
    if not GH_TOKEN or not XMIND_COOKIE or not XMIND_FWT:
        print("❌ 错误: 缺少环境变量")
        sys.exit(1)
        
    print(f"🚀 启动备份任务，仓库: {REPO_NAME}")

    auth = Auth.Token(GH_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(REPO_NAME)

    # 🛡️ 核心修复 1：补全防盗链和身份特征 Headers，完美伪装成浏览器
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Cookie": XMIND_COOKIE,
        "fwt": XMIND_FWT,
        "Referer": "https://app.xmind.cn/home/my-works",
        "x-app-identity": "flatwhite"
    }
    
    payload = {
        "folderId": "_xmind_CfoeIoGlZY",
        "limit": 100,
        "order": "desc",
        "sortBy": "modifiedTime",
        "teamOrMyWorksId": "_xmind_CfoeIoGlZY",
        "type": "file"
    }

    print("☁️ 正在请求 XMind 国内版接口...")
    try:
        resp = requests.post(XMIND_LIST_API, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        
        files = []
        if isinstance(data, list): files = data
        elif isinstance(data, dict):
            files = data.get('data', {}).get('files', []) if 'files' in str(data) else data.get('items', [])
            if not files and 'data' in data and isinstance(data['data'], list):
                files = data['data']
    except Exception as e:
        print(f"❌ 获取列表失败: {e}")
        sys.exit(1)

    print(f"✅ 找到 {len(files)} 个文件/文件夹")

    for idx, item in enumerate(files):
        if item.get('type') == 'folder': continue
            
        name = item.get('name', f'untitled_{idx}')
        if not name.endswith('.xmind'): name += '.xmind'
            
        file_id = item.get('id')
        print(f"⬇️ [{idx+1}/{len(files)}] 下载: {name}")
        
        download_url = f"https://app.xmind.cn/api/drive/file/{file_id}/download"
            
        try:
            # 请求下载接口
            link_resp = requests.get(download_url, headers=headers, allow_redirects=False)
            
            down_resp = None
            
            # 🛡️ 核心修复 2：智能处理服务器的各种放行方式
            if link_resp.status_code == 200:
                if "application/json" in link_resp.headers.get("Content-Type", ""):
                    res_data = link_resp.json()
                    real_url = res_data.get('url') or res_data.get('data', {}).get('url') or res_data.get('downloadUrl')
                    if real_url:
                        down_resp = requests.get(real_url)
                    else:
                        print(f"   └── ❌ JSON 中找不到下载链接: {res_data}")
                        continue
                else:
                    down_resp = link_resp
                    
            elif link_resp.status_code in [301, 302, 303, 307, 308]:
                real_url = link_resp.headers.get('Location')
                down_resp = requests.get(real_url)
                
            else:
                print(f"   └── ❌ 获取链接失败 (状态码: {link_resp.status_code}, 服务器原话: {link_resp.text[:100]})")
                continue
                
            if not down_resp or down_resp.status_code != 200:
                status = down_resp.status_code if down_resp else 'Unknown'
                print(f"   └── ❌ 文件下载失败 (状态码: {status})")
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
