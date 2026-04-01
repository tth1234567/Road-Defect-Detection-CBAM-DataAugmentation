# 智巡 SmartInspect — 道路缺陷智能巡检系统

> 基于 EI 国际会议论文《Road Defect Detection Method Based on CBAM and Data Augmentation》的工程化落地  
> 河北工业大学 · 中国大学生计算机设计大赛 · 人工智能赛道

---

## 第一步：安装后端依赖（只需做一次）

打开终端，执行：

```powershell
conda activate test1
cd E:\cursor_workspace\paper_for_competition_git\backend
pip install -r requirements.txt
```

如果提示某个包已存在，直接忽略，不影响运行。

---

## 第二步：验证模型是否正常（强烈建议先做这一步）

```powershell
conda activate test1
cd E:\cursor_workspace\paper_for_competition_git\backend
python scripts/test_inference.py --image ../datasets/aug_examples/AB_1000.jpeg
```

**正常输出示例：**
```
==================================================
  测试图片：AB_1000.jpeg
  置信度：0.25
==================================================
[1/3] 加载改进模型：...backend\weights\best.pt
      加载成功！
[2/3] 开始推理（imgsz=1280）...
      推理完成，耗时 1234 ms
[3/3] 检测结果：
      共检测到 2 个缺陷框：
      [1] pothole  置信度=0.823  框坐标=[...]
      [2] lateral_crack  置信度=0.671  框坐标=[...]

  结果图片已保存：...backend\scripts\output_test.jpg
==================================================
```

如果看到这个输出，说明模型完全正常，可以继续。

**如果报错 `ModuleNotFoundError: No module named 'app'`：**
请确认你在 `backend/` 目录下运行命令，而不是根目录。

---

## 第三步：启动后端

```powershell
conda activate test1
cd E:\cursor_workspace\paper_for_competition_git\backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**正常输出示例：**
```
==================================================
  智巡 SmartInspect 后端启动中...
==================================================
[模型加载] 正在加载改进模型: ...backend\weights\best.pt
[模型加载] 正在加载基线模型: ...backend\weights\yolov8n.pt
[模型加载] 两个模型加载完成，后端已就绪。
==================================================
  后端已就绪，访问 http://127.0.0.1:8000/docs 查看接口文档
==================================================
INFO:     Uvicorn running on http://127.0.0.1:8000
```

> 注意：后端窗口不要关闭，要一直保持运行。

---

## 第四步：启动前端

**重新开一个终端窗口**（不要关后端），执行：

```powershell
cd E:\cursor_workspace\paper_for_competition_git\frontend
npm run dev
```

**正常输出示例：**
```
  VITE v6.x.x  ready in 500 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

打开浏览器，访问 **http://localhost:5173** 即可看到系统界面。

---

## 演示流程（比赛现场）

### 方案一：Demo 一键演示（推荐）
1. 点击左侧「**智能检测工作台**」
2. 点击「**Demo 演示**」按钮（自动加载3张内置道路图片）
3. 根据需要调整置信度滑动条（默认 0.25 即可）
4. 点击「**开始巡检分析**」
5. 等待3张图依次分析完毕（每张约1–3秒）
6. 右侧出现「待维修路段汇总表」，点击某一行查看详情

### 方案二：演示 A/B 消融实验
1. 在工作台开启「**消融实验 A/B 对比模式**」开关
2. 加载 Demo 或上传自己的图片后开始分析
3. 分析完成后点击汇总表某行，下方显示改进模型 vs 基线模型的**并排对比图**
4. 向评审解释：左图=你的论文模型（58% mAP），右图=基线（55.8% mAP）

### 方案三：展示维修报告
1. 完成工作台分析后，点击左侧「**维修任务报告**」
2. 看到完整的缺陷明细表格（可按类型/危险等级筛选）
3. 点击「**导出维修任务 PDF**」生成报告文件

---

## 常见问题与修复

