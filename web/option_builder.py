"""将用户设置（JSON）转换为 jmcomic 的 JmOption 对象"""

import json
import os
import types


def load_settings(settings_file: str) -> dict:
    from config import DEFAULT_SETTINGS
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                return {**DEFAULT_SETTINGS, **saved}
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings_file: str, settings: dict):
    os.makedirs(os.path.dirname(settings_file), exist_ok=True)
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def build_option_yaml(settings: dict) -> str:
    # 默认指向项目根 downloads/JMComic（与 config.DEFAULT_SETTINGS 一致），
    # 避免缺省时回退到 Windows 风格盘符路径而在 Linux 上生成字面名为 D: 的目录
    download_dir = settings.get('download_dir', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'downloads', 'JMComic')).rstrip('/\\')
    proxy = settings.get('proxy', '')
    thread_image = settings.get('thread_count_image', 20)
    thread_photo = settings.get('thread_count_photo', 3)
    image_suffix = settings.get('image_suffix', None)
    client_impl = settings.get('client_impl', 'api')
    retry_times = settings.get('retry_times', 5)
    zip_enabled = settings.get('zip_enabled', True)
    zip_delete_after = settings.get('zip_delete_after', False)

    # 代理
    if proxy and proxy not in ('null', 'None', ''):
        proxy_line = f"      proxies: {proxy}"
    else:
        proxy_line = "      proxies: null"

    # 后缀
    if not image_suffix or image_suffix in ('null', 'None', ''):
        suffix_line = "    suffix: null"
    else:
        suffix_line = f"    suffix: {image_suffix}"

    # ZIP 由 download_manager 自己处理（更可靠），这里不再配置 jmcomic 插件

    # dir_rule: Bd/Atitle → 每个漫画有自己的文件夹，图片和压缩包都在里面
    yaml_str = f"""log: true
dir_rule:
  rule: Bd / Atitle
  base_dir: {download_dir}
  normalize_zh: null
download:
  cache: false
  image:
    decode: true
{suffix_line}
  threading:
    image: {thread_image}
    photo: {thread_photo}
client:
  impl: {client_impl}
  async_impl: async_api
  retry_times: {retry_times}
  domain: []
  postman:
    type: curl_cffi
    meta_data:
      impersonate: chrome
      headers: null
{proxy_line}
plugins:
  after_init: []
  before_album: []
  after_album: []
  before_photo: []
  after_photo: []
  before_image: []
  after_image: []
"""
    return yaml_str


def build_option(settings: dict):
    """创建 JmOption，自定义图片文件名确保扁平目录下不冲突"""
    from jmcomic import create_option_by_str

    yaml_str = build_option_yaml(settings)
    option = create_option_by_str(yaml_str)

    # 保存原始方法引用
    _original_decide_image_filename = option.decide_image_filename

    def custom_image_filename(self, image):
        """文件名加章节序号前缀：001_00001.jpg，确保同目录下不冲突"""
        photo = getattr(image, 'from_photo', None)
        if photo:
            pidx = str(getattr(photo, 'sort', '0') or '0').zfill(3)
            return f'{pidx}_{_original_decide_image_filename(image)}'
        return _original_decide_image_filename(image)

    option.decide_image_filename = types.MethodType(custom_image_filename, option)
    return option


def build_option_with_extras(settings: dict, extras: dict = None):
    """支持 extras: export_zip, export_pdf, export_long_img"""
    merged = dict(settings)
    if extras:
        if extras.get('export_pdf'):
            merged['zip_enabled'] = False
        elif extras.get('export_long_img'):
            merged['zip_enabled'] = False

    option = build_option(merged)

    if extras and extras.get('export_pdf'):
        yaml_str = build_option_yaml(merged)
        yaml_str = yaml_str.replace(
            'after_album: []',
            """  after_album:
    - plugin: img2pdf
      kwargs:
        dir_rule: Bd / Atitle
        filename_rule: '[JM{{Aid}}] {{Atitle}}.pdf'"""
        )
        from jmcomic import create_option_by_str
        return create_option_by_str(yaml_str)

    if extras and extras.get('export_long_img'):
        yaml_str = build_option_yaml(merged)
        yaml_str = yaml_str.replace(
            'after_album: []',
            """  after_album:
    - plugin: long_img
      kwargs:
        dir_rule: Bd / Atitle
        filename_rule: '[JM{{Aid}}] {{Atitle}}.png'"""
        )
        from jmcomic import create_option_by_str
        return create_option_by_str(yaml_str)

    return option
