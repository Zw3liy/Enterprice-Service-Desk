import subprocess
print("=" * 60)
print("Enterprise Service Desk Builder")
print("=" * 60)
subprocess.run(["python","manage.py","check"])
subprocess.run(["python","manage.py","makemigrations"])
subprocess.run(["python","manage.py","migrate"])
subprocess.run(["python","manage.py","runserver"])
