#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPTV源自动更新脚本 - 适用于 GitHub Actions
从 FOFA 获取 udpxy 代理 IP，检测可用性并生成分类频道列表
"""

import os
import re
import sys
import json
import time
import base64
import socket
import requests
import concurrent.futures
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Set, Tuple, Optional
from collections import OrderedDict

# ===============================
# 配置区 - 使用 GitHub Secrets
# ===============================
FOFA_EMAIL = os.environ.get("FOFA_EMAIL", "")
FOFA_KEY = os.environ.get("FOFA_KEY", "")
FOFA_QUERY = os.environ.get("FOFA_QUERY", '"udpxy" && country="CN" && is_honeypot=false')
MAX_IPS_PER_FILE = int(os.environ.get("MAX_IPS_PER_FILE", "20"))  # 每个运营商文件最多IP数
TEST_TIMEOUT = int(os.environ.get("TEST_TIMEOUT", "5"))  # 检测超时(秒)
RUN_EVERY_N = int(os.environ.get("RUN_EVERY_N", "3"))  # 每N次运行执行完整检测

# 文件路径
COUNTER_FILE = "计数.txt"
IP_DIR = "ip"
RTP_DIR = "rtp"
ZUBO_FILE = "zubo.txt"
IPTV_FILE = "IPTV.txt"
CACHE_DIR = "cache"

# ===============================
# 频道分类配置
# ===============================
CHANNEL_CATEGORIES = {
    "央卫综艺": [
        "CCTV-1综合", "CCTV-2财经", "CCTV-3综艺", "CCTV-4中文国际", "CCTV-5体育",
        "CCTV-6电影", "CCTV-7国防军事", "CCTV-8电视剧", "CCTV-9纪录", "CCTV-10科教",
        "CCTV-11戏曲", "CCTV-12社会与法", "CCTV-13新闻", "CCTV-14少儿", "CCTV-15音乐",
        "CCTV-16奥林匹克", "CCTV-17农业农村", "CCTV-4K超高清", "CCTV-5+体育赛事",
        "湖南卫视", "浙江卫视", "江苏卫视", "东方卫视", "北京卫视", "广东卫视", "深圳卫视",
        "天津卫视", "山东卫视", "四川卫视", "重庆卫视", "辽宁卫视", "黑龙江卫视",
        "安徽卫视", "江西卫视", "湖北卫视", "湖南卫视", "河南卫视", "河北卫视",
        "云南卫视", "贵州卫视", "广西卫视", "陕西卫视", "甘肃卫视", "青海卫视",
        "宁夏卫视", "新疆卫视", "西藏卫视", "海南卫视", "东南卫视", "内蒙古卫视",
        "山西卫视", "吉林卫视", "凤凰卫视中文台", "凤凰卫视资讯台", "凤凰卫视香港台",
        "纪实科教", "大湾区卫视", "金鹰纪实", "环球旅游", "4K视界", "热门综艺",
        "兵器科技", "风云音乐", "风云足球", "风云剧场", "怀旧剧场", "第一剧场",
        "女性时尚", "世界地理", "央视台球", "高尔夫网球", "央视文化精品", "卫生健康",
        "电视指南", "中国交通", "中国天气", "茶频道", "梨园频道", "文物宝库", "法制天地",
        "书法频道", "国学频道", "爱宠宠物", "求索纪录", "求索科学", "求索生活", "求索动物",
        "中国教育1台", "中国教育2台", "中国教育3台", "中国教育4台", "早期教育",
        "山东教育卫视", "新视觉HD", "澳亚卫视", "广州竞赛"
    ],
    "影视剧院": [
        "CHC动作电影", "CHC家庭影院", "CHC影迷电影", "凤凰卫视电影台",
        "淘电影", "淘剧场", "淘4K", "淘娱乐", "淘萌宠", "重温经典",
        "峨眉电影", "峨眉电影4K", "星空卫视", "绚影4K", "CHANNEL[V]",
        "都市剧场", "欢笑剧场", "华数4K", "华数光影", "华数星影", "华数精选",
        "华数动作影院", "华数喜剧影院", "华数家庭影院", "华数经典电影",
        "华数热播剧场", "华数碟战剧场", "华数军旅剧场", "华数城市剧场",
        "华数武侠剧场", "华数古装剧场", "华数魅力时尚", "华数少儿动画",
        "BesTV-4K", "CBN每日影院", "CBN幸福娱乐", "CBN幸福剧场",
        "爱体育", "爱历史", "爱动漫", "爱喜剧", "爱奇谈", "爱幼教", "爱悬疑",
        "爱旅行", "爱浪漫", "爱玩具", "爱科幻", "爱谍战", "爱赛车", "爱院线",
        "爱探索", "爱青春", "爱怀旧", "爱经典", "爱都市", "爱家庭",
        "全球大片", "华语影院", "戏曲精选", "热门剧场", "精彩影视", "古早影院",
        "黑莓电影", "环球影视", "4K乐享超清"
    ],
    "少儿教育": [
        "乐龄学堂", "少儿天地", "动漫秀场", "淘BABY", "黑莓动画", "爱动漫",
        "睛彩青少", "金色学堂", "新动漫", "卡酷少儿", "金鹰卡通", "优漫卡通",
        "哈哈炫动", "嘉佳卡通", "亲子趣学", "爱幼教", "4K少儿", "百变课堂"
    ],
    "体育竞技": [
        "劲爆体育", "快乐垂钓", "四海钓鱼", "来钓鱼吧", "睛彩竞技", "睛彩篮球",
        "睛彩广场舞", "魅力足球", "五星体育", "游戏风云", "武术世界", "哒啵赛事",
        "哒啵电竞", "先锋乒羽", "天元围棋", "汽摩", "电竞天堂"
    ]
}

# ===============================
# 频道别名映射（将不同源的频道名统一为标准名）
# ===============================
CHANNEL_MAPPING = {
    "CCTV-1综合": ["CCTV-1", "CCTV-1 HD", "CCTV1 HD", "CCTV1", "CCTV1HD", "CCTV1综合"],
    "CCTV-2财经": ["CCTV-2", "CCTV-2 HD", "CCTV2 HD", "CCTV2", "CCTV2HD"],
    "CCTV-3综艺": ["CCTV-3", "CCTV-3 HD", "CCTV3 HD", "CCTV3", "CCTV3HD"],
    "CCTV-4中文国际": ["CCTV-4", "CCTV-4 HD", "CCTV4 HD", "CCTV4"],
    "CCTV-5体育": ["CCTV-5", "CCTV-5 HD", "CCTV5 HD", "CCTV5", "CCTV5HD"],
    "CCTV-5+体育赛事": ["CCTV-5+", "CCTV-5+ HD", "CCTV5+HD", "CCTV5+"],
    "CCTV-6电影": ["CCTV-6", "CCTV-6 HD", "CCTV6 HD", "CCTV6", "CCTV6HD"],
    "CCTV-7国防军事": ["CCTV-7", "CCTV-7 HD", "CCTV7 HD", "CCTV7"],
    "CCTV-8电视剧": ["CCTV-8", "CCTV-8 HD", "CCTV8 HD", "CCTV8", "CCTV8HD"],
    "CCTV-9纪录": ["CCTV-9", "CCTV-9 HD", "CCTV9 HD", "CCTV9", "CCTV9HD"],
    "CCTV-10科教": ["CCTV-10", "CCTV-10 HD", "CCTV10 HD", "CCTV10"],
    "CCTV-11戏曲": ["CCTV-11", "CCTV-11 HD", "CCTV11 HD", "CCTV11"],
    "CCTV-12社会与法": ["CCTV-12", "CCTV-12 HD", "CCTV12 HD", "CCTV12"],
    "CCTV-13新闻": ["CCTV-13", "CCTV-13 HD", "CCTV13 HD", "CCTV13"],
    "CCTV-14少儿": ["CCTV-14", "CCTV-14 HD", "CCTV14 HD", "CCTV14"],
    "CCTV-15音乐": ["CCTV-15", "CCTV-15 HD", "CCTV15 HD", "CCTV15"],
    "CCTV-16奥林匹克": ["CCTV-16", "CCTV-16 HD", "CCTV16", "CCTV-16奥林匹克4K"],
    "CCTV-17农业农村": ["CCTV-17", "CCTV-17 HD", "CCTV17", "CCTV17HD"],
    "CCTV-4K超高清": ["CCTV4K超高清", "CCTV4K", "CCTV-4K", "CCTV 4K"],
    "湖南卫视": ["湖南卫视HD", "湖南卫视高清", "HNTV", "湖南卫视"],
    "浙江卫视": ["浙江卫视HD", "浙江卫视高清", "ZJTV", "浙江卫视"],
    "江苏卫视": ["江苏卫视HD", "江苏卫视高清", "JSTV", "江苏卫视"],
    "东方卫视": ["东方卫视HD", "东方卫视高清", "DFTV", "上海卫视", "东方卫视"],
    "北京卫视": ["北京卫视HD", "北京卫视高清", "BTV", "北京卫视"],
    "广东卫视": ["广东卫视HD", "广东卫视高清", "GDTV", "广东卫视"],
    "深圳卫视": ["深圳卫视HD", "深圳卫视高清", "SZTV", "深圳卫视"],
    "凤凰卫视中文台": ["凤凰中文", "凤凰中文台", "凤凰卫视中文", "凤凰卫视"],
    "凤凰卫视资讯台": ["凤凰资讯", "凤凰资讯台", "凤凰卫视资讯"],
    "凤凰卫视香港台": ["凤凰香港台", "凤凰卫视香港", "凤凰香港"],
    "凤凰卫视电影台": ["凤凰电影", "凤凰电影台", "凤凰卫视电影"],
    "CHC动作电影": ["CHC-动作电影", "CHC动作电影HD"],
    "CHC家庭影院": ["CHC-家庭影院", "CHC家庭影院HD"],
    "CHC影迷电影": ["CHC-影迷电影", "CHC影迷电影HD", "影迷电影"],
    "重温经典": ["重温经典HD"],
    "劲爆体育": ["劲爆体育HD"],
    "快乐垂钓": ["快乐垂钓HD", "湖南快乐垂钓"],
    "四海钓鱼": ["四海钓鱼HD"],
    "游戏风云": ["游戏风云HD", "SiTV游戏风云"],
    "卡酷少儿": ["卡酷少儿HD", "北京卡酷少儿", "KAKU少儿"],
    "金鹰卡通": ["金鹰卡通HD", "湖南金鹰卡通"],
    "优漫卡通": ["优漫卡通HD", "江苏优漫卡通"],
    "哈哈炫动": ["哈哈炫动HD", "炫动卡通", "上海哈哈炫动"],
    "茶频道": ["茶频道HD", "湖南茶频道"],
    "梨园频道": ["梨园频道HD", "河南梨园频道"],
    "武术世界": ["武术世界HD", "河南武术世界"]
}

# ===============================
# 工具函数
# ===============================
def log(msg: str, level: str = "INFO"):
    """打印日志"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {msg}")

