FROM python:3.11-buster


WORKDIR /app

# Install dependencies
COPY summarize.py construct_mmcf_problem.py ./

COPY requirements.txt .
RUN python -m pip install -r requirements.txt

ENTRYPOINT ["bash"]
