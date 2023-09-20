# FROM python:3.9

# RUN mkdir /app/
# WORKDIR /app/

# COPY ./requirements.txt /app/requirements.txt
# RUN pip install -r requirements.txt

# COPY ./ /app/

# EXPOSE 8000
# CMD python chain_monitoring.py



FROM python:3.9

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN mkdir /app/
WORKDIR /app/

COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY ./ /app/

# RUN pytest

EXPOSE 8000
CMD ["python", "chain_monitoring.py"]
