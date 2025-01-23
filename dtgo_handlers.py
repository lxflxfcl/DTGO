import requests
import json
import time
from PyQt6.QtCore import QThread, pyqtSignal

class TaskManager(QThread):
    progress_signal = pyqtSignal(str)
    result_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    token_expired_signal = pyqtSignal(str)  # 添加token过期信号
    task_created_signal = pyqtSignal(str)  # 新增任务创建信号
    task_completed_signal = pyqtSignal(str)  # 新增任务完成信号
    
    def __init__(self, beacon_info, targets):
        super().__init__()
        self.beacon_info = beacon_info
        self.targets = targets
        self.task_ids = []  # 存储所有任务ID
        self.running = True
        self.active_tasks = {}  # 存储活动任务的状态信息 {task_id: {last_check_time, last_assets_count, last_leaks_count}}
        
    def stop(self):
        self.running = False
        
    def check_existing_tasks(self):
        """检查灯塔当前的任务数量"""
        url = f"https://{self.beacon_info['target']}/api/task/?page=1&size=100"
        headers = {"Token": self.beacon_info["token"]}
        try:
            response = requests.get(url, headers=headers, verify=False)
            if response.status_code == 200:
                result = response.json()
                tasks = result.get("items", [])
                # 只检查running和waiting状态的任务
                running_tasks = [t for t in tasks if t["status"] in ["running", "waiting"]]
                return len(running_tasks)
        except Exception as e:
            self.error_signal.emit(f"检查任务失败: {str(e)}")
        return 0
        
    def run(self):
        # 首先检查当前任务数量
        current_tasks = self.check_existing_tasks()
        if current_tasks > 5:  # 限制最大并行任务数为5
            self.error_signal.emit(f"灯塔 {self.beacon_info['target']} 运行中的任务过多(>{current_tasks})")
            return
            
        # 提交所有任务
        for target in self.targets:
            if not self.running:
                break
            try:
                task_id = self.submit_task(target)
                if task_id:
                    self.task_ids.append(task_id)
                    self.task_created_signal.emit(task_id)  # 发送任务创建信号
                    # 初始化任务状态
                    self.active_tasks[task_id] = {
                        "last_check_time": 0,
                        "last_assets_count": 0,
                        "last_leaks_count": 0,
                        "target": target
                    }
                else:
                    self.error_signal.emit(f"提交任务失败: {target}")
            except Exception as e:
                self.error_signal.emit(f"任务提交失败: {str(e)}")
        
        # 监控所有任务
        while self.running and self.active_tasks:
            completed_tasks = []
            for task_id in list(self.active_tasks.keys()):
                if not self.running:
                    break
                try:
                    if self.monitor_task_once(task_id):
                        completed_tasks.append(task_id)
                except Exception as e:
                    self.error_signal.emit(f"监控任务失败: {str(e)}")
                    completed_tasks.append(task_id)
            
            # 移除已完成的任务
            for task_id in completed_tasks:
                del self.active_tasks[task_id]
            
            time.sleep(5)  # 避免过于频繁的检查
    
    def monitor_task_once(self, task_id):
        """监控单个任务一次，返回任务是否完成"""
        try:
            status = self.check_task_status(task_id)
            current_time = time.time()
            task_info = self.active_tasks[task_id]
            
            # 检查是否需要收集结果
            if current_time - task_info["last_check_time"] >= 10:  # 每10秒检查一次
                results = self.collect_intermediate_results(
                    task_id,
                    task_info["last_assets_count"],
                    task_info["last_leaks_count"]
                )
                if results:
                    task_info["last_assets_count"] = results["assets_count"]
                    task_info["last_leaks_count"] = results["leaks_count"]
                task_info["last_check_time"] = current_time
            
            if status == "done":
                self.task_completed_signal.emit(task_id)  # 发送任务完成信号
                self.progress_signal.emit(f"任务 {task_id} ({task_info['target']}) 完成，正在收集最终结果...")
                self.collect_final_results(task_id)
                return True
            elif status == "error":
                self.error_signal.emit(f"任务执行失败: {task_id} ({task_info['target']})")
                return True
            else:
                self.progress_signal.emit(f"任务 {task_id} ({task_info['target']}) 状态: {status}")
                return False
                
        except Exception as e:
            self.error_signal.emit(f"监控任务状态失败: {str(e)}")
            return True  # 发生错误时认为任务完成，避免无限循环
        
    def refresh_token(self):
        """刷新token"""
        try:
            url = f"https://{self.beacon_info['target']}/api/user/login"
            data = {"username": "admin", "password": "arlpass"}
            response = requests.post(url, json=data, verify=False, timeout=5)
            result = response.json()
            
            if result.get("code") == 200:
                self.beacon_info["token"] = result["data"]["token"]
                return True
            return False
        except Exception:
            return False
            
    def submit_task(self, target, retry=True):
        url = f"https://{self.beacon_info['target']}/api/task/"
        headers = {
            "Token": self.beacon_info["token"],
            "Content-Type": "application/json"
        }
        data = {
            "name": f"DTGO_{int(time.time())}",
            "target": target,
            "domain_brute_type": "big",
            "port_scan_type": "all",
            "domain_brute": True,
            "alt_dns": False,
            "dns_query_plugin": True,
            "arl_search": True,
            "port_scan": True,
            "service_detection": True,
            "os_detection": False,
            "ssl_cert": False,
            "skip_scan_cdn_ip": True,
            "site_identify": True,
            "search_engines": False,
            "site_spider": False,
            "site_capture": False,
            "file_leak": True,
            "findvhost": False,
            "nuclei_scan": False,
            "web_info_hunter": False
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, verify=False, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 200:
                    self.progress_signal.emit(f"成功提交任务: {target}")
                    return result["items"][0]["task_id"]
                elif result.get("code") == 401 and retry:  # token过期
                    if self.refresh_token():
                        # 刷新token成功，重试提交任务
                        return self.submit_task(target, retry=False)
                    else:
                        self.token_expired_signal.emit(self.beacon_info["target"])
                else:
                    self.progress_signal.emit(f"提交任务失败: {target}")
            else:
                self.progress_signal.emit(f"提交任务失败: {target}")
        except Exception as e:
            self.progress_signal.emit(f"提交任务异常: {target}")
        return None
        
    def check_task_status(self, task_id):
        """检查任务状态"""
        url = f"https://{self.beacon_info['target']}/api/task/{task_id}"
        headers = {"Token": self.beacon_info["token"]}
        try:
            response = requests.get(url, headers=headers, verify=False)
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 200:
                    task_data = result["data"]
                    status = task_data["status"]
                    
                    # 添加详细的状态信息
                    progress_info = []
                    if "service" in task_data:
                        completed_services = [s["name"] for s in task_data.get("service", [])]
                        progress_info.append(f"已完成: {', '.join(completed_services)}")
                    
                    if "end_time" in task_data and task_data["end_time"] != "-":
                        progress_info.append(f"结束时间: {task_data['end_time']}")
                    
                    progress_str = " | ".join(progress_info) if progress_info else "进行中"
                    self.progress_signal.emit(f"任务 {task_id} - {status} ({progress_str})")
                    return status
                elif result.get("code") == 401 and self.refresh_token():
                    # token过期，刷新后重试
                    return self.check_task_status(task_id)
            return None
        except Exception as e:
            self.error_signal.emit(f"检查任务状态失败: {str(e)}")
            return None
        
    def collect_intermediate_results(self, task_id, last_assets_count, last_leaks_count):
        """收集中间结果，只返回新发现的结果"""
        try:
            assets = self.get_assets(task_id)
            leaks = self.get_leaks(task_id)
            domains = self.get_domains(task_id)  # 添加子域名获取
            
            new_assets = assets[last_assets_count:]
            new_leaks = leaks[last_leaks_count:]
            
            if new_assets or new_leaks or domains:  # 修改判断条件
                results = {
                    "assets": new_assets,
                    "leaks": new_leaks,
                    "domains": domains,  # 添加子域名结果
                    "is_final": False,
                    "assets_count": len(assets),
                    "leaks_count": len(leaks)
                }
                self.result_signal.emit(results)
                self.progress_signal.emit(
                    f"任务 {task_id} 发现新结果: "
                    f"{len(new_assets)} 个资产, {len(new_leaks)} 个泄露, {len(domains)} 个子域名"
                )
                return results
            return None
        except Exception as e:
            self.error_signal.emit(f"收集中间结果失败: {str(e)}")
            return None
        
    def collect_final_results(self, task_id):
        """收集最终结果"""
        try:
            results = {
                "assets": self.get_assets(task_id),
                "leaks": self.get_leaks(task_id),
                "domains": self.get_domains(task_id),  # 添加子域名结果
                "is_final": True
            }
            if results["assets"] or results["leaks"] or results["domains"]:
                self.progress_signal.emit(
                    f"任务 {task_id} 完成，共发现 "
                    f"{len(results['assets'])} 个资产, {len(results['leaks'])} 个泄露, "
                    f"{len(results['domains'])} 个子域名"
                )
                self.result_signal.emit(results)
        except Exception as e:
            self.error_signal.emit(f"收集最终结果失败: {str(e)}")
        
    def get_assets(self, task_id, retry=True):
        """获取资产结果"""
        url = f"https://{self.beacon_info['target']}/api/site/?page=1&size=1000&task_id={task_id}"
        headers = {"Token": self.beacon_info["token"]}
        try:
            response = requests.get(url, headers=headers, verify=False)
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 200:
                    return [
                        (
                            item["site"],
                            item["title"],
                            item.get("ip", ""),
                            item.get("http_server", ""),
                            # 格式化 finger 信息
                            ", ".join([
                                f"{f['name']}{f.get('version', '')}"
                                for f in item.get("finger", [])
                            ])
                        )
                        for item in result.get("items", [])
                    ]
                elif result.get("code") == 401 and retry:  # token过期
                    if self.refresh_token():
                        return self.get_assets(task_id, retry=False)
                    else:
                        self.token_expired_signal.emit(self.beacon_info["target"])
        except Exception as e:
            self.error_signal.emit(f"获取资产失败: {str(e)}")
        return []
        
    def get_leaks(self, task_id, retry=True):
        """获取信息泄露结果"""
        url = f"https://{self.beacon_info['target']}/api/fileleak/?page=1&size=1000&task_id={task_id}"
        headers = {"Token": self.beacon_info["token"]}
        try:
            response = requests.get(url, headers=headers, verify=False)
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 200:
                    return [(item["url"], item["title"]) for item in result.get("items", [])]
                elif result.get("code") == 401 and retry:  # token过期
                    if self.refresh_token():
                        # 刷新token成功，重试获取泄露信息
                        return self.get_leaks(task_id, retry=False)
                    else:
                        self.token_expired_signal.emit(self.beacon_info["target"])
        except Exception as e:
            self.error_signal.emit(f"获取信息泄露失败: {str(e)}")
        return []
        
    def get_domains(self, task_id, retry=True):
        """获取子域名结果"""
        url = f"https://{self.beacon_info['target']}/api/domain/?page=1&size=1000&task_id={task_id}"
        headers = {"Token": self.beacon_info["token"]}
        try:
            response = requests.get(url, headers=headers, verify=False)
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 200:
                    return [
                        (
                            item["domain"],
                            item["type"],
                            ", ".join(item.get("ips", []))  # 将IP列表合并为字符串
                        )
                        for item in result.get("items", [])
                    ]
                elif result.get("code") == 401 and retry:  # token过期
                    if self.refresh_token():
                        return self.get_domains(task_id, retry=False)
                    else:
                        self.token_expired_signal.emit(self.beacon_info["target"])
        except Exception as e:
            self.error_signal.emit(f"获取子域名失败: {str(e)}")
        return []
        
    def delete_task(self, task_id, retry=True):
        """删除灯塔任务"""
        url = f"https://{self.beacon_info['target']}/api/task/delete/"
        headers = {
            "Token": self.beacon_info["token"],
            "Content-Type": "application/json"  # 添加 Content-Type 头
        }
        data = {
            "task_id": [task_id],
            "del_task_data": True
        }
        
        try:
            self.progress_signal.emit(f"正在删除任务 {task_id}...")
            response = requests.post(url, json=data, headers=headers, verify=False)
            result = response.json()
            
            if result.get("code") == 200:
                self.progress_signal.emit(f"任务 {task_id} 删除成功")
                return True
            elif result.get("code") == 401 and retry:  # token过期
                if self.refresh_token():
                    return self.delete_task(task_id, retry=False)
                else:
                    self.token_expired_signal.emit(self.beacon_info["target"])
            else:
                self.error_signal.emit(f"删除任务失败: {result.get('message', '未知错误')}")
            return False
        except Exception as e:
            self.error_signal.emit(f"删除任务失败: {str(e)}")
            return False 