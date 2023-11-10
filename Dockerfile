FROM python:3.11-slim-bookworm

WORKDIR /app

ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . .

CMD ["python", "src/main.py"]