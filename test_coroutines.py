import asyncio

async def greet():
    print("Hello")
    await asyncio.sleep(5)  # Simulates a non-blocking delay
    print("World")

async def greet2():
    print("Hello from greet2")
    await asyncio.sleep(1)  # Simulates a non-blocking delay
    print("World from greet2")


async def main():
    print("Starting coroutine test...")
    task1 = asyncio.create_task(greet())
    task2 = asyncio.create_task(greet2())
    
    # Both coroutines run concurrently
    await asyncio.gather(task1, task2)

   
    
    print("Both tasks completed!")

if __name__ == "__main__":
    asyncio.run(main()) # run should happen only once at the top level