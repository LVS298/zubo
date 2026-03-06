import os
import re
import requests
import time
import concurrent.futures
import subprocess
import socket
import json
import threading
import queue
from datetime import datetime, timezone, timedelta
from collections import defaultdict, OrderedDict
import random

# ===============================
# 配置区
FOFA_URLS = {
    "https://fofa.info/result?qbase64=InVkcHh5IiAmJiBjb3VudHJ5PSJDTiI%3D": "ip.txt",
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

COUNTER_FILE = "计数.txt"
IP_DIR = "ip"
RTP_DIR = "rtp"
ZUBO_FILE = "zubo.txt"
IPTV_FILE = "IPTV.txt"
CACHE_DIR = "cache"
PLAYLIST_CACHE = "playlist_cache.json"
SOURCE_STATUS_FILE = "source_status.json"

# 新增配置
MAX_SOURCES_PER_CHANNEL = 5  # 每个频道最多保留的源数量
CHECK_TIMEOUT = 3  # 检测超时时间
CHECK_RETRIES = 2  # 检测重试次数
CACHE_EXPIRE = 3600  # 缓存过期时间（秒）
SOURCE_SCORE_FILE = "source_scores.json"  # 源评分文件

# ===============================
# 分类与映射配置（保持不变）
CHANNEL_CATEGORIES = {
    "央卫综艺": [
        "CCTV-1综合", "湖南卫视", "纪实科教", "大湾区卫视", "CCTV-2财经", "湖南卫视4K", "凤凰卫视中文台", "浙江卫视", "凤凰卫视资讯台", "CCTV-3综艺", 
        "江苏卫视", "CCTV-4中文国际", "浙江卫视4K", "CCTV-4欧洲", "江苏卫视4K", "东方卫视4K", "CCTV-4美洲", "东方卫视", "CCTV-5体育", "深圳卫视",
        "CCTV-6电影", "深圳卫视4K", "凤凰卫视香港台",  "北京卫视", "CCTV-7国防军事", "4K纪实", "CCTV-8电视剧", "北京卫视4K", "CCTV-9纪录", "广东卫视",
        "CCTV-10科教", "广东卫视4K", "CCTV-11戏曲", "广东卫视4K", "四川卫视4K", "CCTV-12社会与法", "东南卫视", "CCTV-13新闻", "广西卫视", "兵器科技", 
        "CCTV-14少儿", "海南卫视", "CCTV-15音乐", "河北卫视", "CCTV-16奥林匹克", "河南卫视", "CCTV-17农业农村", "湖北卫视", "CCTV-4K超高清", "江西卫视", 
        "CCTV-8K超高清", "环球旅游", "四川卫视", "CCTV-5+体育赛事", "4K视界", "热门综艺", "重庆卫视", "风云音乐", "贵州卫视", "风云足球", "云南卫视",      
        "风云剧场", "天津卫视", "怀旧剧场", "安徽卫视", "第一剧场", "山东卫视", "女性时尚", "山东卫视4K", "世界地理", "辽宁卫视", "央视台球", "黑龙江卫视",
        "高尔夫网球", "内蒙古卫视", "吉林卫视", "金鹰纪实", "宁夏卫视", "乐游", "山西卫视", "生活时尚", "陕西卫视", "看天下精选", "中国交通",  "中国交通", 
        "中国天气", "青海卫视", "新疆卫视", "央视文化精品", "西藏卫视", "卫生健康", "三沙卫视", "电视指南", "兵团卫视", "中学生", "延边卫视", "发现之旅", 
        "书法频道", "安多卫视", "国学频道", "康巴卫视", "环球奇观", "农林卫视", "翡翠台", "山东教育卫视", "明珠台", "求索生活", "求索动物", "纪实人文", 
        "中国教育1台", "湖北卫视", "中国教育2台", "中国教育3台", "中国教育4台", "早期教育", "新视觉HD","澳亚卫视", "广州竞赛",  "爱宠宠物", "求索纪录", "求索科学",
        "茶频道", "甘肃卫视", "梨园频道", "文物宝库", "法制天地",
    ],
    "影视剧院": [
        "CHC动作电影", "CHC家庭影院", "CHC影迷电影", "淘电影", "淘剧场", "淘4K", "淘娱乐",  "淘萌宠", "重温经典", "峨眉电影4K",  "星空卫视", "绚影4K",
        "CHANNEL[V]", "凤凰卫视电影台", "都市剧场", "欢笑剧场", "华数4K", "华数光影", "华数星影", "华数精选", "华数动作影院", "华数喜剧影院", "华数家庭影院", 
        "华数经典电影", "华数热播剧场", "华数碟战剧场","华数军旅剧场", "华数城市剧场", "华数武侠剧场", "华数古装剧场", "华数魅力时尚", "峨眉电影", "爱体育",
        "爱历史", "爱喜剧", "爱奇谈", "爱悬疑", "爱旅行", "爱浪漫", "爱玩具", "爱科幻", "爱谍战", "爱赛车", "爱院线", "BesTV-4K", "BesTV4K-1", "BesTV4K-2",
        "CBN每日影院", "CBN幸福娱乐", "CBN幸福剧场", "CBN风尚生活", "爱探索", "爱青春", "爱怀旧", "爱经典", "爱都市", "爱家庭", "全球大片", "华语影院", 
        "戏曲精选", "热门剧场", "BesTV谍战剧场", "NewTV金牌综艺","NEWTV家庭剧场", "NEWTV精品纪录", "NEWTV健康有约", "NEWTV精品体育", "NEWTV军事评论", "NEWTV农业致富",
        "NEWTV古装剧场", "NEWTV动作电影", "NEWTV军旅剧场", "NEWTV惊悚悬疑", "NewTV海外剧场", "NewTV搏击", "NewTV明星大片", "NewTV爱情喜剧", "NewTV精品大剧", 
        "NewTV中国功夫", "4K乐享超清","黑莓电影", "环球影视", "精彩影视",
    ],
    "少儿教育": [
        "乐龄学堂", "少儿天地", "动漫秀场", "淘BABY", "黑莓动画", "爱动漫", "睛彩青少", "金色学堂", "新动漫", "卡酷少儿", "金鹰卡通", "优漫卡通", "哈哈炫动", "嘉佳卡通",
        "华数少儿动画", "华数动画", "亲子趣学", "爱幼教", "4K少儿", "百变课堂",
    ],
    "体育竞技": [
        "劲爆体育", "快乐垂钓", "四海钓鱼", "来钓鱼吧", "睛彩竞技", "睛彩篮球", "睛彩广场舞", "魅力足球", "五星体育", "游戏风云", "武术世界", "哒啵赛事", "哒啵电竞",
        "先锋乒羽", "天元围棋", "汽摩", "电竞天堂", "青春动漫",
    ],
}

# ===== 映射（别名 -> 标准名） =====（保持不变）
CHANNEL_MAPPING = {
    "CCTV-1综合": ["CCTV-1", "CCTV-1 HD", "CCTV1 HD", "CCTV1"],
    "CCTV-2财经": ["CCTV-2", "CCTV-2 HD", "CCTV2 HD", "CCTV2"],
    "CCTV-3综艺": ["CCTV-3", "CCTV-3 HD", "CCTV3 HD", "CCTV3"],
    "CCTV-4中文国际": ["CCTV-4", "CCTV-4 HD", "CCTV4 HD", "CCTV4"],
    "CCTV-4欧洲": ["CCTV-4欧洲", "CCTV-4欧洲", "CCTV4欧洲 HD", "CCTV-4 欧洲", "CCTV-4中文国际欧洲", "CCTV4"],
    "CCTV-4美洲": ["CCTV-4美洲", "CCTV-4北美", "CCTV4美洲 HD", "CCTV-4 美洲", "CCTV-4中文国际美洲", "CCTV4"],
    "CCTV-5体育": ["CCTV-5", "CCTV-5 HD", "CCTV5 HD", "CCTV5"],
    "少儿天地": ["睛彩少儿HD", "精彩连播"],
    "乐龄学堂": ["睛彩学堂HD", "精彩连播"],
    "动漫秀场": ["动漫秀场", "睛彩亲子HD", "精彩连播"],
    "综艺咖秀": ["睛彩综艺HD", "精彩连播"],
    "爱宠宠物": ["睛彩爱宠HD", "精彩连播"],
    "新视觉HD": ["新视觉"],
    "CCTV-5+体育赛事": ["CCTV-5+", "CCTV-5+ HD", "CCTV5+ HD", "CCTV5+"],
    "CCTV-6电影": ["CCTV-6", "CCTV-6 HD", "CCTV6 HD", "CCTV6"],
    "CCTV-7国防军事": ["CCTV-7", "CCTV-7 HD", "CCTV7 HD", "CCTV7"],
    "CCTV-8电视剧": ["CCTV-8", "CCTV-8 HD", "CCTV8 HD", "CCTV8"],
    "CCTV-9纪录": ["CCTV-9", "CCTV-9 HD", "CCTV9 HD", "CCTV9"],
    "CCTV-10科教": ["CCTV-10", "CCTV-10 HD", "CCTV10 HD", "CCTV10"],
    "CCTV-11戏曲": ["CCTV-11", "CCTV-11 HD", "CCTV11 HD", "CCTV11"],
    "CCTV-12社会与法": ["CCTV-12", "CCTV-12 HD", "CCTV12 HD", "CCTV12"],
    "CCTV-13新闻": ["CCTV-13", "CCTV-13 HD", "CCTV13 HD", "CCTV13"],
    "CCTV-14少儿": ["CCTV-14", "CCTV-14 HD", "CCTV14 HD", "CCTV14"],
    "CCTV-15音乐": ["CCTV-15", "CCTV-15 HD", "CCTV15 HD", "CCTV15"],
    "CCTV-16奥林匹克": ["CCTV-16", "CCTV-16 HD", "CCTV-16 4K", "CCTV16", "CCTV16 4K", "CCTV-16奥林匹克4K"],
    "CCTV-17农业农村": ["CCTV-17", "CCTV-17 HD", "CCTV17 HD", "CCTV17"],
    "CCTV-4K超高清": ["CCTV4K超高清", "CCTV4K", "CCTV-4K 超高清", "CCTV 4K"],
    "CCTV-8K超高清": ["CCTV8K超高清", "CCTV8K", "CCTV-8K 超高清", "CCTV 8K"],
    "兵器科技": ["CCTV-兵器科技", "CCTV兵器科技"],
    "风云音乐": ["CCTV-风云音乐", "CCTV风云音乐"],
    "第一剧场": ["CCTV-第一剧场", "CCTV第一剧场"],
    "风云足球": ["CCTV-风云足球", "CCTV风云足球"],
    "风云剧场": ["CCTV-风云剧场", "CCTV风云剧场"],
    "怀旧剧场": ["CCTV-怀旧剧场", "CCTV怀旧剧场"],
    "女性时尚": ["CCTV-女性时尚", "CCTV女性时尚"],
    "世界地理": ["CCTV-世界地理", "CCTV世界地理"],
    "央视台球": ["CCTV-央视台球", "CCTV央视台球"],
    "高尔夫网球": ["CCTV-高尔夫网球", "CCTV高尔夫网球", "CCTV央视高网", "CCTV-高尔夫·网球", "央视高网"],
    "央视文化精品": ["CCTV-央视文化精品", "CCTV央视文化精品", "CCTV文化精品", "CCTV-文化精品", "文化精品"],
    "卫生健康": ["CCTV-卫生健康", "CCTV卫生健康"],
    "电视指南": ["CCTV-电视指南", "CCTV电视指南"],
    "农林卫视": ["陕西农林卫视"],
    "三沙卫视": ["海南三沙卫视"],
    "兵团卫视": ["新疆兵团卫视"],
    "延边卫视": ["吉林延边卫视"],
    "安多卫视": ["青海安多卫视"],
    "康巴卫视": ["四川康巴卫视"],
    "山东教育卫视": ["山东教育"],
    "书法频道": ["书画", "书画HD", "书画", "书画频道"],
    "国学频道": ["国学", "国学高清", "国学HD"],
    "翡翠台": ["TVB翡翠台", "无线翡翠台", "翡翠台"],
    "明珠台": ["明珠台", "无线明珠台", "TVB明珠台"],
    "中国教育1台": ["CETV1", "中国教育一台", "中国教育1", "CETV-1 综合教育", "CETV-1"],
    "中国教育2台": ["CETV2", "中国教育二台", "中国教育2", "CETV-2 空中课堂", "CETV-2"],
    "中国教育3台": ["CETV3", "中国教育三台", "中国教育3", "CETV-3 教育服务", "CETV-3"],
    "中国教育4台": ["CETV4", "中国教育四台", "中国教育4", "CETV-4 职业教育", "CETV-4"],
    "早期教育": ["中国教育5台", "中国教育五台", "CETV早期教育", "华电早期教育", "CETV 早期教育"],
    "新视觉HD": ["新视觉", "新视觉hd", "新视觉高清"],
    "湖南卫视": ["湖南卫视HD"],
    "北京卫视": ["北京卫视HD"],
    "东方卫视": ["东方卫视HD"],
    "广东卫视": ["广东卫视HD"],
    "深圳卫视": ["深圳卫视HD"],
    "山东卫视": ["山东卫视HD"],
    "四川卫视": ["四川卫视HD"],
    "浙江卫视": ["浙江卫视HD"],
    "CHC影迷电影": ["CHC影迷电影HD", "CHC 影迷电影", "影迷电影", "CHC影迷电影高清"],
    "CHC家庭影院": ["CHC 家庭影院", "CHC家庭影院HD", "CHC家庭影院高清"], 
    "CHC动作电影": ["CHC 动作电影", "CHC动作电影HD",, "CHC动作电影高清"],
    "淘电影": ["IPTV淘电影", "北京IPTV淘电影", "北京淘电影"],
    "淘剧场": ["IPTV淘剧场", "北京IPTV淘剧场", "北京淘剧场"],
    "淘4K": ["IPTV淘4K", "北京IPTV4K超高清", "北京淘4K", "淘4K", "北京IPTV淘4K", "北京IPTV4K超清", "4K超清"],
    "淘娱乐": ["IPTV淘娱乐", "北京IPTV淘娱乐", "北京淘娱乐"],
    "淘BABY": ["IPTV淘BABY", "北京IPTV淘BABY", "北京淘BABY", "IPTV淘baby", "北京IPTV淘baby", "北京淘baby", "淘Baby", "淘宝贝"],
    "淘萌宠": ["IPTV淘萌宠", "北京IPTV萌宠TV", "北京淘萌宠", "萌宠TV"],
    "魅力足球": ["上海魅力足球"],
    "睛彩青少": ["睛彩羽毛球", "睛彩青少HD", "睛彩青少高清", "睛彩青少hd"],
    "睛彩广场舞":["睛彩广场舞HD", "睛彩广场舞高清", "睛彩广场舞hd"],
    "睛彩竞技":["睛彩竞技高清", "睛彩竞技HD", "睛彩竞技hd"],
    "睛彩篮球":["睛彩篮球HD", "睛彩篮球高清", "睛彩篮球hd"],
    "求索纪录": ["求索记录", "求索纪录HD", "求索记录4K", "求索纪录 4K", "求索记录 4K"],
    "金鹰纪实": ["湖南金鹰纪实", "金鹰记实" "金鹰纪实HD"],
    "纪实科教": ["北京纪实科教", "BRTV纪实科教", "纪实科教8K"],
    "星空卫视": ["星空衛視", "星空衛视", "星空卫視"],
    "CHANNEL[V]": ["CHANNEL-V", "Channel[V]HD", "ChannelV"],
    "凤凰卫视中文台": ["凤凰中文", "凤凰中文台", "凤凰卫视中文", "凤凰卫视"],
    "凤凰卫视香港台": ["凤凰香港台", "凤凰卫视香港", "凤凰香港"],
    "凤凰卫视资讯台": ["凤凰资讯", "凤凰资讯台", "凤凰咨询", "凤凰咨询台", "凤凰卫视咨询台", "凤凰卫视资讯", "凤凰卫视咨询"],
    "凤凰卫视电影台": ["凤凰电影", "凤凰电影台", "凤凰卫视电影", "鳳凰衛視電影台", "凤凰电影"],
    "茶频道": ["湖南茶频道"],
    "快乐垂钓": ["湖南快乐垂钓", "快乐垂钓HD"],
    "四海钓鱼": ["四海钓鱼HD"],
    "来钓鱼吧": ["来钓鱼吧HD", "睛彩钓鱼HD"],
    "先锋乒羽": ["湖南先锋乒羽"],
    "天元围棋": ["天元围棋频道", "天元围棋HD"],
    "汽摩": ["重庆汽摩", "汽摩频道", "重庆汽摩频道"],
    "梨园频道": ["河南梨园频道", "梨园", "河南梨园", "梨园频道HD"],
    "法制天地": ["法治天地HD"],
    "文物宝库": ["河南文物宝库"],
    "武术世界": ["河南武术世界"],
    "乐游": ["乐游频道", "上海乐游频道", "乐游纪实", "SiTV乐游频道", "SiTV 乐游频道", "乐游HD"],
    "欢笑剧场": ["上海欢笑剧场4K", "欢笑剧场 4K", "欢笑剧场4K", "上海欢笑剧场"],
    "生活时尚": ["生活时尚4K", "SiTV生活时尚", "上海生活时尚", "生活时尚HD"],
    "都市剧场": ["都市剧场4K", "SiTV都市剧场", "上海都市剧场", "都市剧场HD"],
    "游戏风云": ["游戏风云4K", "SiTV游戏风云", "上海游戏风云", "游戏风云HD"],
    "金色学堂": ["金色学堂4K", "SiTV金色学堂", "上海金色学堂", "金色学堂HD"],
    "动漫秀场": ["动漫秀场4K", "SiTV动漫秀场", "上海动漫秀场"],
    "卡酷少儿": ["北京KAKU少儿", "BRTV卡酷少儿", "北京卡酷少儿", "卡酷动画"],
    "哈哈炫动": ["炫动卡通", "上海哈哈炫动"],
    "优漫卡通": ["江苏优漫卡通", "优漫漫画"],
    "金鹰卡通": ["湖南金鹰卡通"],
    "中国交通": ["中国交通频道"],
    "中国天气": ["中国天气频道"],
    "亲子趣学": ["睛彩亲子4K"],
    "华数4K": ["华数低于4K", "华数4K电影", "华数爱上4K", "爱上4K"],
    "华数光影": ["光影"],
    "华数星影": ["星影"],
    "华数精选": ["精选"],
    "华数电影": ["IPTV6华数电影"],
    "华数动作影院": ["动作电影", "动作电影HD"],
    "华数喜剧影院": ["喜剧影院", "喜剧影院HD"],
    "华数家庭影院": ["家庭影院", "家庭影院HD"], 
    "华数经典电影": ["IPTV经典电影", "经典电影", "经典电影HD"],
    "华数热播剧场": ["IPTV热播剧场", "热播剧场", "热播剧场HD"],
    "华数碟战剧场": ["IPTV谍战剧场", "谍战剧场", "谍战剧场HD"],
    "华数军旅剧场": ["IPTV军旅剧场", "军旅剧场", "军旅剧场HD"],
    "华数城市剧场": ["IPTV城市剧场", "城市剧场", "城市剧场HD"],
    "华数武侠剧场": ["IPTV武侠剧场", "武侠剧场", "武侠剧场HD"],
    "华数古装剧场": ["IPTV古装剧场", "古装剧场", "古装剧场HD"],
    "华数魅力时尚": ["IPTV魅力时尚", "魅力时尚", "魅力时尚HD"],
    "华数少儿动画": ["华数少儿动画"],
    "华数动画": ["华数卡通", "IPTV少儿动画"],
    "峨眉电影": ["四川峨眉HD", "峨眉电影高清", "峨眉电影", "四川峨眉", "四川峨眉电影", "四川峨眉高清"],
    "峨眉电影4K": ["4K超高清电影"],
    "绚影4K": ["绚影4K", "睛彩绚影4K", "精彩连播", "天府绚影高清影院"],
    "4K乐享": ["4K乐享超清"],
    "爱体育": ["爱体育HD", "IHOT爱体育", "iHOT爱体育", "爱体育高清"],
    "爱历史": ["爱历史HD", "IHOT爱历史", "iHOT爱历史", "HO爱历史", "爱历史高清"], 
    "爱动漫": ["爱动漫HD", "IHOT爱动漫", "iHOT爱动漫" "爱动漫高清"], 
    "爱喜剧": ["爱喜剧HD", "IHOT爱喜剧", "iHOT爱喜剧", "爱喜剧高清"],
    "爱奇谈": ["爱奇谈HD", "IHOT爱奇谈", "iHOT爱奇谈", "爱奇谈高清"], 
    "爱幼教": ["爱幼教HD", "IHOT爱幼教", "iHOT爱幼教", "爱幼教高清"], 
    "爱悬疑": ["爱悬疑HD", "IHOT爱悬疑", "iHOT爱悬疑", "爱悬疑高清"],
    "爱旅行": ["爱旅行HD", "IHOT爱旅行", "iHOT爱旅行", "爱旅行高清"], 
    "爱浪漫": ["爱浪漫HD", "IHOT爱浪漫", "iHOT爱浪漫", "爱浪漫高清"],
    "爱玩具": ["爱玩具HD", "IHOT爱玩具", "iHOT爱玩具", "爱玩具高清"],
    "爱科幻": ["爱科幻HD", "IHOT爱科幻", "iHOT爱科幻", "爱科幻高清"], 
    "爱谍战": ["爱谍战HD", "IHOT爱谍战", "iHOT爱谍战", "爱谍战高清"],
    "爱赛车": ["爱谍战HD", "IHOT爱赛车", "iHOT爱赛车", "爱赛车高清"],
    "爱院线": ["爱院线HD", "IHOT爱院线", "iHOT爱院线", "爱院线高清"],
    "爱科学": ["爱科学HD", "IHOT爱科学", "iHOT爱科学", "爱科学高清"],
    "爱探索": ["爱探索HD", "THOT爱探索", "iHOT爱探索", "爱探索高清"],
    "爱青春": ["爱青春HD", "IHOT爱青春", "iHOT爱青春", "爱青春高清"],
    "爱怀旧": ["爱怀旧HD", "IHOT爱怀旧", "iHOT爱怀旧", "爱怀旧高清"],
    "爱经典": ["爱经典HD", "IHOT爱经典", "iHOT爱经典", "HO经典", "爱经典高清"],
    "爱都市": ["爱都市HD", "IHOT爱都市", "iHOT爱都市", "爱都市高清"],
    "爱家庭": ["爱家庭HD", "IHOT爱家庭", "iHOT爱家庭", "爱家庭高清"],
    "环球奇观": ["环球奇观HD"],
    "精彩影视": ["精彩影视高清"],
}

# ===============================
# 新增：源评分管理类
class SourceScoreManager:
    def __init__(self, score_file=SOURCE_SCORE_FILE):
        self.score_file = score_file
        self.scores = self.load_scores()
        self.lock = threading.Lock()
    
    def load_scores(self):
        """加载源评分"""
        if os.path.exists(self.score_file):
            try:
                with open(self.score_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_scores(self):
        """保存源评分"""
        with open(self.score_file, 'w', encoding='utf-8') as f:
            json.dump(self.scores, f, ensure_ascii=False, indent=2)
    
    def update_score(self, url, success, response_time=None):
        """更新源评分"""
        with self.lock:
            if url not in self.scores:
                self.scores[url] = {
                    'success_count': 0,
                    'fail_count': 0,
                    'avg_response_time': 0,
                    'last_check': time.time(),
                    'score': 50  # 初始分数
                }
            
            score_data = self.scores[url]
            
            if success:
                score_data['success_count'] += 1
                if response_time:
                    # 更新平均响应时间
                    old_avg = score_data['avg_response_time']
                    count = score_data['success_count']
                    score_data['avg_response_time'] = (old_avg * (count - 1) + response_time) / count
                
                # 分数计算公式：基础分 + 成功率 * 30 + 响应时间因子 * 20
                success_rate = score_data['success_count'] / max(1, score_data['success_count'] + score_data['fail_count'])
                time_score = max(0, min(20, 20 * (1 - (score_data['avg_response_time'] / 10))))  # 响应时间越快分数越高
                score_data['score'] = 50 + success_rate * 30 + time_score
            else:
                score_data['fail_count'] += 1
                # 失败降分
                score_data['score'] = max(0, score_data['score'] - 10)
            
            score_data['last_check'] = time.time()
            self.save_scores()
    
    def get_best_sources(self, urls, limit=3):
        """获取评分最高的源"""
        scored = [(url, self.scores.get(url, {}).get('score', 50)) for url in urls]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [url for url, score in scored[:limit]]

# ===============================
# 新增：流媒体检测优化类
class StreamChecker:
    def __init__(self, timeout=CHECK_TIMEOUT, retries=CHECK_RETRIES):
        self.timeout = timeout
        self.retries = retries
        self.cache = {}
        self.cache_time = {}
        self.lock = threading.Lock()
    
    def check_stream(self, url, force=False):
        """检查流媒体是否可用，带缓存和重试机制"""
        current_time = time.time()
        
        # 检查缓存
        with self.lock:
            if not force and url in self.cache:
                if current_time - self.cache_time.get(url, 0) < 60:  # 缓存1分钟
                    return self.cache[url]
        
        for i in range(self.retries):
            try:
                start_time = time.time()
                
                # 使用ffprobe检测，增加超时控制
                result = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_streams", "-i", url],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self.timeout + 2,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                response_time = time.time() - start_time
                success = b"codec_type" in result.stdout
                
                # 更新缓存
                with self.lock:
                    self.cache[url] = success
                    self.cache_time[url] = current_time
                
                return success, response_time
                
            except subprocess.TimeoutExpired:
                if i == self.retries - 1:
                    with self.lock:
                        self.cache[url] = False
                        self.cache_time[url] = current_time
                    return False, self.timeout
            except Exception:
                if i == self.retries - 1:
                    with self.lock:
                        self.cache[url] = False
                        self.cache_time[url] = current_time
                    return False, None
                time.sleep(0.5)
        
        return False, None
    
    def batch_check(self, urls, max_workers=5):
        """批量检测流媒体"""
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(self.check_stream, url): url for url in urls}
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    success, response_time = future.result()
                    results[url] = (success, response_time)
                except Exception as e:
                    results[url] = (False, None)
        return results

# ===============================
# 新增：智能源选择器
class SourceSelector:
    def __init__(self):
        self.score_manager = SourceScoreManager()
        self.checker = StreamChecker()
        self.source_groups = defaultdict(list)  # 按频道分组的源
    
    def add_source(self, channel, url, operator):
        """添加源到分组"""
        self.source_groups[channel].append({
            'url': url,
            'operator': operator,
            'last_check': 0,
            'score': 50
        })
    
    def select_best_source(self, channel):
        """为频道选择最佳源"""
        if channel not in self.source_groups:
            return None
        
        sources = self.source_groups[channel]
        
        # 获取所有源的URL
        urls = [s['url'] for s in sources]
        
        # 按评分排序
        best_urls = self.score_manager.get_best_sources(urls, limit=3)
        
        # 检测最佳的几个源
        for url in best_urls:
            success, response_time = self.checker.check_stream(url)
            if success:
                # 更新评分
                self.score_manager.update_score(url, True, response_time)
                return url
            else:
                self.score_manager.update_score(url, False)
        
        return None
    
    def get_all_sources(self, channel):
        """获取频道的所有可用源"""
        if channel not in self.source_groups:
            return []
        
        sources = self.source_groups[channel]
        urls = [s['url'] for s in sources]
        
        # 批量检测
        results = self.checker.batch_check(urls)
        
        # 更新评分并返回可用源
        available = []
        for url, (success, response_time) in results.items():
            if success:
                self.score_manager.update_score(url, True, response_time)
                available.append(url)
            else:
                self.score_manager.update_score(url, False)
        
        # 按评分排序
        return self.score_manager.get_best_sources(available)

# ===============================
# 原有的函数（保持基本不变，但可能调用新的类）
def get_run_count():
    if os.path.exists(COUNTER_FILE):
        try:
            return int(open(COUNTER_FILE, "r", encoding="utf-8").read().strip() or "0")
        except Exception:
            return 0
    return 0

def save_run_count(count):
    try:
        with open(COUNTER_FILE, "w", encoding="utf-8") as f:
            f.write(str(count))
    except Exception as e:
        print(f"⚠️ 写计数文件失败：{e}")

def get_isp_from_api(data):
    isp_raw = (data.get("isp") or "").lower()

    if "telecom" in isp_raw or "ct" in isp_raw or "chinatelecom" in isp_raw:
        return "电信"
    elif "unicom" in isp_raw or "cu" in isp_raw or "chinaunicom" in isp_raw:
        return "联通"
    elif "mobile" in isp_raw or "cm" in isp_raw or "chinamobile" in isp_raw:
        return "移动"

    return "未知"

def get_isp_by_regex(ip):
    if re.match(r"^(1[0-9]{2}|2[0-3]{2}|1|14|42|43|58|59|60|61|106|110|111|112|113|114|115|116|117|118|119|120|121|122|123|124|125|126|127|139|171|175|180|182|183|184|185|186|187|188|189|218|219|220|221|222|223)\.", ip):
        return "电信"

    elif re.match(r"^(14|27|42|43|58|59|60|61|106|110|111|112|113|114|115|116|117|118|119|120|121|122|123|124|125|126|127|153|175|180|182|183|184|185|186|187|188|189|211|223)\.", ip):
        return "联通"

    elif re.match(r"^(223|36|37|38|39|100|101|102|103|104|105|106|107|108|109|120|134|135|136|137|138|139|150|151|152|157|158|159|170|178|182|183|184|187|188|189)\.", ip):
        return "移动"

    return "未知"

# ===============================
# 第一阶段（优化：增加IP去重和验证）
def first_stage():
    os.makedirs(IP_DIR, exist_ok=True)
    all_ips = set()

    for url, filename in FOFA_URLS.items():
        print(f"📡 正在爬取 {filename} ...")
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            urls_all = re.findall(r'<a href="http://(.*?)"', r.text)
            # 基本验证IP格式
            for u in urls_all:
                u = u.strip()
                if u and ':' in u:
                    ip_part = u.split(':')[0]
                    if re.match(r'^\d{1,3}(\.\d{1,3}){3}$', ip_part) or re.match(r'^[a-zA-Z0-9.-]+$', ip_part):
                        all_ips.add(u)
        except Exception as e:
            print(f"❌ 爬取失败：{e}")
        time.sleep(3)

    province_isp_dict = {}

    for ip_port in all_ips:
        try:
            host = ip_port.split(":")[0]

            is_ip = re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host)

            if not is_ip:
                try:
                    resolved_ip = socket.gethostbyname(host)
                    print(f"🌐 域名解析成功: {host} → {resolved_ip}")
                    ip = resolved_ip
                except Exception:
                    print(f"❌ 域名解析失败，跳过：{ip_port}")
                    continue
            else:
                ip = host

            # 增加重试机制
            for retry in range(3):
                try:
                    res = requests.get(f"http://ip-api.com/json/{ip}?lang=zh-CN", timeout=10)
                    if res.status_code == 200:
                        data = res.json()
                        break
                except:
                    if retry == 2:
                        raise
                    time.sleep(1)

            province = data.get("regionName", "未知")
            isp = get_isp_from_api(data)

            if isp == "未知":
                isp = get_isp_by_regex(ip)

            if isp == "未知":
                print(f"⚠️ 无法判断运营商，跳过：{ip_port}")
                continue

            fname = f"{province}{isp}.txt"
            province_isp_dict.setdefault(fname, set()).add(ip_port)

        except Exception as e:
            print(f"⚠️ 解析 {ip_port} 出错：{e}")
            continue

    count = get_run_count() + 1
    save_run_count(count)

    for filename, ip_set in province_isp_dict.items():
        path = os.path.join(IP_DIR, filename)
        try:
            # 读取现有IP去重
            existing_ips = set()
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    existing_ips = set(line.strip() for line in f if line.strip())
            
            # 合并新IP
            all_ips = existing_ips.union(ip_set)
            
            with open(path, "w", encoding="utf-8") as f:
                for ip_port in sorted(all_ips):
                    f.write(ip_port + "\n")
            print(f"{path} 已写入 {len(all_ips)} 个 IP（新增 {len(ip_set)}）")
        except Exception as e:
            print(f"❌ 写入 {path} 失败：{e}")

    print(f"✅ 第一阶段完成，当前轮次：{count}")
    return count

