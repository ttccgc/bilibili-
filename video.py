import requests
import lxml
from lxml import etree
import subprocess
import os
import json
import logging
import sys
import time

# 获取requests的日志记录器
requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.DEBUG)

# 如果还希望看到 `requests` 库的 `DEBUG` 级日志在控制台上，您还需要设置一个日志处理程序：
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)

# 添加处理程序到requests的日志记录器
requests_log.addHandler(handler)

class VideoDownloader:

    HEADERS = {
        'Cache-Control':'max-age = 0',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Referer': 'https://www.bilibili.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    }

    def __init__(self, user_cookie,log_level=logging.INFO):
        self.user_cookie = user_cookie
        self.desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        logging.basicConfig(level=log_level, format='%(asctime)s - %(message)s', datefmt='%m-%d %H:%M:%S')

    def send_response(self, url):
        logging.info("与b站建立新的连接")
        with requests.Session() as s:
            response = s.get(url, headers=self.HEADERS, cookies=self.user_cookie)
        return response

    def get_response(self,url):
        try:
            response = self.send_response(url)
            response.raise_for_status()  # 这行会在HTTP错误时触发异常
        except requests.RequestException as e:
            logging.error(f"网络似乎开小差了: {e}")
            sys.exit(0)
            return None
        try:
            html = etree.HTML(response.text)
            script_tags = html.xpath("//script[contains(text(), 'window.__playinfo__')]")
            json_content = json.loads(script_tags[0].text.split('=', 1)[1])

        except lxml.etree.XPathError as e:
            logging.error(f"bilibili网站结构或内容发生变化，请联系作者更新: {e}")
            return None
        return html,json_content


    def get_title(self,html):
        title=html.xpath("//title/text()")[0]
        return title

    def errorCheck_page_download(self,json_content, title):
        with open(str(title) + '.json', 'w', encoding='utf-8') as fp:
            json.dump(json_content, fp, ensure_ascii=False, indent=4)

    def get_quality_options(self,json_content):
        quality_dict = {
            '120': '4K 超清',
            '116': '1080P 高清60帧',
            '112': '1080P 高码率',
            '80': '1080P 高清',
            '64': '720P 高清',
            '32': '480P 清晰',
            '16': '360P 流畅'
        }
        quality_id_options = []
        try:
            dash_data = json_content["data"]["dash"]
            for video_info in dash_data["video"]:
                quality = video_info["id"]
                if quality not in quality_id_options:
                    quality_id_options.append(quality)
        except KeyError as e:
            logging.error(f"json文件发生变化，请联系作者更新。错误{e}")
        #quality_list以列表的形式储存获取到的该清晰度信息，如'1080P 高清60帧'
        #quality为清晰度信息，如'1080P 高清60帧'
        #quality_id为对应的id值，如'1080P 高清60帧'对应116，用于查找对应视频的链接
        quality_list = []
        for id in quality_id_options:
            id = str(id)
            if id in quality_dict:  # Check if the id exists in the dictionary
                quality_list.append(quality_dict[id])
            else:
                logging.error(f"不支持ID为 {id} 的清晰度")
        return quality_id_options, quality_list

    def select_quality(self,quality_id_options, quality_list):
        print('该视频可选的清晰度有:')
        i = 1
        for option in quality_list:
            print(f"{i}: {option}")
            i += 1
        index = int(input("输入对应编号:")) - 1  # Subtract 1 to get the correct index
        quality = quality_list[index]
        logging.info('你选择了:' + quality)
        if 0 <= index < len(quality_id_options):
            return index, quality
        else:
            logging.error('不存在该清晰度')
            return None

    def get_video_and_audio_urls(self,json_content, quality_id):
        video_info=None
        for video in json_content["data"]["dash"]["video"]:
            if video["id"] == quality_id:
                video_info = video
                break
        try:
            audio_url=json_content["data"]["dash"]["audio"][0]["baseUrl"]
            video_url= video_info["baseUrl"]
            return video_url,audio_url
        except IndexError as e:
            logging.error(f"解析出的json文件发生变化，请联系作者更新。错误{e}")

    def download_file(self, url, filename):
        try:
            r = requests.get(url, stream=True, headers=self.HEADERS, timeout=60)
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        except Exception as e:
            logging.error(f"无法从指定url下载文件 {url}. 错误: {e}")


    def merge_video_audio_to_mp4(self, video_input, audio_input, output_file):
        def run_ffmpeg_command(command):
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       universal_newlines=True, encoding='utf-8')
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    #设置为debug级别的日志，默认不输出视频详细信息
                    logging.debug(output.strip())
        ffmpeg_command = ['ffmpeg', '-i', video_input, '-i', audio_input, '-c', 'copy', output_file]
        try:
            logging.debug("自动生成视频下载数据")
            run_ffmpeg_command(ffmpeg_command)
        except Exception as e:
            logging.error(f"无法合并视频和音频. Error: {e}")

    def process_video(self, url,title,json_content):

        quality_id_options, quality_list = self.get_quality_options(json_content)
        index, quality = self.select_quality(quality_id_options, quality_list)

        if index is not None:
            quality_id = quality_id_options[index]

        video_filename = os.path.join(self.desktop_path, "video.m4s")
        audio_filename = os.path.join(self.desktop_path, "audio.m4s")
        output_file = os.path.join(self.desktop_path, title + '_' + quality + ".mp4")

        while os.path.exists(output_file):
            user_input = input(f"文件 '{output_file}' 已存在。要重新下载它吗？(y/n): ")
            if user_input.lower() == 'y':
                os.remove(output_file)
                break
            elif user_input.lower() == 'n':
                logging.info("程序自动退出")
                sys.exit(0)
            else:
                print("无效的数据！请重新输入")

        video_url, audio_url = self.get_video_and_audio_urls(json_content,quality_id)
        logging.info('正在下载视频数据...')
        self.download_file(video_url, video_filename)
        logging.info('正在下载音频数据...')
        self.download_file(audio_url, audio_filename)
        self.merge_video_audio_to_mp4(video_filename, audio_filename, output_file)

        os.remove(video_filename)
        os.remove(audio_filename)

    def download_video(self, url):
        try:
            html, json_content = self.get_response(url)
            title = self.get_title(html).replace('|', '-').replace('/', '-').strip()

            self.process_video(url,title,json_content)
            logging.info('下载完成!')
        except Exception as e:
            logging.error(f"下载失败. 错误类型: {type(e).__name__}, 错误: {e}")

