import asyncio
async def task1():
   await asyncio.sleep(2)
   print("Tâche 1 terminée")
async def task2():
   await asyncio.sleep(1)
   print("Tâche 2 terminée")
async def main():
   # Lancement des tâches en parallèle
   t1 = asyncio.create_task(task1())
   t2 = asyncio.create_task(task2())
   await t1
   await t2
asyncio.run(main())