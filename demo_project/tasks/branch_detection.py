import subprocess

def get_current_git_branch():
    try:
        result = subprocess.run(['git', 'branch', '--show-current'], stdout=subprocess.PIPE, text=True, check=True)
        current_branch = result.stdout.strip()
        return current_branch
    except subprocess.CalledProcessError:
       
        return None

# if current_branch:
#     print(f"Current branch is: {current_branch}")
# else:
#     print("Unable to determine the current branch.")