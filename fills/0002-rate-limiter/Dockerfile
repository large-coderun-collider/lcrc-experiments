FROM python:3.13-slim

WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml README.md /app/
COPY src/ /app/src/
COPY tests/ /app/tests/

RUN python -m pip install -U pip \
 && python -m pip install -e .

# default: run tests
CMD ["python", "-m", "unittest", "-v"]