def get_run_count() -> int:
    """获取运行次数"""
    if os.path.exists(COUNTER_FILE):
        try:
            with open(COUNTER_FILE, "r", encoding="utf-8") as f:
                return int(f.read().strip() or "0")
        except Exception:
            return 0
    return 0

def save_run_count(count: int):
    """保存运行次数"""
    try:
        with open(COUNTER_FILE, "w", encoding="utf-8") as f:
            f.write(str(count))
    except Exception as e:
        log(f"保存计数失败: {e}", "ERROR")

# ===============================
# FOFA API 相关函数
# ===============================
def search_fofa_api(email: str, key: str, query: str, size: int = 100, page: int = 1) -> Tuple[List[str], int]:
    """通过FOFA API搜索数据"""
    if not email or not key:
        return [], 0
    
    qbase64 = base64.b64encode(query.encode('utf-8')).decode('utf-8')
    
    api_url = "https://fofa.info/api/v1/search/all"
    params = {
        'email': email,
        'key': key,
        'qbase64': qbase64,
        'size': min(size, 100),
        'page': page,
        'fields': 'host,ip,port'
    }
    
    try:
        response = requests.get(api_url, params=params, timeout=30)
        data = response.json()
        
        if data.get('error'):
            log(f"FOFA API错误: {data['error']}", "ERROR")
            return [], 0
        
        results = data.get('results', [])
        hosts = [item[0] for item in results if item and item[0]]
        
        return hosts, len(results)
        
    except requests.RequestException as e:
        log(f"FOFA API请求失败: {e}", "ERROR")
        return [], 0
    except Exception as e:
        log(f"FOFA API异常: {e}", "ERROR")
        return [], 0

