FROM python:3.12-slim
LABEL org.opencontainers.image.source="https://github.com/willtheorangeguy/hadge-sparkyfitness-connector" \
      org.opencontainers.image.title="Hadge to Sparky Fitness connector" \
      org.opencontainers.image.description="Sync Apple Health workout summaries from Hadge into Sparky Fitness" \
      org.opencontainers.image.licenses="MIT"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .
ENTRYPOINT ["hadge-sparkyfitness-connector"]
CMD ["watch"]
