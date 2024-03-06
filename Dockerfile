# pin specific version for stability
FROM python:3.10.13-alpine

# specify working directory other than /
WORKDIR /app

# copy file for installing requirements
ADD prod.requirements.txt .

# install requirements
RUN pip install -r prod.requirements.txt

# copy remain source code after install requirements
ADD ./src ./src

# indicated exposed port
EXPOSE 8000

ENTRYPOINT [ "uvicorn", "src.voting_app.app:app", "--host=0.0.0.0", "--port=8000"]
