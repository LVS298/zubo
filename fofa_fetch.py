import os
import re
import requests
import base64
import time
import concurrent.futures
import subprocess
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

# ===============================
# 配置区
FOFA_CONFIG = {
    "email": "1762791419@qq.com",  # 替换为你的FOFA邮箱
    "key": "955eb1006ee827d036b8af26427ebf59",               # 替换为你的FOFA API Key
    "query": '"udpxy" && country="CN" && is_honeypot=false',
    "size": 1000,  # 每次获取数量（免费用户最大100）
    "max_pages": 10,  # 最大翻页数
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

COUNTER_FILE = "计数.txt"
IP_DIR = "ip"
RTP_DIR = "rtp"
ZUBO_FILE = "zubo.txt"
IPTV_FILE = "IPTV.txt"

# ===============================
# 分类与映射配置（保持原有不变）
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
        "NewTV中国功夫", "4K乐享超清","黑莓电影", "环球影视", "精彩影视", "古早影院",
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

# ===== 映射（别名 -> 标准名）保持原有不变 =====
CHANNEL_MAPPING = {
    "CCTV-1综合": ["CCTV-1", "CCTV-1 HD", "CCTV1 HD", "CCTV1", "CCTV1HD"],
    "CCTV-2财经": ["CCTV-2", "CCTV-2 HD", "CCTV2 HD", "CCTV2", "CCTV2HD"],
    "CCTV-3综艺": ["CCTV-3", "CCTV-3 HD", "CCTV3 HD", "CCTV3", "CCTV3HD"],
    "CCTV-4中文国际": ["CCTV-4", "CCTV-4 HD", "CCTV4 HD", "CCTV4", "CCTV4"],
    "CCTV-4欧洲": ["CCTV-4欧洲", "CCTV-4欧洲", "CCTV4欧洲 HD", "CCTV-4 欧洲", "CCTV-4中文国际欧洲", "CCTV4", "CCTV4欧洲HD"],
    "CCTV-4美洲": ["CCTV-4美洲", "CCTV-4北美", "CCTV4美洲 HD", "CCTV-4 美洲", "CCTV-4中文国际美洲", "CCTV4", "CCTV-4 美洲"],
    "CCTV-5体育": ["CCTV-5", "CCTV-5 HD", "CCTV5 HD", "CCTV5", "CCTV5HD"],
    "少儿天地": ["睛彩少儿HD", "精彩连播"],
    "乐龄学堂": ["睛彩学堂HD", "精彩连播"],
    "动漫秀场": ["动漫秀场", "睛彩亲子HD", "精彩连播"],
    "综艺咖秀": ["睛彩综艺HD", "精彩连播"],
    "爱宠宠物": ["睛彩爱宠HD", "精彩连播"],
    "新视觉HD": ["新视觉"],
    "古早影院": ["古早影院HD"],
    "CCTV-5+体育赛事": ["CCTV-5+", "CCTV-5+ HD", "CCTV5+HD", "CCTV5+"],
    "CCTV-6电影": ["CCTV-6", "CCTV-6 HD", "CCTV6 HD", "CCTV6", "CCTV6HD"],
    "CCTV-7国防军事": ["CCTV-7", "CCTV-7 HD", "CCTV7 HD", "CCTV7", "CCTV7 HD"],
    "CCTV-8电视剧": ["CCTV-8", "CCTV-8 HD", "CCTV8 HD", "CCTV8", "CCTV8HD"],
    "CCTV-9纪录": ["CCTV-9", "CCTV-9 HD", "CCTV9 HD", "CCTV9", "CCTV9HD"],
    "CCTV-10科教": ["CCTV-10", "CCTV-10 HD", "CCTV10 HD", "CCTV10", "CCTV10 HD"],
    "CCTV-11戏曲": ["CCTV-11", "CCTV-11 HD", "CCTV11 HD", "CCTV11", "CCTV11HD"],
    "CCTV-12社会与法": ["CCTV-12", "CCTV-12 HD", "CCTV12 HD", "CCTV12", "CCTV12HD"],
    "CCTV-13新闻": ["CCTV-13", "CCTV-13 HD", "CCTV13 HD", "CCTV13", "CCTV13HD"],
    "CCTV-14少儿": ["CCTV-14", "CCTV-14 HD", "CCTV14 HD", "CCTV14", "CCTV14 HD"],
    "CCTV-15音乐": ["CCTV-15", "CCTV-15 HD", "CCTV15 HD", "CCTV15", "CCTV15 HD"],
    "CCTV-16奥林匹克": ["CCTV-16", "CCTV-16 HD", "CCTV-16HD", "CCTV-16 4K", "CCTV16", "CCTV-16奥林匹克4K"],
    "CCTV-17农业农村": ["CCTV-17", "CCTV-17 HD", "CCTV17 HD", "CCTV17", "CCTV17HD"],
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
    "CHC影迷电影": ["CHC影迷电影HD", "CHC-影迷电影", "影迷电影", "chc影迷电影高清"],
    "CHC家庭影院": ["CHC-家庭影院", "CHC家庭影院HD", "chc家庭影院高清"], 
    "CHC动作电影": ["CHC-动作电影", "CHC动作电影HD", "chc动作电影高清"],
    "淘电影": ["IPTV淘电影", "北京IPTV淘电影", "北京淘电影", "淘电影HD", "淘剧场HD"],
    "淘剧场": ["IPTV淘剧场", "北京IPTV淘剧场", "北京淘剧场"],
    "淘4K": ["IPTV淘4K", "北京IPTV4K超高清", "北京淘4K", "北京IPTV淘4K", "北京IPTV4K超清", "4K超清", "北京4K超清"],
    "淘娱乐": ["IPTV淘娱乐", "北京IPTV淘娱乐", "北京淘娱乐", "淘娱乐HD"],
    "淘BABY": ["IPTV淘BABY", "北京IPTV淘BABY", "北京淘BABY", "IPTV淘baby", "北京IPTV淘baby", "北京淘baby", "淘Baby", "淘宝贝", "淘BabyHD"],
    "淘萌宠": ["IPTV淘萌宠", "北京IPTV萌宠TV", "北京淘萌宠", "萌宠TV", "萌宠TVHD" ],
    "重温经典": ["重温经典HD"],
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
    "茶频道": ["湖南茶频道", "茶频道HD"],
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
    "卡酷少儿": ["北京KAKU少儿", "BRTV卡酷少儿", "北京卡酷少儿", "卡酷动画", "卡酷少儿HD"],
    "哈哈炫动": ["炫动卡通", "上海哈哈炫动"],
    "优漫卡通": ["江苏优漫卡通", "优漫漫画"],
    "金鹰卡通": ["湖南金鹰卡通"],
    "中国交通": ["中国交通频道"],
    "中国天气": ["中国天气频道"],
    "亲子趣学": ["睛彩亲子4K"],
    "华数4K": ["华数低于4K", "华数4K电影", "华数爱上4K", "爱上4K"],
    "华数光影": ["光影", "光影HD"],
    "华数星影": ["星影", "星影HD"],
    "华数精选": ["精选", "精选HD"],
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
    "华数动画": ["华数卡通", "IPTV少儿动画", "IPTV少儿动画HD"],
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
# FOFA API 获取函数
def search_fofa_api(email, key, query, size=100, page=1):
    """通过FOFA API搜索数据"""
    # Base64编码查询语句
    qbase64 = base64.b64encode(query.encode('utf-8')).decode('utf-8')
    
    # 构建API URL
    api_url = "https://fofa.info/api/v1/search/all"
    params = {
        'email': email,
        'key': key,
        'qbase64': qbase64,
        'size': min(size, 100),  # 单次最大100
        'page': page,
        'fields': 'host,ip,port,protocol,country,province,city,isp'
    }
    
    try:
        print(f"  请求第{page}页，每页{params['size']}条...")
        response = requests.get(api_url, params=params, timeout=30)
        data = response.json()
        
        if data.get('error'):
            print(f"  ❌ API错误: {data['error']}")
            return None, 0
        
        results = data.get('results', [])
        total = data.get('size', 0)  # 实际返回数量
        
        # 提取host字段（IP:端口）
        hosts = []
        for item in results:
            if item and len(item) > 0:
                host = item[0]  # host字段包含IP:端口
                if host:
                    hosts.append(host)
        
        print(f"  ✅ 获取到 {len(hosts)} 个地址")
        return hosts, total
        
    except Exception as e:
        print(f"  ❌ API请求失败: {e}")
        return None, 0

def get_fofa_data_paginated():
    """分页获取所有FOFA数据"""
    print("🔍 使用FOFA API获取udpxy数据...")
    
    email = FOFA_CONFIG['email']
    key = FOFA_CONFIG['key']
    query = FOFA_CONFIG['query']
    max_pages = FOFA_CONFIG['max_pages']
    page_size = min(FOFA_CONFIG['size'], 100)
    
    all_hosts = []
    
    for page in range(1, max_pages + 1):
        hosts, total = search_fofa_api(email, key, query, page_size, page)
        
        if hosts is None:
            break
        
        if not hosts:
            print(f"  第{page}页无数据，停止翻页")
            break
        
        all_hosts.extend(hosts)
        
        # 如果返回数量小于请求数量，说明是最后一页
        if total < page_size:
            print(f"  已获取全部数据")
            break
        
        # 避免请求过快
        time.sleep(1)
    
    # 去重
    unique_hosts = list(dict.fromkeys(all_hosts))
    print(f"✅ 总计获取到 {len(unique_hosts)} 个唯一IP地址")
    
    return unique_hosts

def get_isp_from_api(ip):
    """通过API获取运营商信息"""
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?lang=zh-CN", timeout=10)
        data = response.json()
        
        isp_raw = (data.get("isp") or "").lower()
        
        if "telecom" in isp_raw or "ct" in isp_raw or "chinatelecom" in isp_raw:
            return "电信"
        elif "unicom" in isp_raw or "cu" in isp_raw or "chinaunicom" in isp_raw:
            return "联通"
        elif "mobile" in isp_raw or "cm" in isp_raw or "chinamobile" in isp_raw:
            return "移动"
        
        return "未知"
    except Exception:
        return "未知"

def get_isp_by_regex(ip):
    """通过IP段判断运营商"""
    first_octet = int(ip.split('.')[0])
    
    # 电信常见段
    telecom_ranges = [1, 14, 42, 43, 58, 59, 60, 61, 106, 110, 111, 112, 113, 114, 115, 
                      116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 139, 
                      171, 175, 180, 182, 183, 184, 185, 186, 187, 188, 189, 218, 219, 
                      220, 221, 222, 223]
    
    # 联通常见段
    unicom_ranges = [14, 27, 42, 43, 58, 59, 60, 61, 106, 110, 111, 112, 113, 114, 115,
                     116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 153,
                     175, 180, 182, 183, 184, 185, 186, 187, 188, 189, 211, 223]
    
    # 移动常见段
    mobile_ranges = [36, 37, 38, 39, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
                     120, 134, 135, 136, 137, 138, 139, 150, 151, 152, 157, 158, 159,
                     170, 178, 182, 183, 184, 187, 188, 189, 223]
    
    if first_octet in telecom_ranges:
        return "电信"
    elif first_octet in unicom_ranges:
        return "联通"
    elif first_octet in mobile_ranges:
        return "移动"
    
    return "未知"

# ===============================
# 第一阶段：获取IP并分类
def first_stage():
    """获取IP地址并分类"""
    os.makedirs(IP_DIR, exist_ok=True)
    
    # 获取FOFA数据
    ips = get_fofa_data_paginated()
    
    if not ips:
        print("❌ 未能获取到任何IP地址")
        return 0
    
    # 解析IP地址，获取地理位置和运营商信息
    province_isp_dict = {}
    processed = 0
    
    for ip_port in ips:
        processed += 1
        if processed % 50 == 0:
            print(f"  处理进度: {processed}/{len(ips)}")
        
        try:
            # 提取IP（可能包含端口）
            host = ip_port.split(":")[0] if ":" in ip_port else ip_port
            
            # 验证IP格式
            if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
                continue
            
            # 获取运营商
            isp = get_isp_from_api(host)
            if isp == "未知":
                isp = get_isp_by_regex(host)
            
            if isp == "未知":
                continue
            
            # 获取省份信息
            try:
                res = requests.get(f"http://ip-api.com/json/{host}?lang=zh-CN", timeout=10)
                data = res.json()
                province = data.get("regionName", "未知")
            except Exception:
                province = "未知"
            
            fname = f"{province}{isp}.txt"
            province_isp_dict.setdefault(fname, set()).add(ip_port)
            
        except Exception as e:
            print(f"⚠️ 解析 {ip_port} 出错：{e}")
            continue
    
    # 保存到文件
    count = get_run_count() + 1
    save_run_count(count)
    
    for filename, ip_set in province_isp_dict.items():
        path = os.path.join(IP_DIR, filename)
        try:
            with open(path, "a", encoding="utf-8") as f:
                for ip_port in sorted(ip_set):
                    f.write(ip_port + "\n")
            print(f"✅ {path} 已追加写入 {len(ip_set)} 个 IP")
        except Exception as e:
            print(f"❌ 写入 {path} 失败：{e}")
    
    print(f"✅ 第一阶段完成，当前轮次：{count}")
    return count

# ===============================
# 第二、三阶段函数保持原样（与之前相同）
def second_stage():
    """生成zubo.txt"""
    print("🔔 第二阶段触发：生成 zubo.txt")
    if not os.path.exists(IP_DIR):
        print("⚠️ ip 目录不存在，跳过第二阶段")
        return

    combined_lines = []

    if not os.path.exists(RTP_DIR):
        print("⚠️ rtp 目录不存在，无法进行第二阶段组合，跳过")
        return

    for ip_file in os.listdir(IP_DIR):
        if not ip_file.endswith(".txt"):
            continue

        ip_path = os.path.join(IP_DIR, ip_file)
        rtp_path = os.path.join(RTP_DIR, ip_file)

        if not os.path.exists(rtp_path):
            continue

        try:
            with open(ip_path, encoding="utf-8") as f1, open(rtp_path, encoding="utf-8") as f2:
                ip_lines = [x.strip() for x in f1 if x.strip()]
                rtp_lines = [x.strip() for x in f2 if x.strip()]
        except Exception as e:
            print(f"⚠️ 文件读取失败：{e}")
            continue

        if not ip_lines or not rtp_lines:
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

    # 去重
    unique = {}
    for line in combined_lines:
        url_part = line.split(",", 1)[1]
        if url_part not in unique:
            unique[url_part] = line

    try:
        with open(ZUBO_FILE, "w", encoding="utf-8") as f:
            for line in unique.values():
                f.write(line + "\n")
        print(f"🎯 第二阶段完成，写入 {len(unique)} 条记录")
    except Exception as e:
        print(f"❌ 写文件失败：{e}")

def third_stage():
    """多线程检测代表频道生成IPTV.txt"""
    print("🧩 第三阶段：多线程检测代表频道生成 IPTV.txt")

    if not os.path.exists(ZUBO_FILE):
        print("⚠️ zubo.txt 不存在，跳过第三阶段")
        return

    def check_stream(url, timeout=5):
        """检查流是否可播放"""
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_streams", "-i", url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout + 2
            )
            return b"codec_type" in result.stdout
        except Exception:
            return False

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

    # 读取 zubo.txt 并按 ip:port 分组
    groups = {}
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
            groups.setdefault(ip_port, []).append((ch_main, url))

    # 选择代表频道并检测
    def detect_ip(ip_port, entries):
        rep_channels = [u for c, u in entries if c == "CCTV1"]
        if not rep_channels and entries:
            rep_channels = [entries[0][1]]
        playable = any(check_stream(u) for u in rep_channels[:3])
        return ip_port, playable

    print(f"🚀 启动多线程检测（共 {len(groups)} 个 IP）...")
    playable_ips = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(detect_ip, ip, chs): ip for ip, chs in groups.items()}
        for future in concurrent.futures.as_completed(futures):
            try:
                ip_port, ok = future.result()
            except Exception as e:
                print(f"⚠️ 线程检测返回异常：{e}")
                continue
            if ok:
                playable_ips.add(ip_port)

    print(f"✅ 检测完成，可播放 IP 共 {len(playable_ips)} 个")

    valid_lines = []
    seen = set()
    operator_playable_ips = {}

    for ip_port in playable_ips:
        operator = ip_info.get(ip_port, "未知")

        for c, u in groups.get(ip_port, []):
            key = f"{c},{u}"
            if key not in seen:
                seen.add(key)
                valid_lines.append(f"{c},{u}${operator}")
                operator_playable_ips.setdefault(operator, set()).add(ip_port)

    # 写回可用的IP到ip目录（覆盖）
    for operator, ip_set in operator_playable_ips.items():
        target_file = os.path.join(IP_DIR, operator + ".txt")
        try:
            with open(target_file, "w", encoding="utf-8") as wf:
                for ip_p in sorted(ip_set):
                    wf.write(ip_p + "\n")
            print(f"📥 写回 {target_file}，共 {len(ip_set)} 个可用地址")
        except Exception as e:
            print(f"❌ 写回 {target_file} 失败：{e}")

    # 写 IPTV.txt（包含更新时间与分类）
    beijing_now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    disclaimer_url = "https://kakaxi-1.asia/LOGO/Disclaimer.mp4"

    try:
        with open(IPTV_FILE, "w", encoding="utf-8") as f:
            f.write(f"更新时间: {beijing_now}（北京时间）\n\n")
            f.write("更新时间,#genre#\n")
            f.write(f"{beijing_now},{disclaimer_url}\n\n")

            for category, ch_list in CHANNEL_CATEGORIES.items():
                f.write(f"{category},#genre#\n")
                for ch in ch_list:
                    for line in valid_lines:
                        name = line.split(",", 1)[0]
                        if name == ch:
                            f.write(line + "\n")
                f.write("\n")
        print(f"🎯 IPTV.txt 生成完成，共 {len(valid_lines)} 条频道")
    except Exception as e:
        print(f"❌ 写 IPTV.txt 失败：{e}")

