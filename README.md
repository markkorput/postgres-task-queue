# postgres-task-queue: PostgreSQL Task Queue

A PostgreSQL-based distributed task queue system built on [pgmq](https://github.com/pgmq/pgmq). postgres-task-queue provides a high-level Python API for defining tasks, processing messages with worker concurrency, handling dead-letter queues, and automatically pruning archived messages.

## Installation

```bash
pip install postgres-task-queue
```

## Usage

### Setup (database connection)

Before using the task queue, configure your (asyncpg) database connection using the `setup` method:

Option 1: Provide an asyncpg connection factory

```python
import asyncpg
from postgres_task_queue import setup

async def get_connection():
    conn = await asyncpg.connect("postgresql://user:password@localhost:5432/dbname")
    try:
        yield conn
    finally:
        await conn.close()

setup(connection=get_connection)
```

Option 2: Provide a pre-configured PGMQ instance

```python
from pgmq import AsyncPGMQueue

pgmq = AsyncPGMQueue(connection_string="postgresql://user:password@localhost:5432/dbname")
await pgmq.init()

setup(pgmq=pgmq)
```

### Complete Example: Single Queue with input validation

#### Create the queue (`queue.py`)

```python
from pydantic import BaseModel
from postgres_task_queue import create_queue

class UserAction(BaseModel):
    user_id: int
    action: str

user_actions_queue = create_queue("user_actions", input_model=UserAction)
```


#### Schedule tasks

```python
from .queue import user_actions_queue

async def some_api_endpoint_or_cli_function():
    user_action = user_action(user_id=123, action="login")
    await user_actions_queue.enqueue(user_action)
```


#### Create a queue processor (`processor.py`)

```python
from postgres_task_queue.processor import processor
from .queue import user_actions_queue

@processor(user_actions_queue)
async def user_actions_processor(user_action: UserAction) -> None:
    print(f"Processing: User {user_action.user_id} performed {user_action.action}")
```


#### Run a worker

```python
from postgres_task_queue.worker import Worker
from .processor import user_actions_processor

async def run_worker():
    worker = Worker(
        processors={user_actions_processor},
    )
    await worker.run()
```


### Enqueuing Options

```python
async def enqueue_examples():
    # Enqueue a dict message to a basic queue with input validation
    await basic_queue.enqueue({"user_id": 123, "action": "login"})

    # Enqueue a Pydantic model for input validation
    task = MyTask(user_id=456, action="purchase")
    await typed_queue.enqueue(task)

    # Enqueue with a group for strict (FIFO/LIFO) ordering within the group
    await typed_queue.enqueue(task, group="vip_users")

    # Enqueue with delay (seconds)
    await typed_queue.enqueue(task, delay=60)
```


### Processor Options

```python
from pydantic import BaseModel

class Task(BaseModel):
  value: float
  message: str
  task_id: str

@processor(
    queue,
    max_retries=3, # (default: 0)
    retry_on=(ConnectionError, TimeoutError), # Exceptions for which a retry should be scheduled (default: None / all exceptions)
    retry_delay=5.0, # delay (in seconds) between multiple (retry) attemps (default: no delay)
    timeout=120, # the time (in seconds) how long a task becomes "invisible" on the queue when a processor starts processing it, before becoming visible to (other) processors/workers again. If it takes longer for a processor to execute a task, it will be interrupted and aborted. (default: 60)
    concurrency_limit=10, # queue-level concurrency-limit (default: None / no limit)
    grouped=True, # when True, respects strictly ordered FIFO/LIFO grouping headers (default: False)
    lifo=True, # when True, will process tasks in reverse order (default: False)
    idempotency_key: "task_id", # the property in the input data that will be populated with a stable task-specific key (str)
)
async def processor_func(task: Task) -> None:
    # Process task with retry logic
    pass
```


### Worker Options

```python
from postgres_task_queue.worker import Worker
from .processor import user_actions_processor

async def run_worker():
    worker = Worker(
        processors={user_actions_processor},
        concurrency_limit=10,  # Number of concurrent tasks this worker can execute (default: 1)
        poll_interval_seconds=1.0,  # Interval in seconds between poll attempts (default: 1.0)
        poll_exception_interval_seconds=5.0,  # Interval in seconds between poll attempts when an exception occurs (default: 5.0)
        prune_interval=datetime.timedelta(hours=12),  # Pruning interval for archived messages (default: 12 hours, None disables pruning)
        prune_batch_size=1000,  # Maximum number of archived messages to prune in one batch (default: 1000)
    )
    await worker.run()
```

### CLI Worker Options

You can also run workers directly from the command line:

```bash
# Run worker scanning a module for Processor instances
uv run python -m postgres_task_queue.worker myapp.processors

# With options
uv run python -m postgres_task_queue.worker myapp.processors \
    --concurrency-limit 10 \
    --poll-interval-seconds 0.5 \
    --poll-exception-interval-seconds 3.0 \
    --prune-interval 60 \  # minutes
    --prune-batch-size 500

# Filter specific processors
uv run python -m postgres_task_queue.worker myapp.processors \
    --include user_actions \
    --exclude legacy_tasks
```

Note that this method will cause PGMQ to look for DB details in [environment variables](https://pgmq.github.io/pgmq-py/latest/getting_started/#environment-variables).

