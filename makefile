lint:
	uv run ruff check .
	uv run ruff format --check .

lintfix:
	uv run ruff format .
	uv run ruff check --fix .

ty:
	uv run ty check

test:
	uv run pytest

validate:
	make lint
	make ty
	make test
