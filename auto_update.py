import subprocess
import getpass
import time
import datetime
import os

def git_pull_every_15_min():
    """
    Updates a git repository every 15 minutes. 
    Changes to the repo path, stashes uncommitted changes, pulls the latest changes, and re-applies the stashed changes. 
    Writes the current date and time to '.last_update.out' after each successful pull.
    Runs indefinitely until interrupted.
    """
    # Get the current username + Set the path to the git repository
    username = getpass.getuser()
    repo_path = f"/home/{username}/Desktop/e-Paper/RaspberryPi_JetsonNano/python/examples"

    while True:
        try:
            # Change the current working directory + Stash any uncommitted changes
            # Execute git pull + Pop the stash to reapply uncommitted changes
            os.chdir(repo_path)
            subprocess.check_call(["git", "stash"])
            subprocess.check_call(["git", "pull"])
            subprocess.check_call(["git", "stash", "pop"])

            # If all subprocess calls are successful, write the current date and time to .last_update.out
            with open('.last_update.out', 'w', encoding='utf-8') as f:
                f.write(f"Last Update: {datetime.datetime.now().strftime('%m/%d/%Y - %I:%M%p')}\n")

        except subprocess.CalledProcessError:
            print("An error occurred while executing a subprocess call.")

        # Wait for 15 minutes
        time.sleep(900)

if __name__ == "__main__":
    git_pull_every_15_min()