# ===============================
# 辅助函数
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

def push_all_files():
    """推送所有更新文件到GitHub"""
    print("🚀 推送所有更新文件到 GitHub...")
    try:
        os.system('git config --global user.name "github-actions"')
        os.system('git config --global user.email "github-actions@users.noreply.github.com"')
    except Exception:
        pass

    os.system("git add 计数.txt || true")
    os.system("git add ip/*.txt || true")
    os.system("git add IPTV.txt || true")
    os.system('git commit -m "自动更新：使用FOFA API获取数据" || echo "⚠️ 无需提交"')
    os.system("git push origin main || echo '⚠️ 推送失败'")

# ===============================
# 主执行逻辑
if __name__ == "__main__":
    # 确保目录存在
    os.makedirs(IP_DIR, exist_ok=True)
    os.makedirs(RTP_DIR, exist_ok=True)
    
    print("=" * 60)
    print("IPTV源自动更新脚本 (使用FOFA API)")
    print("=" * 60)
    
    # 检查配置
    if FOFA_CONFIG['email'] == "your_email@example.com" or FOFA_CONFIG['key'] == "your_api_key":
        print("⚠️ 警告：请先在脚本中配置FOFA的email和key")
        print("   配置位置：FOFA_CONFIG字典中的'email'和'key'字段")
        print("")
        print("如何获取FOFA API密钥：")
        print("1. 访问 https://fofa.info 注册账号")
        print("2. 登录后进入个人中心")
        print("3. 找到并复制API Key")
        print("4. 修改脚本中的配置")
        print("")
        response = input("是否继续（使用免费API）？(y/N): ")
        if response.lower() != 'y':
            exit(0)
    
    # 执行第一阶段（总是执行）
    run_count = first_stage()
    
    # 每10轮执行第二、三阶段
    if run_count % 10 == 0:
        print(f"\n🎯 第{run_count}轮，执行完整检测流程")
        second_stage()
        third_stage()
    else:
        print(f"\nℹ️ 第{run_count}轮，跳过第二、三阶段（每10轮执行一次）")
    
    # 推送文件
    push_all_files()
    
    print("\n✅ 所有任务完成！")
