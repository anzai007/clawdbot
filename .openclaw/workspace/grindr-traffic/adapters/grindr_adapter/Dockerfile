FROM python:3.12-slim

# 关闭 pyc、开启无缓冲日志，便于容器日志排查。
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 先安装依赖，提升构建缓存命中率。
COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements.txt

# 拷贝运行代码到镜像内；运行时会由 volume 覆盖为工作区最新代码。
COPY . /app

EXPOSE 8787
