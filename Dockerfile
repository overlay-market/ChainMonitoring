FROM python:3.9

RUN mkdir /app/
WORKDIR /app/

COPY ./requirements-eth-brownie-1.19.3.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY ./ /app/

EXPOSE 8000
CMD python chain_monitoring.py