# ===============================
# 第二阶段（优化：增加URL有效性预检）
def second_stage():
    print("🔔 第二阶段触发：生成 zubo.txt")
    if not os.path.exists(IP_DIR):
        print("⚠️ ip 目录不存在，跳过第二阶段")
        return

    combined_lines = []

    if not os.path.exists(RTP_DIR):
        print("⚠️ rtp 目录不存在，无法进行第二阶段组合，跳过")
        return

    # 预检IP有效性
    valid_ips = {}
    for ip_file in os.listdir(IP_DIR):
        if not ip_file.endswith(".txt"):
            continue
        ip_path = os.path.join(IP_DIR, ip_file)
        try:
            with open(ip_path, encoding="utf-8") as f:
                ips = [x.strip() for x in f if x.strip()]
                if ips:
                    valid_ips[ip_file] = ips
        except Exception as e:
            print(f"⚠️ 读取 {ip_path} 失败：{e}")

    for ip_file, ip_lines in valid_ips.items():
        rtp_path = os.path.join(RTP_DIR, ip_file)

        if not os.path.exists(rtp_path):
            continue

        try:
            with open(rtp_path, encoding="utf-8") as f2:
                rtp_lines = [x.strip() for x in f2 if x.strip()]
        except Exception as e:
            print(f"⚠️ 文件读取失败：{e}")
            continue

        if not rtp_lines:
            continue

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

    # 去重并保留所有可用源（不合并，保留多源）
    unique_sources = {}
    for line in combined_lines:
        name, url = line.split(",", 1)
        key = f"{name},{url}"
        if key not in unique_sources:
            unique_sources[key] = line

    try:
        with open(ZUBO_FILE, "w", encoding="utf-8") as f:
            for line in unique_sources.values():
                f.write(line + "\n")
        print(f"🎯 第二阶段完成，写入 {len(unique_sources)} 条记录（含多源）")
    except Exception as e:
        print(f"❌ 写文件失败：{e}")

