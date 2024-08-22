FROM zenika/alpine-chrome:with-node

WORKDIR /app

COPY *.py /app/
COPY requirements.txt /app/
COPY bracket/ /app/bracket/
COPY migrations/ /app/migrations/
COPY xonotic/ /app/xonotic/
COPY cmdresults.json /app/
COPY gametypes.json /app/
COPY xonotic.json /app/

USER root

ENV PYTHONUNBUFFERED=1
RUN apk add --update --no-cache python3 python3-dev py3-pip && \
  python -m venv /app/venv && \
  source /app/venv/bin/activate && \
  pip install -r requirements.txt

USER chrome

CMD ["python", "startbot.py"]