| 症状 | 原因 | 修复方法 |
|------|------|----------|
| 后端启动时报 `FileNotFoundError: best.pt` | 权值文件路径错误 | 确认 `backend/weights/best.pt` 存在 |
| 后端启动时报 `ModuleNotFoundError: No module named 'torch'` | 没有激活 test1 环境 | 运行 `conda activate test1` |
| 后端启动时报 `ModuleNotFoundError: No module named 'multipart'` | 缺少依赖 | 运行 `pip install python-multipart` |
| 前端显示「后端未启动」红点 | 后端没有运行或端口错误 | 确认后端终端正在运行且显示 8000 端口 |
| 前端页面空白 | JavaScript 报错 | 按 F12 打开控制台查看错误信息 |
| 检测完成但汇总表为空 | 所有图片均未检出缺陷 | 把置信度滑动条降低到 0.1 重试 |
| Demo 按钮报错 | 后端未启动 | 先启动后端再点 Demo |
| PDF 导出图表空白 | html2canvas 渲染问题 | 等页面完全加载后再点导出 |

---

## 文件结构说明

```
paper_for_competition_git/
├── best.pt                          原始位置，已复制到 backend/weights/
├── weights/yolov8n.pt               原始位置，已复制到 backend/weights/
├── datasets/aug_examples/           Demo 图片来源（3张道路缺陷图）
│
├── backend/                         ← 后端（Python/FastAPI）
│   ├── app/
│   │   ├── main.py                  ★ FastAPI 启动入口，配置 CORS
│   │   ├── api/
│   │   │   └── routes.py            ★ HTTP 接口定义（/api/detect 等）
│   │   ├── services/
│   │   │   ├── inference.py         ★ 模型加载与推理核心逻辑
│   │   │   └── evaluator.py         ★ 危险等级与维修费用计算
│   │   ├── models/
│   │   │   └── cbam_modules.py      ★ CBAM 类定义（加载 best.pt 必须）
│   │   ├── schemas/
│   │   │   └── responses.py         定义返回 JSON 的数据格式
│   │   └── core/
│   │       └── config.py            路径常量、类别名、成本参数
│   ├── weights/
│   │   ├── best.pt                  改进模型权值（论文最终模型）
│   │   └── yolov8n.pt               基线模型权值
│   ├── demo_images/                 3张内置演示图片
│   ├── scripts/
│   │   └── test_inference.py        本地命令行测试脚本
│   └── requirements.txt             后端依赖列表
│
└── frontend/                        ← 前端（Vue 3/Vite）
    └── src/
        ├── main.js                  前端启动入口，注册 Element Plus
        ├── App.vue                  ★ 整体布局：左侧导航栏 + 顶部 Header
        ├── router/index.js          页面路由配置
        ├── api/http.js              ★ 与后端通信的 Axios 封装
        ├── stores/inspectionStore.js 跨页面共享的巡检数据
        └── views/
            ├── Dashboard.vue        ★ 巡检仪表盘（ECharts 图表 + 地图）
            ├── DetectionWorkspace.vue ★ 智能检测工作台（核心页面）
            └── HistoryReports.vue   ★ 维修任务报告（PDF 导出）
```

标有 ★ 的是核心文件，遇到问题优先查看这些文件。

---

## 接口文档

后端启动后，打开浏览器访问：  
**http://127.0.0.1:8000/docs**

可以看到自动生成的 Swagger 接口文档，可以在网页上直接测试接口，不需要写代码。

---

## 技术栈说明

| 层 | 技术 | 用途 |
|---|---|---|
| AI 模型 | YOLOv8n + CBAM（论文模型） | 道路缺陷目标检测 |
| 后端框架 | FastAPI + Uvicorn | HTTP 服务 |
| 数据校验 | Pydantic v2 | 接口返回格式保证 |
| 图像处理 | OpenCV + Pillow | 图片解码/编码 |
| 前端框架 | Vue 3 + Vite | 单页面应用 |
| UI 组件库 | Element Plus | 表格、上传、弹窗等组件 |
| 图表 | ECharts + vue-echarts | 饼图、柱图、地图 |
| HTTP 请求 | Axios | 前端调用后端接口 |
| GPS 提取 | exifr | 读取图片 EXIF 真实坐标 |
| PDF 导出 | html2canvas + jsPDF | 导出维修报告 |
