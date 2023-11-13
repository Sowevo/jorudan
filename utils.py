import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

name_map = {
    'あさま': {'cn_name': '浅间', 'series': ''},
    'かがやき': {'cn_name': '光辉', 'series': ''},
    'こだま': {'cn_name': '回声', 'series': ''},
    'こまち': {'cn_name': '小町', 'series': ''},
    'さくら': {'cn_name': '樱', 'series': ''},
    'たにがわ': {'cn_name': '谷川', 'series': ''},
    'つばさ': {'cn_name': '翼', 'series': ''},
    'つばめ': {'cn_name': '燕', 'series': ''},
    'つるぎ': {'cn_name': '剑', 'series': ''},
    'とき': {'cn_name': '朱鹭', 'series': ''},
    'なすの': {'cn_name': '那须野', 'series': ''},
    'のぞみ': {'cn_name': '希望', 'series': ''},
    'はくたか': {'cn_name': '白鹰', 'series': ''},
    'はやて': {'cn_name': '疾风', 'series': ''},
    'はやぶさ': {'cn_name': '隼', 'series': ''},
    'ひかり': {'cn_name': '光', 'series': ''},
    'みずほ': {'cn_name': '瑞穗', 'series': ''},
    'やまびこ': {'cn_name': '山彦', 'series': ''}
}


def parse_title(text):
    """
    从标题中解析出车次部分信息
    """
    # 使用正则表达式来匹配信息，允许车型信息可选，并排除括号
    pattern = r'^(.*?)\d+号(?:\((.*?)\))? *\((.*?)行\)の運行表$'
    match = re.match(pattern, text)

    if match:
        name = match.group(1)
        series = match.group(2) if match.group(2) else None
        direction = match.group(3)
        number = re.search(r'\d+', text).group()
    else:
        name = None
        series = None
        direction = None
        number = None
    cn_name = name_map[name]['cn_name'] if name in name_map else name
    return name, cn_name, number, series, direction


def clean_params(url):
    # 解析URL
    parsed_url = urlparse(url)
    # 获取查询参数字典
    params = parse_qs(parsed_url.query)
    # 只保留'lid'参数
    if 'lid' in params:
        new_params = {'lid': params['lid']}
    else:
        new_params = {}
    # 重新构建URL
    new_query = urlencode(new_params, doseq=True)
    new_url = urlunparse(
        (parsed_url.scheme, parsed_url.netloc, parsed_url.path, parsed_url.params, new_query, parsed_url.fragment))
    return new_url
