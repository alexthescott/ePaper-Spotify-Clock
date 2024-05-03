import subprocess
import getpass
import time
import datetime

def git_pull_every_15_min():
    """
    Periodically pulls the latest changes from a git repository every 15 minutes.

    This function changes the current working directory to the specified git repository path,
    stashes any uncommitted changes, pulls the latest changes from the remote repository,
    and then pops the stash to reapply the uncommitted changes. It also writes the current
    date and time to a file named '.last_update.out' after a successful pull.

    Note: This function runs indefinitely until interrupted.
    """
    # Get the current username + Set the path to the git repository
    username = getpass.getuser()
    repo_path = f"/home/{username}/Desktop/e-Paper/RaspberryPi_JetsonNano/python/examples"

    while True:
        try:
            # Change the current working directory + Stash any uncommitted changes
            # Execute git pull + Pop the stash to reapply uncommitted changes
            subprocess.check_call(["cd", repo_path])
            subprocess.check_call(["git", "stash"])
            subprocess.check_call(["git", "pull"])
            subprocess.check_call(["git", "stash", "pop"])

            # If all subprocess calls are successful, write the current date and time to .last_update.out
            with open('.last_update.out', 'w', encoding='utf-8') as f:
                f.write(f"Last Update: {datetime.datetime.now().strftime('%m/%d/%Y - %I:%M%p')}")

        except subprocess.CalledProcessError:
            print("An error occurred while executing a subprocess call.")

        # Wait for 15 minutes
        time.sleep(900)

if __name__ == "__main__":
    git_pull_every_15_min()