# ===============================
# 配置区新增（请添加到文件开头的配置区）
MAX_RUNTIME = 10800  # 最大运行时间：3小时（10800秒）
MAX_SOURCES_PER_CHANNEL_CHECK = 50  # 每个频道最多检测的源数量
FAST_CHECK_TIMEOUT = 2  # 快速检测超时时间
BATCH_SIZE = 20  # 每批检测的频道数量
MIN_SUCCESS_RATE = 0.05  # 最小成功率阈值
# ===============================

# ===============================
# 新增：快速流媒体检测类（放在SourceSelector类后面）
class FastStreamChecker:
    """快速检测类 - 使用HTTP HEAD请求代替ffprobe"""
    
    def __init__(self, timeout=FAST_CHECK_TIMEOUT):
        self.timeout = timeout
        self.cache = {}
        self.cache_time = {}
        self.lock = threading.Lock()
    
    def check_stream_fast(self, url, force=False):
        """快速检测：只检查HTTP响应头，检查是否能连接"""
        current_time = time.time()
        
        # 检查缓存
        with self.lock:
            if not force and url in self.cache:
                if current_time - self.cache_time.get(url, 0) < 300:  # 缓存5分钟
                    return self.cache[url], 0.5
        
        try:
            start_time = time.time()
            # 只发送HEAD请求，检查是否能连接
            response = requests.head(
                url, 
                timeout=self.timeout, 
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            response_time = time.time() - start_time
            success = response.status_code < 400
            
            # 更新缓存
            with self.lock:
                self.cache[url] = success
                self.cache_time[url] = current_time
            
            return success, response_time
        except Exception:
            with self.lock:
                self.cache[url] = False
                self.cache_time[url] = current_time
            return False, None
    
    def batch_check_fast(self, urls, max_workers=20):
        """快速批量检测"""
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(self.check_stream_fast, url): url for url in urls}
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    success, resp_time = future.result()
                    results[url] = (success, resp_time)
                except Exception:
                    results[url] = (False, None)
        return results

