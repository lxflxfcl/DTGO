# DTGO (灯塔狩猎者)

DTGO (灯塔收割者) 是一个用于批量管理和监控资产灯塔系统任务的图形化工具。它能够自动发现灯塔系统、批量提交任务、监控任务状态，并支持导出任务结果。

![image.png](https://lxflxf.oss-cn-beijing.aliyuncs.com/20250122092443.png)

## 功能特点

### 灯塔发现

- 自动调用 FOFA API 发现资产灯塔系统

- 支持批量自动登录验证

- 自动保存已验证的灯塔信息

- 支持灯塔状态颜色标识

### 任务管理

- 支持批量提交任务到多个灯塔

- 智能任务分配算法，优先分配给空闲灯塔

- 实时监控任务执行状态

- 自动处理 token 过期问题

- 限制单个灯塔并行任务数量（最大5个）

- 支持任务状态持久化存储

### 结果导出

- 支持导出资产列表（包含网站、标题、IP、Server、指纹信息）

- 支持导出子域名信息（包含域名、类型、IP列表）

- 支持导出信息泄露数据（包含URL和标题）

- 支持 Excel 格式


### 界面功能

- 任务运行状态实时显示

- 支持任务执行进度展示

- 支持删除历史任务记录

- 任务状态颜色区分显示

- 支持右键菜单快捷操作

- 支持任务确认对话框预览
## 项目结构

```
DTGO/
├── dtgo_main.py # 主程序入口和GUI实现

├── dtgo_handlers.py # 任务处理模块

├── dtgo_config.py # 配置管理模块

├── requirements.txt # 依赖清单

├── README.md # 项目文档

```

## 安装说明

### 安装步骤


```
1. 克隆项目
bash
git clone https://github.com/yourusername/DTGO.git
cd DTGO
2. 创建虚拟环境
bash
python -m venv .venv
source .venv/bin/activate # Linux/Mac
或
.venv\Scripts\activate # Windows
3. 安装依赖
bash
pip install -r requirements.txt
```

## 使用说明

### 配置

1. 启动程序后，点击"设置"按钮
2. 输入 FOFA API Key
3. 点击保存

![image.png](https://lxflxf.oss-cn-beijing.aliyuncs.com/20250122092228.png)

### 基本操作

1. 扫描灯塔

- 点击"扫描灯塔"按钮开始自动发现灯塔系统

- 程序会自动尝试登录验证发现的灯塔

- 成功验证的灯塔会显示在左侧列表中

![image.png](https://lxflxf.oss-cn-beijing.aliyuncs.com/20250122093145.png)



2. 提交任务

- 在左侧输入框中输入目标域名（每行一个）

- 在灯塔列表中选择要提交到的灯塔（支持多选）

- 点击"提交任务"按钮

- 在确认对话框中查看任务分配情况

- 确认后开始执行任务

![image.png](https://lxflxf.oss-cn-beijing.aliyuncs.com/20250122093015.png)


3. 查看结果

- 任务列表实时显示任务状态

- 运行中的任务显示为蓝色

- 已完成的任务显示为绿色

- 可以查看资产列表、子域名、信息泄露三个标签页的结果

4. 导出结果

- 右键点击任务列表中的任务

- 选择"导出到XLSX"

- 选择保存位置
  
![image.png](https://lxflxf.oss-cn-beijing.aliyuncs.com/20250122093417.png)


### 注意事项
- 每个灯塔最多同时运行 5 个任务
- 任务状态每 2 分钟自动检查一次
- Token 过期会自动重新登录
- 程序关闭后任务状态会保存，下次打开可继续查看

## 更新日志

### v1.0.0 (2025-01-21)
- 初始版本发布
- 实现基本功能
- 支持任务管理和结果导出

### v1.1.0 (计划中)
- [ ] 添加批量导出功能
- [ ] 支持自定义灯塔配置
- [ ] 添加结果筛选功能

## 问题反馈
- 提交 Issue
- 发送邮件至：lxflxfcl@gmail.com
- 加入讨论群：
![image.png](https://lxflxf.oss-cn-beijing.aliyuncs.com/20250122161802.png)
- 添加作者：
![image.png](https://lxflxf.oss-cn-beijing.aliyuncs.com/20250122162041.png)
## 作者
小艾
微信公众号：小艾搞安全

## 免责声明
本工具仅用于安全研究和授权测试，使用本工具进行违法操作造成的后果由使用者自行承担。

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=lxflxfcl/DTGO&type=Date)](https://star-history.com/#lxflxfcl/DTGO&Date)
