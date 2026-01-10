import sys
import os
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tingwu20220930 import models as tingwu_models
from alibabacloud_tingwu20220930.client import Client as AlibabaTingwuClient

# 引入项目配置
sys.path.append(os.getcwd())
from src.utils.config import Config

def test_region(region_id, app_key, access_key, secret_key):
    """测试指定区域是否可用"""
    print(f"\n🔍 正在尝试连接区域: 【{region_id}】...")
    endpoint = f"tingwu.{region_id}.aliyuncs.com"
    
    try:
        # 配置客户端
        config = open_api_models.Config(
            access_key_id=access_key,
            access_key_secret=secret_key
        )
        config.region_id = region_id
        config.endpoint = endpoint
        client = AlibabaTingwuClient(config)

        # 构造一个最小请求（不实际提交文件，只做参数校验）
        # 我们故意传一个无效URL，如果AppKey校验通过，它会报URL错误而不是InvalidAppKey
        request = tingwu_models.CreateFileTransRequest()
        request.body = {
            "AppKey": app_key,
            "Input": {"FileUrl": "http://check-region.mp3"}, 
            "Parameters": {
                "Format": "mp3", 
                "SampleRate": 16000,
                "Language": "zh-CN"
            }
        }
        
        client.create_file_trans(request)
        print(f"✅ 成功！您的 AppKey 属于区域: {region_id}")
        return True

    except Exception as e:
        error_msg = str(e)
        if "InvalidAppKey" in error_msg:
            print(f"❌ 失败: 此 AppKey 不属于 {region_id}")
            return False
        elif "FileDownloadFailed" in error_msg or "Input.FileUrl" in error_msg:
            # 如果报错变成了文件下载失败，说明 AppKey 验证通过了！
            print(f"✅ 成功！您的 AppKey 属于区域: {region_id}")
            return True
        else:
            # 其他网络或权限错误
            print(f"⚠️  其他错误 (可能是区域正确但权限不足): {error_msg}")
            # 通常如果不是 InvalidAppKey，我们就认为可能找对地方了
            return False

if __name__ == "__main__":
    print("=== 阿里云听悟 AppKey 区域自动探测工具 ===")
    
    # 读取配置
    config = Config()
    app_key = config.get("tingwu.app_key")
    access_key = config.get("aliyun.access_key_id")
    secret_key = config.get("aliyun.access_key_secret")
    
    if not all([app_key, access_key, secret_key]):
        print("❌ 错误: 请先在 config.yaml 中填好 app_key, access_key 和 secret")
        sys.exit(1)

    print(f"当前配置的 AppKey: {app_key[:6]}******{app_key[-4:]}")
    
    # 依次测试常见区域
    valid_region = None
    
    # 1. 测北京
    if test_region("cn-beijing", app_key, access_key, secret_key):
        valid_region = "cn-beijing"
    
    # 2. 如果北京不行，测上海
    elif test_region("cn-shanghai", app_key, access_key, secret_key):
        valid_region = "cn-shanghai"
        
    # 3. 测深圳 (少见但有可能)
    elif test_region("cn-shenzhen", app_key, access_key, secret_key):
        valid_region = "cn-shenzhen"

    print("\n" + "="*30)
    if valid_region:
        print(f"🎉 诊断完成！正确的区域是: 【{valid_region}】")
        print(f"👉 请修改 config.yaml 文件:")
        print(f'   aliyun:\n     region: "{valid_region}"')
    else:
        print("❌ 所有区域都测试失败。可能原因：")
        print("1. AppKey 抄写错误（请去控制台复制）")
        print("2. 这是一个“智能语音交互”项目的Key，但没开通“听悟”功能")
        print("3. 账号欠费或权限不足")