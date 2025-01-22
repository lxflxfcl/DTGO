import json
import os

class Config:
    def __init__(self):
        self.config_file = "dtgo_config.json"
        self.config = self.load_config()
    
    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # 确保有任务记录字段
                    if "task_records" not in config:
                        config["task_records"] = {}
                    return config
            except:
                return {
                    "fofa_key": "",
                    "successful_beacons": {},
                    "task_records": {}  # 添加任务记录存储
                }
        return {
            "fofa_key": "",
            "successful_beacons": {},
            "task_records": {}
        }
    
    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f)
    
    def get_fofa_key(self):
        return self.config.get("fofa_key", "")
    
    def set_fofa_key(self, key):
        self.config["fofa_key"] = key
        self.save_config()
    
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