def get_fofa_ips() -> List[str]:
    """从FOFA获取IP列表"""
    if not FOFA_EMAIL or not FOFA_KEY:
        log("未配置FOFA密钥，跳过FOFA获取", "WARNING")
        return []
    
    log(f"从FOFA获取数据: {FOFA_QUERY}")
    
    all_hosts = []
    page = 1
    max_pages = 3  # GitHub Actions 时间有限
    page_size = 100
    
    while page <= max_pages:
        hosts, count = search_fofa_api(FOFA_EMAIL, FOFA_KEY, FOFA_QUERY, page_size, page)
        
        if not hosts:
            break
        
        all_hosts.extend(hosts)
        log(f"第{page}页获取 {len(hosts)} 个地址")
        
        if count < page_size:
            break
        
        page += 1
        time.sleep(1)
    
    # 去重
    unique_hosts = list(OrderedDict.fromkeys(all_hosts))
    log(f"共获取 {len(unique_hosts)} 个唯一IP地址")
    
    return unique_hosts

# ===============================
# IP 信息获取函数
# ===============================
def get_ip_info(ip: str) -> Tuple[str, str]:
    """获取IP的地理位置和运营商信息"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"{ip}.json")
    
    # 读取缓存
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('expire', 0) > time.time():
                    return data.get('province', '未知'), data.get('isp', '未知')
        except Exception:
            pass
    
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?lang=zh-CN", timeout=10)
        data = response.json()
        
        if data.get('status') == 'success':
            province = data.get("regionName", "未知")
            isp_raw = (data.get("isp") or "").lower()
            
            # 判断运营商
            if any(x in isp_raw for x in ["telecom", "ct", "chinatelecom"]):
                isp = "电信"
            elif any(x in isp_raw for x in ["unicom", "cu", "chinaunicom"]):
                isp = "联通"
            elif any(x in isp_raw for x in ["mobile", "cm", "chinamobile"]):
                isp = "移动"
            else:
                isp = "未知"
            
            # 缓存24小时
            cache_data = {
                'province': province,
                'isp': isp,
                'expire': time.time() + 86400
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f)
            
            return province, isp
        else:
            return "未知", "未知"
            
    except Exception as e:
        log(f"获取IP信息失败 {ip}: {e}", "WARNING")
        return "未知", "未知"

def quick_isp_detect(ip: str) -> str:
    """通过IP段快速判断运营商"""
    try:
        first_octet = int(ip.split('.')[0])
    except:
        return "未知"
    
    # 电信IP段
    if first_octet in {1, 14, 42, 43, 58, 59, 60, 61, 106, 110, 111, 112, 113, 114, 115,
                       116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 139,
                       171, 175, 180, 182, 183, 184, 185, 186, 187, 188, 189, 218, 219,
                       220, 221, 222, 223}:
        return "电信"
    
    # 联通IP段
    if first_octet in {14, 27, 42, 43, 58, 59, 60, 61, 106, 110, 111, 112, 113, 114, 115,
                       116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 153,
                       175, 180, 182, 183, 184, 185, 186, 187, 188, 189, 211, 223}:
        return "联通"
    
    # 移动IP段
    if first_octet in {36, 37, 38, 39, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
                       120, 134, 135, 136, 137, 138, 139, 150, 151, 152, 157, 158, 159,
                       170, 178, 182, 183, 184, 187, 188, 189, 223}:
        return "移动"
    
    return "未知"

# ===============================
# 第一阶段：获取并分类IP
# ===============================
def first_stage() -> int:
    """第一阶段：获取IP并分类保存"""
    log("=" * 50)
    log("第一阶段：获取IP地址")
    log("=" * 50)
    
    os.makedirs(IP_DIR, exist_ok=True)
    
    # 获取FOFA数据
    ips = get_fofa_ips()
    
    if not ips:
        log("未获取到任何IP", "WARNING")
        return 0
    
    # 分类IP
    province_isp_dict: Dict[str, List[str]] = {}
    
    for idx, ip_port in enumerate(ips, 1):
        if idx % 50 == 0:
            log(f"处理进度: {idx}/{len(ips)}")
        
        try:
            # 提取IP
            host = ip_port.split(":")[0] if ":" in ip_port else ip_port
            
            # 验证IP格式
            if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
                continue
            
            # 获取运营商
            _, isp = get_ip_info(host)
            
            if isp == "未知":
                isp = quick_isp_detect(host)
            
            if isp == "未知":
                continue
            
            # 按运营商分组
            province_isp_dict.setdefault(isp, []).append(ip_port)
            
        except Exception as e:
            log(f"处理失败 {ip_port}: {e}", "WARNING")
            continue
    
    # 保存结果
    count = get_run_count() + 1
    save_run_count(count)
    
    for isp, ip_list in province_isp_dict.items():
        # 去重并限制数量
        unique_ips = list(OrderedDict.fromkeys(ip_list))
        if len(unique_ips) > MAX_IPS_PER_FILE:
            unique_ips = unique_ips[:MAX_IPS_PER_FILE]
        
        filename = f"{isp}.txt"
        filepath = os.path.join(IP_DIR, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            for ip_port in unique_ips:
                f.write(ip_port + "\n")
        
        log(f"{filename} 写入 {len(unique_ips)} 个IP")
    
    log(f"第一阶段完成，当前轮次: {count}")
    return count

# ===============================
# 第二阶段：生成zubo.txt
# ===============================
def second_stage():
    """第二阶段：组合IP和RTP频道"""
    log("=" * 50)
    log("第二阶段：生成直播源地址")
    log("=" * 50)
    
    if not os.path.exists(IP_DIR):
        log("ip目录不存在", "WARNING")
        return
    
    if not os.path.exists(RTP_DIR):
        log("rtp目录不存在，跳过第二阶段", "WARNING")
        return
    
    combined_lines = []
    rtp_files = [f for f in os.listdir(RTP_DIR) if f.endswith('.txt')]
    
    if not rtp_files:
        log("rtp目录下没有频道文件", "WARNING")
        return
    
    for ip_file in os.listdir(IP_DIR):
        if not ip_file.endswith(".txt"):
            continue
        
        ip_path = os.path.join(IP_DIR, ip_file)
        
        # 获取运营商对应的rtp文件
        isp_name = ip_file.replace(".txt", "")
        rtp_file = None
        
        for rf in rtp_files:
            if isp_name in rf or rf.startswith(isp_name):
                rtp_file = rf
                break
        
        if not rtp_file:
            rtp_file = rtp_files[0]  # 使用第一个可用文件
        
        rtp_path = os.path.join(RTP_DIR, rtp_file)
        
        if not os.path.exists(rtp_path):
            continue
        
        with open(ip_path, "r", encoding="utf-8") as f1:
            ip_lines = [x.strip() for x in f1 if x.strip()]
        
        with open(rtp_path, "r", encoding="utf-8") as f2:
            rtp_lines = [x.strip() for x in f2 if x.strip()]
        
        if not ip_lines or not rtp_lines:
            continue
        
        log(f"组合 {ip_file} ({len(ip_lines)} IP) × {rtp_file} ({len(rtp_lines)} 频道)")
        
        for ip_port in ip_lines:
            for rtp_line in rtp_lines:
                if "," not in rtp_line:
                    continue
                
                ch_name, rtp_url = rtp_line.split(",", 1)
                
                if "rtp://" in rtp_url:
                    part = rtp_url.split("rtp://", 1)[1]
                    combined_lines.append(f"{ch_name},http://{ip_port}/rtp/{part}")
                elif "udp://" in rtp_url:
                    part = rtp_url.split("udp://", 1)[1]
                    combined_lines.append(f"{ch_name},http://{ip_port}/udp/{part}")
    
    # 去重
    unique = OrderedDict()
    for line in combined_lines:
        url_part = line.split(",", 1)[1]
        if url_part not in unique:
            unique[url_part] = line
    
    with open(ZUBO_FILE, "w", encoding="utf-8") as f:
        for line in unique.values():
            f.write(line + "\n")
    
    log(f"第二阶段完成，生成 {len(unique)} 条记录")

# ===============================
# 第三阶段：检测可用性
# ===============================
def check_stream(url: str, timeout: int = TEST_TIMEOUT) -> bool:
    """快速检查流是否可播放"""
    try:
        # 使用HEAD请求快速检测
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        return response.status_code == 200
    except requests.RequestException:
        return False
    except Exception:
        return False

def test_ip(ip_port: str, entries: List[Tuple[str, str]]) -> Tuple[str, bool]:
    """测试单个IP的可用性"""
    # 优先测试CCTV1
    test_urls = [url for name, url in entries if "CCTV1" in name or "CCTV-1" in name]
    
    # 如果没有CCTV1，测试第一个频道
    if not test_urls and entries:
        test_urls = [entries[0][1]]
    
    for url in test_urls[:2]:
        if check_stream(url):
            return ip_port, True
    
    return ip_port, False

def third_stage():
    """第三阶段：检测频道可用性并生成IPTV.txt"""
    log("=" * 50)
    log("第三阶段：检测频道可用性")
    log("=" * 50)
    
    if not os.path.exists(ZUBO_FILE):
        log("zubo.txt不存在", "WARNING")
        return
    
    # 读取并分组
    groups: Dict[str, List[Tuple[str, str]]] = {}
    
    with open(ZUBO_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "," not in line:
                continue
            
            parts = line.split(",", 1)
            if len(parts) != 2:
                continue
            
            ch_name, url = parts
            match = re.match(r"http://([^/:]+)(?::\d+)?/", url)
            if not match:
                continue
            
            ip_port = match.group(1)
            groups.setdefault(ip_port, []).append((ch_name, url))
    
    log(f"共 {len(groups)} 个IP需要检测")
    
    # 多线程检测
    playable_ips = set()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(test_ip, ip, chs): ip for ip, chs in groups.items()}
        
        for future in concurrent.futures.as_completed(futures):
            try:
                ip_port, ok = future.result(timeout=TEST_TIMEOUT + 5)
                if ok:
                    playable_ips.add(ip_port)
                    log(f"✅ {ip_port} 可用")
                else:
                    log(f"❌ {ip_port} 不可用")
            except concurrent.futures.TimeoutError:
                log(f"⏰ {futures[future]} 检测超时")
            except Exception as e:
                log(f"⚠️ 检测异常: {e}")
    
    log(f"可用IP: {len(playable_ips)}/{len(groups)}")
    
    # 生成最终IPTV.txt
    generate_iptv_file(playable_ips, groups)

def generate_iptv_file(playable_ips: Set[str], groups: Dict):
    """生成IPTV.txt文件"""
    # 构建别名映射
    alias_map = {}
    for main_name, aliases in CHANNEL_MAPPING.items():
        for alias in aliases:
            alias_map[alias.lower()] = main_name
    
    # 收集有效频道
    valid_channels = {}
    
    for ip_port in playable_ips:
        for ch_name, url in groups.get(ip_port, []):
            # 标准化频道名
            normalized = alias_map.get(ch_name.lower(), ch_name)
            key = f"{normalized},{url}"
            if key not in valid_channels:
                valid_channels[key] = (normalized, url)
    
    # 按频道名排序
    sorted_channels = sorted(valid_channels.values(), key=lambda x: x[0])
    
    # 写入文件
    beijing_now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    
    with open(IPTV_FILE, "w", encoding="utf-8") as f:
        f.write(f"# 更新时间: {beijing_now} (北京时间)\n")
        f.write(f"# 可用频道数: {len(sorted_channels)}\n")
        f.write(f"# 可用IP数: {len(playable_ips)}\n\n")
        
        # 按分类输出
        for category, channel_list in CHANNEL_CATEGORIES.items():
            category_channels = []
            for ch_name, url in sorted_channels:
                if ch_name in channel_list:
                    category_channels.append((ch_name, url))
            
            if category_channels:
                f.write(f"{category},#genre#\n")
                for ch_name, url in category_channels:
                    f.write(f"{ch_name},{url}\n")
                f.write("\n")
        
        # 其他未分类频道
        other_channels = [(ch_name, url) for ch_name, url in sorted_channels 
                         if not any(ch_name in cl for cl in CHANNEL_CATEGORIES.values())]
        
        if other_channels:
            f.write("其他频道,#genre#\n")
            for ch_name, url in other_channels:
                f.write(f"{ch_name},{url}\n")
            f.write("\n")
    
    log(f"IPTV.txt 生成完成，共 {len(sorted_channels)} 条频道")

# ===============================
# Git 操作函数
# ===============================
def push_to_github():
    """推送到GitHub"""
    log("=" * 50)
    log("推送更新到GitHub")
    log("=" * 50)
    
    # 配置git
    os.system('git config user.name "github-actions[bot]"')
    os.system('git config user.email "github-actions[bot]@users.noreply.github.com"')
    
    # 添加文件
    os.system(f"git add {COUNTER_FILE} 2>/dev/null || true")
    os.system(f"git add {IP_DIR}/*.txt 2>/dev/null || true")
    os.system(f"git add {IPTV_FILE} 2>/dev/null || true")
    os.system(f"git add {ZUBO_FILE} 2>/dev/null || true")
    os.system("git add cache/*.json 2>/dev/null || true")
    
    # 检查是否有变更
    result = os.system('git diff --cached --quiet')
    if result == 0:
        log("没有文件变更，跳过提交")
        return
    
    # 提交
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.system(f'git commit -m "auto: 更新IPTV源 ({timestamp})"')
    
    # 推送
    push_result = os.system('git push origin main 2>/dev/null')
    if push_result == 0:
        log("推送成功")
    else:
        log("推送失败", "WARNING")

# ===============================
# 主函数
# ===============================
def main():
    """主函数"""
    log("=" * 50)
    log("IPTV源自动更新脚本启动")
    log(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 50)
    
    # 显示配置
    log(f"FOFA配置: {'已配置' if FOFA_EMAIL and FOFA_KEY else '未配置'}")
    log(f"每文件最大IP数: {MAX_IPS_PER_FILE}")
    log(f"检测超时: {TEST_TIMEOUT}秒")
    log(f"完整检测间隔: 每{RUN_EVERY_N}次")
    
    # 创建必要目录
    os.makedirs(IP_DIR, exist_ok=True)
    os.makedirs(RTP_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    # 执行第一阶段（总是执行）
    run_count = first_stage()
    
    # 根据运行次数决定是否执行完整检测
    if run_count > 0 and run_count % RUN_EVERY_N == 0:
        log(f"第{run_count}轮，执行完整检测")
        second_stage()
        third_stage()
    else:
        log(f"第{run_count}轮，跳过完整检测（每{RUN_EVERY_N}轮一次）")
    
    # 推送更新
    push_to_github()
    
    log("=" * 50)
    log("所有任务完成！")
    log("=" * 50)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("用户中断", "WARNING")
        sys.exit(0)
    except Exception as e:
        log(f"程序异常: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)