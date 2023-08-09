FROM python:3.11

RUN mkdir /app/
WORKDIR /app/

COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY ./ /app/

EXPOSE 8000
# ENV FLASK_APP=query_mint_events.py
# CMD flask run -h 0.0.0 -p 5000
CMD python query_mint_events.py
