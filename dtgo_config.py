import json
import os
import sys
import traceback

class Config:
    def __init__(self):
        try:
            # 获取应用程序的实际路径
            if getattr(sys, 'frozen', False):
                # 如果是打包后的应用
                self.app_path = os.path.dirname(sys.executable)
            else:
                # 如果是开发环境
                self.app_path = os.path.dirname(os.path.abspath(__file__))
            
            # 配置文件路径
            self.config_file = os.path.join(self.app_path, "dtgo_config.json")
            self.config = self.load_config()
        except Exception as e:
            print(f"Config initialization error: {str(e)}")
            traceback.print_exc()
            self.config = {
                "fofa_key": "",
                "successful_beacons": {},
                "task_records": {}
            }
    
    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if "task_records" not in config:
                        config["task_records"] = {}
                    return config
        except Exception as e:
            print(f"Load config error: {str(e)}")
            traceback.print_exc()
        return {
            "fofa_key": "",
            "successful_beacons": {},
            "task_records": {}
        }
    
    def save_config(self):
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # 保存配置
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Save config error: {str(e)}")
            traceback.print_exc()
            return False
    
    def get_fofa_key(self):
        return self.config.get("fofa_key", "")
    
    def set_fofa_key(self, key):
        try:
            self.config["fofa_key"] = key
            return self.save_config()
        except Exception as e:
            print(f"Set fofa key error: {str(e)}")
            traceback.print_exc()
            return False
    
    def get_successful_beacons(self):
        return self.config.get("successful_beacons", {})
    
    def save_successful_beacons(self, beacons):
        self.config["successful_beacons"] = beacons
        self.save_config()
    
    def get_task_records(self):
        return self.config.get("task_records", {})
    
    def save_task_records(self, records):
        self.config["task_records"] = records
        self.save_config() 