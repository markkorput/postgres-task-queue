# Postgres Task Queue Demo

This demo shows:

- How to create [a queue](./src/postgres_task_queue_demo/timers/queue.py)

- How to create [a queue processor](./src/postgres_task_queue_demo/timers/processor.py)

- How to use pgmq queries to create the required message queues for your pgmq-based task queues in [DB migrations](./src/postgres_task_queue_demo/alembic/versions/)
- How to use the `create_router` helper to [generate endpoints](./src/postgres_task_queue_demo/api.py) for your [FastAPI](https://fastapi.tiangolo.com/) application.

- How to use the `setup` method to provide the database connection and invoke various operations (scheduling tasks, starting the worker) from [a cli](./src/postgres_task_queue_demo/__main__.py)

