# Agent_Vue_Campus

An agent website for learning and training

软件环境
类别	
操作系统	Ubuntu Server 22.04 LTS
GPU驱动	与CUDA和显卡型号匹配的NVIDIA官方驱动
模型服务	Ollama
后端环境	Python Conda环境，隔离CUDA、OCR、后端服务依赖
前端环境	Node.js LTS版本
数据库	PostgreSQL+pgvector
缓存和队列	Redis
反向代理以及安全保障	Nginx
异步任务	Celeryworker，文档队列和网页队列分开运行
