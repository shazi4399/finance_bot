# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
import requests
import urllib.parse
from datetime import datetime
from pathlib import Path

# ================= 环境与配置加载 =================
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

try:
    from src.utils.config import Config
    config = Config()
    
    APP_ID = config.get("xfyun.APPID")
    ACCESS_KEY_ID = config.get("xfyun.APIKey") 
    ACCESS_KEY_SECRET = config.get("xfyun.APISecret")
    
    # 【核心修改 1】您的本地文件路径
    AUDIO_FILE_PATH = r"/Users/zhanghao/Downloads/finance_bot/BV1UNBKBoE5A.mp3"
    
    # 【核心修改 2】手动指定准确时长（毫秒）
    # 29分10秒 = (29 * 60 + 10) * 1000 = 1750000 ms
    REAL_DURATION_MS = 1750000
    
    if not all([APP_ID, ACCESS_KEY_ID, ACCESS_KEY_SECRET]):
        raise ValueError("配置缺失，请检查 config.yaml 中的 xfyun 配置")
        
    print(f"✅ 配置加载成功: AppID={APP_ID}")

except Exception as e:
    print(f"❌ 配置错误: {e}")
    sys.exit(1)

BASE_URL = "https://office-api-ist-dx.iflyaisol.com"

class XfyunLLMClient:
    def __init__(self, app_id, access_key_id, access_key_secret):
        self.app_id = app_id
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret

    def _get_signature(self, params):
        """生成鉴权签名 (HMAC-SHA1 + Base64)"""
        sorted_keys = sorted(params.keys())
        query_list = []
        for key in sorted_keys:
            if key == "signature": 
                continue
            value = str(params[key])
            if value:
                encoded_key = urllib.parse.quote(key, safe='')
                encoded_value = urllib.parse.quote(value, safe='')
                query_list.append(f"{encoded_key}={encoded_value}")
        
        base_string = "&".join(query_list)
        secret_bytes = self.access_key_secret.encode('utf-8')
        message_bytes = base_string.encode('utf-8')
        hmac_obj = hmac.new(secret_bytes, message_bytes, hashlib.sha1)
        return base64.b64encode(hmac_obj.digest()).decode('utf-8')

    def upload(self, file_path, duration_ms):
        """上传文件"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件未找到: {file_path}")
            
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        
        # 构造请求参数
        date_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+0800")
        
        params = {
            "appId": self.app_id,
            "accessKeyId": self.access_key_id,
            "dateTime": date_time,
            "signatureRandom": str(uuid.uuid4()).replace("-", "")[:16],
            "fileSize": str(file_size),
            "fileName": file_name,
            "duration": str(duration_ms), # 使用准确时长
            "language": "autodialect",
            "pd": "finance",           # 领域：金融
            "eng_colloqproc": "true",  # 口语规整：开启 (注意必须是字符串小写 "true")
            "eng_vad_mdn": "2",        # 远近场模式：近场 (2)
            
            
        }
        
        signature = self._get_signature(params)
        url = f"{BASE_URL}/v2/upload"
        headers = {
            "Content-Type": "application/octet-stream",
            "signature": signature
        }
        
        print(f"🚀 [Xfyun-LLM] 正在上传: {file_name}")
        print(f"   - 大小: {file_size/1024/1024:.2f}MB")
        print(f"   - 设定时长: {duration_ms/1000/60:.2f}分钟 ({duration_ms}ms)")
        
        with open(file_path, "rb") as f:
            audio_data = f.read()
            
        response = requests.post(url, params=params, headers=headers, data=audio_data)
        
        try:
            data = response.json()
        except:
            raise Exception(f"API返回非JSON: {response.text}")
            
        if data.get("code") != "000000":
            print(f"❌ 上传失败响应: {json.dumps(data, ensure_ascii=False)}")
            raise Exception(f"上传失败: {data.get('descInfo')}")
            
        order_id = data.get("content", {}).get("orderId")
        print(f"✅ 上传成功! 订单号: {order_id}")
        return order_id

    def get_result(self, order_id):
        """查询结果"""
        url = f"{BASE_URL}/v2/getResult"
        print("⏳ 开始轮询结果 (预计耗时5-10分钟)...")
        start_time = time.time()
        
        while True:
            time.sleep(20) # 建议间隔稍长
            
            date_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+0800")
            params = {
                "accessKeyId": self.access_key_id,
                "dateTime": date_time,
                "signatureRandom": str(uuid.uuid4()).replace("-", "")[:16],
                "orderId": order_id,
                "resultType": "transfer"
            }
            
            signature = self._get_signature(params)
            headers = {
                "Content-Type": "application/json",
                "signature": signature
            }
            
            try:
                response = requests.post(url, params=params, headers=headers, json={})
                data = response.json()
            except Exception as e:
                print(f"⚠️ 网络请求异常: {e}, 重试中...")
                continue
                
            if data.get("code") != "000000":
                print(f"❌ 查询请求错误: {data}")
                break
                
            content = data.get("content", {})
            order_info = content.get("orderInfo", {})
            status = order_info.get("status")
            # status: 0已创建 3处理中 4已完成 -1失败
            
            if status == 4:
                print(f"\n✅ 转写完成! (耗时: {time.time()-start_time:.0f}s)")
                return content.get("orderResult", "")
            elif status == -1:
                fail_type = order_info.get("failType")
                print(f"\n❌ 转写失败: failType={fail_type}")
                # 打印详细文档链接提示
                if fail_type == 5:
                    print("   -> 原因: 音频时长校验失败，请再次核对毫秒数。")
                break
            else:
                # 打印进度条效果
                elapsed = int(time.time() - start_time)
                print(f"\r   - 状态: 处理中 (已等待 {elapsed}s)...", end="")

    def parse_result(self, raw_json_str):
        """解析结果"""
        try:
            if not raw_json_str: return ""
            result_obj = json.loads(raw_json_str)
            lattice = result_obj.get("lattice", [])
            full_text = ""
            for item in lattice:
                json_1best = item.get("json_1best", "{}")
                best_obj = json.loads(json_1best)
                st = best_obj.get("st", {})
                rt_list = st.get("rt", [])
                for rt in rt_list:
                    ws_list = rt.get("ws", [])
                    for ws in ws_list:
                        cw_list = ws.get("cw", [])
                        for cw in cw_list:
                            full_text += cw.get("w", "")
            return full_text
        except Exception as e:
            print(f"⚠️ 解析警告: {e}")
            return str(raw_json_str)

def main():
    try:
        client = XfyunLLMClient(APP_ID, ACCESS_KEY_ID, ACCESS_KEY_SECRET)
        
        # 1. 上传 (传入准确时长)
        order_id = client.upload(AUDIO_FILE_PATH, REAL_DURATION_MS)
        
        # 2. 查询
        raw_result = client.get_result(order_id)
        
        # 3. 解析并保存
        if raw_result:
            text = client.parse_result(raw_result)
            print("\n" + "="*50)
            print("📝 转写结果 (前500字):")
            print("="*50)
            print(text[:500] + "...")
            
            # 使用时间戳防止覆盖
            ts_suffix = int(time.time())
            filename = f"xfyun_llm_result_{ts_suffix}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"\n✅ 结果已保存至 {filename}")
            
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")

if __name__ == '__main__':
    main()