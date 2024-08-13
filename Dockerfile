FROM python:slim

WORKDIR /app

COPY *.py /app/
COPY requirements.txt /app/
COPY bracket/ /app/bracket/
COPY migrations/ /app/migrations/
COPY xonotic/ /app/xonotic/
COPY cmdresults.json /app/
COPY gametypes.json /app/
COPY xonotic.json /app/

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "startbot.py"]
