import requests
import lxml
from lxml import etree
import subprocess
import os
import json
import re
import logging
import sys
import time

class BangumiDownloader:

    HEADERS = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Origin": "https://www.bilibili.com",
        "Referer": "https://www.bilibili.com/anime/?spm_id_from=333.1007.0.0",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    }

    BASE_PLAYURL = 'https://api.bilibili.com/pgc/player/web/v2/playurl?support_multi_audio=true'

    def __init__(self, user_cookie,log_level=logging.INFO):
        self.desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        self.user_cookie = user_cookie
        logging.basicConfig(level=log_level, format='%(asctime)s - %(message)s', datefmt='%m-%d %H:%M:%S')

    def validate_url(self,url):
        ep_pattern = re.compile(r'play\/ep\d{6}')
        ss_pattern = re.compile(r'play\/ss\d{5}')
        if ep_pattern.search(url):
            return "ep"
        elif ss_pattern.search(url):
            return "ss"
        else:
            return None

    def send_response(self, url):
        try:
            with requests.Session() as s:
                response = s.get(url, headers=self.HEADERS, cookies=self.user_cookie)
                response.raise_for_status()
                data = response.json()
            return data
        except requests.RequestException as e:
            logging.error(f"网络请求失败: {e}")
            return None

    def get_response(self,url):
        try:
            response = requests.get(url=url, headers=self.HEADERS)
            response.raise_for_status()  # 这行会在HTTP错误时触发异常
        except requests.RequestException as e:
            logging.error(f"网络似乎开小差了: {e}")
            return None
        try:
            html = etree.HTML(response.text)
            script_tags = html.xpath('//script[@id="__NEXT_DATA__"]')
            json_content = json.loads(script_tags[0].text)
            episode_list = json_content.get('props', {}).get('pageProps', {}).get('dehydratedState', {}).get('queries', [{}])[
                0].get('state', {}).get('data', {}).get('seasonInfo', {}).get('mediaInfo', {}).get('episodes',{})
            return episode_list
        except Exception as e:
            logging.error(f"获取响应时出现错误: {e}")
            return None

    def get_episode_info(self, url, episode_list):
        try:
            # 从 URL 中提取 episode_id
            match = re.search(r'play\/(.*?)\?', url)
            episode_id = re.search(r'\d{6}', str(match)).group()
            episode_id = int(episode_id)
        except AttributeError:
            logging.error(f"无法从你输入的url提取出该集的ID号，请重新检查你的url: {url}")
            return None
        # 在 episode_list 中查找与 episode_id 匹配的 episode
        episode_info = next((d for d in episode_list if d['ep_id'] == episode_id), None)
        if episode_info is None:
            logging.error(f"没有匹配到该集的信息: ep_id:{episode_id}")
        else:
            logging.info(f"正在匹配该集信息:ep_id{episode_id}")

        return episode_info


    def get_title(self, episode_info):
        title = episode_info.get('playerEpTitle', {})
        return title

    def get_playurl(self, episode_info):
        avid = episode_info['aid']
        cid = episode_info['cid']
        playurl = self.BASE_PLAYURL+ "&avid=" + str(avid) + "&cid=" + str(cid)+ '&qn=112&fnver=0&fnval=4048'
        return playurl

    def get_quality_options(self, script_content, title):
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
        # 尝试从'dash'获取质量选项
        try:
            dash_result = script_content["result"]['video_info']["dash"]
            for video_info in dash_result["video"]:
                quality = video_info["id"]
                if quality not in quality_id_options:
                    quality_id_options.append(quality)
        except KeyError:
            # 如果用户不是会员，我们只提供1080P选项
            logging.info("你似乎不是会员，只能下载1080P的三分钟试看视频")
            return ['80'], ['1080P 高清']
        quality_list = []
        for id in quality_id_options:
            id = str(id)
            if id in quality_dict:  # Check if the id exists in the dictionary
                quality_list.append(quality_dict[id])
            else:
                logging.info(f"此视频没有该清晰度，ID:{id} ")
        return quality_id_options, quality_list

    def select_quality(self, quality_id_options, quality_list):
        print('你可以选的清晰度有:')
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

    def get_video_and_audio_urls(self, url, quality_id, session):
        response = session.get(url, headers=self.HEADERS,cookies=self.user_cookie)
        data = response.json()
        try:
            dash_result = data["result"]['video_info']["dash"]
            for video_info in dash_result["video"]:
                if video_info["id"] == quality_id:
                    video_url = video_info["baseUrl"]
                    break
            audio_url = dash_result['audio'][0]['baseUrl']
        except KeyError:
            video_url = data['result']['video_info']['durl'][0]['url']
            audio_url = None
        return video_url, audio_url

    def download_file(self, url, filename, session):
        try:
            r = session.get(url, stream=True, headers=self.HEADERS, timeout=60)
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        except Exception as e:
            print(f"无法从指定url下载文件 {url}. 错误: {e}")


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
            run_ffmpeg_command(ffmpeg_command)
        except Exception as e:
            logging.error(f"无法合并视频和音频. Error: {e}")

    def process_video(self, url, title):
        with requests.Session() as s:
            # 获取视频清晰度
            quality_id_options, quality_list = self.get_quality_options(self.send_response(url), title)

            # 用户选择清晰度
            index, quality = self.select_quality(quality_id_options, quality_list)
            if index is not None:
                quality_id = quality_id_options[index]
                url += "&qn=" + str(quality_id)

            video_filename = os.path.join(self.desktop_path, "video.m4s")
            audio_filename = os.path.join(self.desktop_path, "audio.m4s")
            output_file = os.path.join(self.desktop_path, str(title) + '_' + quality + ".mp4")

            while os.path.exists(output_file):
                time.sleep(1)
                user_input = input(f"文件 '{output_file}' 已存在。要重新下载它吗？(y/n): ")
                if user_input.lower() == 'y':
                    os.remove(output_file)
                    break
                elif user_input.lower() == 'n':
                    logging.info("程序自动退出")
                    sys.exit(0)
                else:
                    print("无效的数据！请重新输入")

            # 获取视频和音频URL
            video_url, audio_url = self.get_video_and_audio_urls(url, quality_id, s)

            logging.info('正在下载视频数据...')
            self.download_file(video_url, video_filename, s)

            if audio_url:  # 如果有音频文件，下载并合并
                logging.info('正在下载音频数据...')
                self.download_file(audio_url, audio_filename, s)
                logging.info('正在合并中...')
                self.merge_video_audio_to_mp4(video_filename, audio_filename, output_file)
                os.remove(audio_filename)
            else:  # 如果没有音频文件，直接重命名视频文件
                os.rename(video_filename, output_file)

            # 确保删除video.m4s文件
            if os.path.exists(video_filename):
                os.remove(video_filename)

            logging.info('下载完成!')

    def download_bangumi(self, url):
        title = None
        episode_list = None
        playurl = None
        try:
            while True:
                url_type = self.validate_url(url)
                if url_type == "ep":
                    logging.info('正在获取数据...')
                    episode_list = self.get_response(url)
                    episode_info = self.get_episode_info(url, episode_list)
                    title = self.get_title(episode_info)
                    playurl = self.get_playurl(episode_info)
                    self.process_video(playurl, title)
                    break
                elif url_type == "ss":
                    logging.error(
                        "输入的URL不可用，请确保您的URL格式为 :'https://www.bilibili.com/bangumi/play/epxxxxxx/...'。")
                    break
                else:
                    logging.error("输入的URL无效，请重新输入正确的URL。")
                    break
        except Exception as e:
            logging.error(f"bangumi脚本运行过程中出现错误: {e}")
            if episode_list:
                logging.error("自动下载episode_list.json文件")
                with open('episode_list.json', 'w', encoding='utf-8') as fp:
                    json.dump(episode_list, fp, ensure_ascii=False, indent=4)
            else:
                logging.error("没有episode_list信息,请手动检查原始网页的html文件")
