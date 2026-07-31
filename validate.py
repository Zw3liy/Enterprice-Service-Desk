import subprocess
print("=" * 60)
print("Validation Report")
print("=" * 60)
subprocess.run(["python","manage.py","check"])
subprocess.run(["python","-m","compileall","."])