# ===============================
# 优化后的第三阶段
def third_stage():
    print("🧩 第三阶段：智能多源检测生成 IPTV.txt")
    start_time = time.time()

    if not os.path.exists(ZUBO_FILE):
        print("⚠️ zubo.txt 不存在，跳过第三阶段")
        return

    # 初始化检测工具
    fast_checker = FastStreamChecker()
    standard_checker = StreamChecker()
    score_manager = SourceScoreManager()

    # 别名映射
    alias_map = {}
    for main_name, aliases in CHANNEL_MAPPING.items():
        for alias in aliases:
            alias_map[alias] = main_name

    # 读取现有 ip 文件，建立 ip_port -> operator 映射
    ip_info = {}
    if os.path.exists(IP_DIR):
        for fname in os.listdir(IP_DIR):
            if not fname.endswith(".txt"):
                continue
            province_operator = fname.replace(".txt", "")
            try:
                with open(os.path.join(IP_DIR, fname), encoding="utf-8") as f:
                    for line in f:
                        ip_port = line.strip()
                        if ip_port:
                            ip_info[ip_port] = province_operator
            except Exception as e:
                print(f"⚠️ 读取 {fname} 失败：{e}")

    # 读取 zubo.txt 并按频道分组
    channel_sources = defaultdict(list)
    with open(ZUBO_FILE, encoding="utf-8") as f:
        for line in f:
            if "," not in line:
                continue

            ch_name, url = line.strip().split(",", 1)
            ch_main = alias_map.get(ch_name, ch_name)
            m = re.match(r"http://([^/]+)/", url)
            if not m:
                continue

            ip_port = m.group(1)
            operator = ip_info.get(ip_port, "未知")
            
            channel_sources[ch_main].append({
                'url': url,
                'operator': operator,
                'ip_port': ip_port
            })

    print(f"🚀 开始智能检测（共 {len(channel_sources)} 个频道）")
    print(f"⏰ 时间限制: {MAX_RUNTIME/3600:.1f}小时")

    # 按源数量排序，先处理源少的频道（这样可以快速获得结果）
    sorted_channels = sorted(channel_sources.items(), key=lambda x: len(x[1]))
    
    valid_sources_per_channel = {}
    channels_processed = 0
    total_sources_checked = 0
    total_sources_found = 0

    for channel, sources in sorted_channels:
        # 检查是否超时
        elapsed = time.time() - start_time
        if elapsed > MAX_RUNTIME:
            print(f"⏰ 达到时间限制（{elapsed/60:.1f}分钟），停止检测。已处理 {channels_processed}/{len(sorted_channels)} 个频道")
            break

        channels_processed += 1
        total_sources = len(sources)
        
        # 显示进度
        progress = (channels_processed / len(sorted_channels)) * 100
        time_left = (MAX_RUNTIME - elapsed) / 60 if elapsed < MAX_RUNTIME else 0
        print(f"\n  [{channels_processed}/{len(sorted_channels)}] {progress:.1f}% 📺 检测频道: {channel}")
        print(f"    总源数: {total_sources} | 已用时间: {elapsed/60:.1f}分钟 | 剩余时间: {time_left:.1f}分钟")
        
        # ===== 第一阶段：快速检测，筛选可能可用的源 =====
        # 如果源太多，进行抽样
        if total_sources > MAX_SOURCES_PER_CHANNEL_CHECK * 2:
            # 分层抽样：优先保留评分高的源
            sources_with_scores = []
            for s in sources:
                score = score_manager.scores.get(s['url'], {}).get('score', 50)
                sources_with_scores.append((s, score))
            
            # 按评分排序，取前N个
            sources_with_scores.sort(key=lambda x: x[1], reverse=True)
            
            # 保留高分源，再随机补充一些低分源以防遗漏
            high_score_count = min(MAX_SOURCES_PER_CHANNEL_CHECK, len(sources_with_scores))
            sources_to_fast_check = [s[0] for s in sources_with_scores[:high_score_count]]
            
            # 如果还有名额，随机补充一些
            if len(sources_to_fast_check) < MAX_SOURCES_PER_CHANNEL_CHECK and len(sources_with_scores) > high_score_count:
                remaining = sources_with_scores[high_score_count:]
                random_count = min(MAX_SOURCES_PER_CHANNEL_CHECK - len(sources_to_fast_check), len(remaining))
                random_samples = random.sample(remaining, random_count)
                sources_to_fast_check.extend([s[0] for s in random_samples])
        else:
            sources_to_fast_check = sources

        print(f"    第一阶段快速检测: {len(sources_to_fast_check)}/{total_sources} 个源")
        
        # 执行快速检测
        fast_urls = [s['url'] for s in sources_to_fast_check]
        fast_results = fast_checker.batch_check_fast(fast_urls, max_workers=20)
        
        # 找出快速检测通过的源
        fast_passed = []
        for source in sources_to_fast_check:
            if fast_results.get(source['url'], (False, None))[0]:
                fast_passed.append(source)
        
        print(f"    快速检测通过: {len(fast_passed)}/{len(sources_to_fast_check)}")
        
        # 如果没有快速通过的源，继续下一频道
        if not fast_passed:
            print(f"    ⚠️ 没有可用源，跳过")
            valid_sources_per_channel[channel] = []
            continue
        
        # ===== 第二阶段：对快速通过的源进行完整检测 =====
        # 限制完整检测的数量
        if len(fast_passed) > MAX_SOURCES_PER_CHANNEL:
            # 如果太多，按评分排序后取前N个
            fast_passed_with_scores = []
            for s in fast_passed:
                score = score_manager.scores.get(s['url'], {}).get('score', 50)
                fast_passed_with_scores.append((s, score))
            
            fast_passed_with_scores.sort(key=lambda x: x[1], reverse=True)
            sources_to_full_check = [s[0] for s in fast_passed_with_scores[:MAX_SOURCES_PER_CHANNEL]]
        else:
            sources_to_full_check = fast_passed

        print(f"    第二阶段完整检测: {len(sources_to_full_check)}/{len(fast_passed)} 个源")
        
        # 执行完整检测
        full_urls = [s['url'] for s in sources_to_full_check]
        full_results = standard_checker.batch_check(full_urls, max_workers=10)
        
        # 收集完整检测通过的源
        available_sources = []
        for source in sources_to_full_check:
            url = source['url']
            success, response_time = full_results.get(url, (False, None))
            
            if success:
                # 更新评分
                score_manager.update_score(url, True, response_time)
                available_sources.append({
                    'url': url,
                    'operator': source['operator'],
                    'ip_port': source['ip_port'],
                    'score': score_manager.scores.get(url, {}).get('score', 50),
                    'response_time': response_time
                })
                total_sources_found += 1
            else:
                score_manager.update_score(url, False)
            
            total_sources_checked += 1
        
        # 按评分排序，取前MAX_SOURCES_PER_CHANNEL个
        available_sources.sort(key=lambda x: x['score'], reverse=True)
        valid_sources_per_channel[channel] = available_sources[:MAX_SOURCES_PER_CHANNEL]
        
        print(f"    ✅ 最终可用: {len(valid_sources_per_channel[channel])}/{len(available_sources)} 个")
        
        # 如果可用源比例很低，记录下来供后续分析
        if available_sources and len(available_sources) / len(sources_to_full_check) < MIN_SUCCESS_RATE:
            print(f"    ⚠️ 注意: 该频道可用源比例较低 ({len(available_sources)}/{len(sources_to_full_check)})")

    # 统计和总结
    elapsed_total = time.time() - start_time
    print(f"\n{'='*50}")
    print(f"✅ 检测完成统计")
    print(f"   总运行时间: {elapsed_total/60:.1f} 分钟")
    print(f"   处理频道数: {channels_processed}/{len(sorted_channels)}")
    print(f"   检测源总数: {total_sources_checked}")
    print(f"   发现可用源: {total_sources_found}")
    print(f"   最终保留源: {sum(len(v) for v in valid_sources_per_channel.values())}")
    print(f"{'='*50}\n")

    # 统计可用IP
    playable_ips = set()
    for sources in valid_sources_per_channel.values():
        for source in sources:
            playable_ips.add(source['ip_port'])

    print(f"📊 可播放 IP 共 {len(playable_ips)} 个")

    # 更新IP文件（只保留可用IP）
    operator_playable_ips = defaultdict(set)
    for ip_port in playable_ips:
        operator = ip_info.get(ip_port, "未知")
        operator_playable_ips[operator].add(ip_port)

    for operator, ip_set in operator_playable_ips.items():
        target_file = os.path.join(IP_DIR, operator + ".txt")
        try:
            with open(target_file, "w", encoding="utf-8") as wf:
                for ip_p in sorted(ip_set):
                    wf.write(ip_p + "\n")
            print(f"📥 写回 {target_file}，共 {len(ip_set)} 个可用地址")
        except Exception as e:
            print(f"❌ 写回 {target_file} 失败：{e}")

    # 生成IPTV.txt（支持多源，格式优化）
    beijing_now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    disclaimer_url = "https://kakaxi-1.asia/LOGO/Disclaimer.mp4"

    try:
        with open(IPTV_FILE, "w", encoding="utf-8") as f:
            f.write(f"更新时间: {beijing_now}（北京时间）\n")
            f.write(f"检测用时: {elapsed_total/60:.1f} 分钟\n")
            f.write(f"每组频道提供 {MAX_SOURCES_PER_CHANNEL} 个备用源，播放器可自动切换\n\n")
            f.write("更新时间,#genre#\n")
            f.write(f"{beijing_now},{disclaimer_url}\n\n")

            for category, ch_list in CHANNEL_CATEGORIES.items():
                f.write(f"{category},#genre#\n")
                for ch in ch_list:
                    if ch in valid_sources_per_channel and valid_sources_per_channel[ch]:
                        sources = valid_sources_per_channel[ch]
                        for i, source in enumerate(sources, 1):
                            # 格式：频道名,URL$运营商 [备用N] (响应时间)
                            if len(sources) > 1:
                                f.write(f"{ch},{source['url']}$运营:{source['operator']} [备用{i}] ({source.get('response_time', 0):.1f}s)\n")
                            else:
                                f.write(f"{ch},{source['url']}$运营:{source['operator']} ({source.get('response_time', 0):.1f}s)\n")
                    else:
                        # 没有可用源的频道，添加注释
                        f.write(f"# {ch},暂无可用源\n")
                f.write("\n")
        
        # 生成M3U格式
        generate_m3u(valid_sources_per_channel, beijing_now, elapsed_total)
        
        print(f"🎯 IPTV.txt 生成完成，共覆盖 {len([v for v in valid_sources_per_channel.values() if v])} 个有源的频道")
    except Exception as e:
        print(f"❌ 写 IPTV.txt 失败：{e}")

