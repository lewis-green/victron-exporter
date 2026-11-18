FROM python:3.12-slim
WORKDIR /app
COPY exporter/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY exporter/victron_exporter ./victron_exporter
USER nobody
EXPOSE 9105
ENTRYPOINT ["python", "-m", "victron_exporter"]
