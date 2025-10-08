FROM python:3.13.5-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1
WORKDIR /build

# Create requirements.txt file
FROM base AS poetry
RUN pip install poetry==2.1.3
RUN poetry self add poetry-plugin-export
COPY poetry.lock pyproject.toml ./
RUN poetry export -o /requirements.txt --without-hashes

FROM base AS final
COPY --from=poetry /requirements.txt .

# Create venv, add it to path and install requirements
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
RUN pip install -r requirements.txt
RUN pip install playwright==1.55.0 && playwright install --with-deps chromium firefox

# Copy the rest of app
COPY app app
COPY pyproject.toml .
COPY init.sh .

# Expose port
EXPOSE 8000

# Make the init script executable
RUN chmod +x ./init.sh

# Set ENTRYPOINT to always run init.sh
ENTRYPOINT ["./init.sh"]

# Run docker from entrypoint of PoC
CMD ["/venv/bin/python","-m","app.app_driver"]