def generate_m3u(channel_sources, update_time, elapsed_time):
    """生成M3U格式的播放列表（优化版）"""
    m3u_file = "IPTV.m3u"
    try:
        with open(m3u_file, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(f'#EXTINF:-1 tvg-name="更新时间" group-title="系统信息",{update_time} (检测用时:{elapsed_time/60:.1f}分钟)\n\n')
            
            for channel, sources in channel_sources.items():
                if not sources:
                    continue
                    
                for i, source in enumerate(sources, 1):
                    # 添加更详细的标签
                    tags = []
                    tags.append(f"tvg-name=\"{channel}\"")
                    tags.append(f"tvg-logo=\"https://example.com/logo/{channel}.png\"")
                    tags.append("group-title=\"自动分类\"")
                    
                    if len(sources) > 1:
                        title = f"{channel} [备用{i}]"
                        tags.append(f"backup=\"{i}\"")
                    else:
                        title = channel
                    
                    # 添加响应时间信息
                    if source.get('response_time'):
                        tags.append(f"response-time=\"{source['response_time']:.1f}\"")
                    
                    f.write(f"#EXTINF:-1 {' '.join(tags)},{title}\n")
                    f.write(f"{source['url']}\n")
        
        print(f"📺 M3U文件生成完成: {m3u_file}")
    except Exception as e:
        print(f"❌ 生成M3U失败：{e}")

# ===============================
# 新增：快速切换支持文件
def generate_quick_switch_support():
    """生成支持快速切换的辅助文件"""
    quick_file = "quick_switch.json"
    try:
        if os.path.exists(IPTV_FILE):
            channel_map = {}
            with open(IPTV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if "," in line and not line.startswith("#") and not line.startswith("更新时间"):
                        parts = line.strip().split(",")
                        if len(parts) >= 2:
                            ch_name = parts[0]
                            url = parts[1].split("$")[0]  # 去掉备注
                            if ch_name not in channel_map:
                                channel_map[ch_name] = []
                            channel_map[ch_name].append(url)
            
            # 保存为JSON
            with open(quick_file, "w", encoding="utf-8") as f:
                json.dump({
                    "update_time": datetime.now().isoformat(),
                    "channels": channel_map
                }, f, ensure_ascii=False, indent=2)
            
            print(f"⚡ 快速切换支持文件生成: {quick_file}")
    except Exception as e:
        print(f"❌ 生成快速切换文件失败：{e}")

# ===============================
# 文件推送
def push_all_files():
    print("🚀 推送所有更新文件到 GitHub...")
    try:
        os.system('git config --global user.name "github-actions"')
        os.system('git config --global user.email "github-actions@users.noreply.github.com"')
    except Exception:
        pass

    os.system("git add 计数.txt || true")
    os.system("git add ip/*.txt || true")
    os.system("git add IPTV.txt || true")
    os.system("git add IPTV.m3u || true")
    os.system("git add source_scores.json || true")
    os.system("git add quick_switch.json || true")
    os.system('git commit -m "自动更新：多源检测优化" || echo "⚠️ 无需提交"')
    os.system("git push origin main || echo '⚠️ 推送失败'")

# ===============================
# 主执行逻辑
if __name__ == "__main__":
    # 确保目录存在
    os.makedirs(IP_DIR, exist_ok=True)
    os.makedirs(RTP_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)

    run_count = first_stage()

    if run_count % 10 == 0:
        second_stage()
        third_stage()
        generate_quick_switch_support()
    else:
        print("ℹ️ 本次不是 10 的倍数，跳过第二、三阶段")

    push_all_files()
