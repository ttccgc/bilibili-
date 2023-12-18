from static.bilibili爬取.bangumi import BangumiDownloader
from static.bilibili爬取.video import VideoDownloader
import re
import logging

def main():
    url = input('请输入B站视频或番剧的链接：')

    if not re.match(r"https?://www\.bilibili\.com/(video|bangumi)/[a-zA-Z0-9]+", url):
        logging.error("无效的URL!")
        return

    user_input = input("您是否想要手动输入cookie?(不输入则使用默认cookie) (y/n): ").lower()
    user_cookie_value = None
    if user_input == 'y':
        user_cookie_value = input("请输入您的cookie: ")

    user_cookie = {
        "Cookie": user_cookie_value or (
            "buvid3=5ECB2A45-221C-8BCC-B267-75C1A2592D0C55560infoc; b_nut=1696993455; i-wanna-go-back=-1; b_ut=7; _uuid=18F4AD91-D9E4-5748-10BD3-A9F36B1AEB7B55873infoc; buvid4=6FDAE32A-6B6F-5F41-0F11-217FB058DC7756541-023101111-7XDfT9HnZ77a48%2B9fJv0aloRDLISZf45b0t3m0Likq7zuczD07LcEw%3D%3D; rpdid=0z9ZwfQnPW|QwbrtoGg|2th|3w1QQpwJ; header_theme_version=CLOSE; enable_web_push=DISABLE; fingerprint=3c06a5a34826409eea8d993052e480f6; buvid_fp_plain=undefined; CURRENT_BLACKGAP=0; VIP_DEFINITION_GUIDE=1; hit-dyn-v2=1; bp_video_offset_3546562395375856=0; DedeUserID=266991838; DedeUserID__ckMd5=536abd07f30bfd00; LIVE_BUVID=AUTO5816972922943682; CURRENT_QUALITY=112; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2OTc4OTc4NjIsImlhdCI6MTY5NzYzODYwMiwicGx0IjotMX0.nQxrrjmud8AdJPZX6scDpInzlzCdY46aljz6IEHnCB4; bili_ticket_expires=1697897802; home_feed_column=5; VIP_CONTENT_REMIND=1; buvid_fp=3c06a5a34826409eea8d993052e480f6; PVID=2; VIP_DEFINITION_REMIND=1; SESSDATA=2fadf7ea%2C1713340781%2C7c6a6%2Aa1CjCNrCgYjRwYtDlM6ylhCT6Pf9B8lPRltMIGSlzEUH_1CLR168rGmwfHQR1eyzKIhYwSVnRSaGFLdnV4NEs1d0xTU1FlaGpEX3NtTWJYUUpGaDJoRU1pa1c2UG90T3ZISVJIc0wxUTBOOS1XZEdLTTQ4TGNGSEZoUXhFZGt4T0RDeEdQa0g2NnN3IIEC; bili_jct=e83fdd670c53c04e28c546c28484de47; bp_video_offset_266991838=854485135137964033; innersign=0; b_lsid=B109B1D106_18B4C47F052; browser_resolution=1560-883; sid=4ynzr92f; CURRENT_FNVAL=4048"
        )
    }

    detailed_log_input = input("是否想查看详细的日志？ (y/n): ").strip().lower()
    log_level = logging.DEBUG if detailed_log_input == 'y' else logging.INFO

    try:
        if "video" in url:
            logging.info('你想要下载一个视频')
            downloader = VideoDownloader(user_cookie,log_level)
            downloader.download_video(url)  # 确保 download_video 是 VideoDownloader 类的方法
        elif "bangumi" in url:
            logging.info('你想要下载一个番剧')
            downloader = BangumiDownloader(user_cookie, log_level)
            downloader.download_bangumi(url)  # 确保 download_bangumi 是 BangumiDownloader 类的方法
        else:
            logging.error("无效的URL!")
    except SystemExit:
        # 如果是 SystemExit 异常，说明用户选择了不覆盖文件，直接退出
        pass
    except Exception as e:
        logging.error(f"下载过程中出现错误: {e}")



if __name__ == '__main__':
    main()
